"""The verifier queue is derived from disk — `iteration.json` is not a source.

Regression background: `discover_eligible()` read iteration.json and returned a
silent `[]` when the file was missing, so the *batch* verification queue was
永空 in every project without that file, while the per-change `--stage` path
kept working (one-sided failure).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _lib.verifier.discovery import (  # noqa: E402
    discover_eligible,
    discover_eligible_detailed,
)


def _mk_change(root: Path, name: str, tasks: str) -> None:
    d = root / "openspec" / "changes" / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "tasks.md").write_text(tasks, encoding="utf-8")


def _write_iteration(root: Path, changes: list[dict]) -> None:
    state = root / ".rddf" / "state"
    state.mkdir(parents=True, exist_ok=True)
    (state / "iteration.json").write_text(
        json.dumps({"version": 7, "changes": changes}, ensure_ascii=False),
        encoding="utf-8",
    )


# --- AC1: no iteration.json, task-complete change is queued -----------------


def test_without_iteration_json_queues_task_complete_change(tmp_path):
    _mk_change(tmp_path, "c-done", "- [x] a\n- [x] b\n")
    assert discover_eligible(tmp_path) == ["c-done"]


def test_incomplete_change_is_not_queued(tmp_path):
    _mk_change(tmp_path, "c-half", "- [x] a\n- [ ] b\n")
    assert discover_eligible(tmp_path) == []


def test_archived_change_is_not_queued(tmp_path):
    d = tmp_path / "openspec" / "changes" / "archive" / "2026-01-01-c-old"
    d.mkdir(parents=True)
    (d / "tasks.md").write_text("- [x] a\n", encoding="utf-8")
    assert discover_eligible(tmp_path) == []


# --- AC3: iteration.json present & consistent ⇒ same answer ------------------


def test_consistent_iteration_json_matches_disk(tmp_path):
    _mk_change(tmp_path, "c-a", "- [x] a\n")
    _mk_change(tmp_path, "c-b", "- [ ] a\n")
    _write_iteration(tmp_path, [
        {"name": "c-a", "status": "completed", "tasks_done": 1, "tasks_total": 1},
        {"name": "c-b", "status": "proposed", "tasks_done": 0, "tasks_total": 1},
    ])
    result = discover_eligible_detailed(tmp_path)
    assert result.eligible == ["c-a"]
    assert result.notices == []


# --- stale iteration entry: disk wins, and says so ---------------------------


def test_stale_iteration_entry_does_not_override_disk(tmp_path):
    _mk_change(tmp_path, "c-a", "- [x] a\n")
    _write_iteration(tmp_path, [
        {"name": "c-a", "status": "proposed", "tasks_done": 0, "tasks_total": 1},
    ])
    result = discover_eligible_detailed(tmp_path)
    assert result.eligible == ["c-a"]
    assert len(result.notices) == 1
    assert "disk wins" in result.notices[0]
    assert "c-a" in result.notices[0]


# --- AC2: an empty queue is diagnosable, never a silent [] ------------------


def test_empty_queue_reports_reason_no_active_change(tmp_path):
    result = discover_eligible_detailed(tmp_path)
    assert result.eligible == []
    assert any("no active change" in r for r in result.reasons)


def test_empty_queue_reports_reason_no_complete_tasks(tmp_path):
    _mk_change(tmp_path, "c-half", "- [x] a\n- [ ] b\n")
    result = discover_eligible_detailed(tmp_path)
    assert result.eligible == []
    assert any("no change has all tasks checked" in r for r in result.reasons)


def test_iteration_only_fixture_is_no_longer_the_source(tmp_path):
    """An iteration.json alone (no change dir) is NOT a queue source."""
    _write_iteration(tmp_path, [
        {"name": "ghost", "status": "in_worktree", "tasks_done": 3, "tasks_total": 3},
    ])
    assert discover_eligible(tmp_path) == []


# --- CLI surface: stdout keeps its shape, reasons go to stderr --------------


def test_cli_empty_queue_prints_reasons_on_stderr(tmp_path, capsys, monkeypatch):
    from _lib.cli.rdd_verify_cmd import cmd_rdd_verify

    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    rc = cmd_rdd_verify(["--dry-run"])
    out, err = capsys.readouterr()

    assert rc == 0
    assert "No eligible changes to verify (empty queue)." in out
    assert "no active change" in err


def test_cli_dry_run_lists_change_without_iteration_json(tmp_path, capsys, monkeypatch):
    from _lib.cli.rdd_verify_cmd import cmd_rdd_verify

    _mk_change(tmp_path, "c-done", "- [x] a\n")
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    rc = cmd_rdd_verify(["--dry-run"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "c-done" in out
