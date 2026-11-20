"""`rddf status` is derived from disk — never from iteration.json.

Covers the contract of change `rddf-status-based-on-improvements`:

- iteration.json missing / corrupt ⇒ status still works (exit 0)
- Mode B: archived change ⇒ exit 0 with an `archived` view; unknown
  change ⇒ exit 1
- `--iteration` ⇒ rejected (exit 2)
- `collect_pending()`: missing dir / empty dir / no status field /
  malformed front-matter (per-entry degradation, not a blank table)
"""
from __future__ import annotations

from pathlib import Path

import pytest

from _lib.cli.status_cmd import cmd_status, cmd_status_detail


def _write_improvement(root: Path, name: str, status: str | None = "待讨论") -> None:
    imp = root / ".rddf" / "improvements"
    imp.mkdir(parents=True, exist_ok=True)
    lines = ["---", "优先级: P1"]
    if status is not None:
        lines.append(f"状态: {status}")
    lines += ["---", "", f"# {name}", ""]
    (imp / f"{name}.md").write_text("\n".join(lines), encoding="utf-8")


def _corrupt_iteration(root: Path, payload: str = "{not json") -> None:
    state = root / ".rddf" / "state"
    state.mkdir(parents=True, exist_ok=True)
    (state / "iteration.json").write_text(payload, encoding="utf-8")


# --------------------------------------------------------------------------
# AC-1: zero iteration.json dependence
# --------------------------------------------------------------------------


@pytest.mark.parametrize("payload", [None, "{not json", "[]not-json"])
def test_status_works_without_iteration_json(tmp_path, capsys, monkeypatch, payload):
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    _write_improvement(tmp_path, "my-improvement")
    if payload is not None:
        _corrupt_iteration(tmp_path, payload)

    rc = cmd_status([])
    out = capsys.readouterr().out

    assert rc == 0, out
    assert "Improvement proposals" in out
    assert "my-improvement" in out
    assert "iteration.json not found" not in out
    assert "iteration.json fails schema validation" not in out


def test_status_ignores_iteration_json_content(tmp_path, capsys, monkeypatch):
    """A stale iteration.json must not influence the output at all."""
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    _write_improvement(tmp_path, "real-one")
    _corrupt_iteration(
        tmp_path,
        '{"changes": [{"name": "ghost", "status": "in_worktree", '
        '"tasks_done": 1, "tasks_total": 1}]}',
    )
    rc = cmd_status([])
    out = capsys.readouterr().out
    assert rc == 0
    assert "real-one" in out
    assert "ghost" not in out


# --------------------------------------------------------------------------
# AC-4: Mode B disk-derived detail
# --------------------------------------------------------------------------


def test_mode_b_archived_change_exits_zero(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    archived = tmp_path / "openspec" / "changes" / "archive" / "2026-01-01-old-x"
    archived.mkdir(parents=True)
    (archived / "tasks.md").write_text("- [x] a\n", encoding="utf-8")

    assert cmd_status_detail("old-x", str(tmp_path)) == 0
    out = capsys.readouterr().out
    assert "Change: old-x" in out
    assert "archived" in out


def test_mode_b_unknown_change_exits_one(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    assert cmd_status_detail("nope", str(tmp_path)) == 1
    assert "not found" in capsys.readouterr().out


def test_mode_b_omits_phase_and_blocker(tmp_path, capsys, monkeypatch):
    """Those two fields only existed in iteration.json — they are gone."""
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    change = tmp_path / "openspec" / "changes" / "c1"
    change.mkdir(parents=True)
    (change / "tasks.md").write_text("- [x] a\n- [ ] b\n", encoding="utf-8")

    assert cmd_status_detail("c1", str(tmp_path)) == 0
    out = capsys.readouterr().out
    assert "Tasks: 1/2" in out
    assert "Builder phase:" in out
    assert "Phase:" not in out
    assert "Blocker:" not in out


# --------------------------------------------------------------------------
# AC-5: Mode E removed
# --------------------------------------------------------------------------


def test_iteration_flag_is_rejected(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    assert cmd_status(["--iteration"]) == 2
    assert "unknown flag" in capsys.readouterr().err


def test_print_view_still_importable():
    """The public export must survive (removing it breaks the API)."""
    from skills._lib.iteration import print_view  # noqa: F401


# --------------------------------------------------------------------------
# AC-6: robustness of the improvement collector
# --------------------------------------------------------------------------


def test_collect_pending_missing_dir(tmp_path):
    from skills._lib.dashboard import collect_pending
    snap = collect_pending(str(tmp_path))
    assert snap.suggestions == []
    assert snap.errors == []


def test_collect_pending_empty_dir(tmp_path):
    from skills._lib.dashboard import collect_pending
    (tmp_path / ".rddf" / "improvements").mkdir(parents=True)
    snap = collect_pending(str(tmp_path))
    assert snap.suggestions == []
    assert snap.errors == []


def test_collect_pending_missing_status_field(tmp_path):
    from skills._lib.dashboard import collect_pending
    _write_improvement(tmp_path, "no-status", status=None)
    snap = collect_pending(str(tmp_path))
    assert [s.name for s in snap.suggestions] == ["no-status"]
    assert snap.errors == []


def test_collect_pending_malformed_entry_degrades_per_entry(tmp_path, monkeypatch):
    """One broken entry must not blank the whole table.

    The breakage is injected at the classifier (the only place that can
    raise on a malformed status value): the contract under test is the
    per-entry degradation, not one particular input format.
    """
    import skills._lib.dashboard as dash

    _write_improvement(tmp_path, "good-one")
    _write_improvement(tmp_path, "bad-one")

    real = dash.classify_improvement_status
    calls = {"n": 0}

    def flaky(raw: str):
        calls["n"] += 1
        if calls["n"] == 2:          # the second entry blows up
            raise ValueError("simulated malformed status")
        return real(raw)

    monkeypatch.setattr(dash, "classify_improvement_status", flaky)
    snap = dash.collect_pending(str(tmp_path))

    names = [s.name for s in snap.suggestions]
    assert len(names) == 1, names
    assert snap.errors, "a malformed entry must be reported in errors"


def test_status_reports_unreadable_improvements(tmp_path, capsys, monkeypatch):
    import skills._lib.dashboard as dash

    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    _write_improvement(tmp_path, "good-one")
    _write_improvement(tmp_path, "bad-one")

    real = dash.classify_improvement_status
    calls = {"n": 0}

    def flaky(raw: str):
        calls["n"] += 1
        if calls["n"] == 2:
            raise ValueError("simulated malformed status")
        return real(raw)

    monkeypatch.setattr(dash, "classify_improvement_status", flaky)
    rc = cmd_status([])
    out = capsys.readouterr().out
    assert rc == 0
    assert "good-one" in out
    assert "unreadable" in out
