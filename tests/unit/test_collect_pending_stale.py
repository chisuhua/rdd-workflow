"""Stale improvement statuses must be VISIBLE, and the terminal vocabulary
must have exactly ONE definition point.

Background (fix-rddf-status-terminal-markers): ``collect_pending()`` filtered
archived / approved names **before** classifying their status ⇒ an improvement
whose status line was stale (e.g. still "已批准·待立项" after the change was
archived) disappeared from every view: not pending, not an error, not
anywhere. Four archived entries were invisible that way.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from _lib.dashboard import collect_pending  # noqa: E402
from _lib.dashboard.improvement_status import TERMINAL_MARKERS  # noqa: E402


def _write_improvement(root: Path, name: str, status: str | None = "待讨论",
                       broken: bool = False) -> None:
    imp_dir = root / ".rddf" / "improvements"
    imp_dir.mkdir(parents=True, exist_ok=True)
    if broken:
        body = (
            "---\n"
            "优先级: P2\n"
            "状态: \"未闭合的引号\n"
            "---\n\n"
            f"# {name}\n"
        )
    else:
        lines = ["---", "优先级: P1"]
        if status is not None:
            lines.append(f"状态: {status}")
        lines += ["---", "", f"# {name}", ""]
        body = "\n".join(lines)
    (imp_dir / f"{name}.md").write_text(body, encoding="utf-8")


def _make_project(tmp_path, improvements, *, archived=(), approved=()):
    for name, status in improvements.items():
        broken = isinstance(status, tuple) and status[0] == "broken"
        _write_improvement(tmp_path, name,
                           None if broken else status, broken=broken)
    (tmp_path / "improvement-approved.md").write_text(
        "## 已批准提案\n\n| 提案 | 优先级 | 批准时间 | 批准者 |\n|---|---|---|---|\n"
        + "".join(
            f"| [{name}](improvements/{name}.md) | P1 | 2026-11-27 | x |\n"
            for name in approved
        ),
        encoding="utf-8",
    )
    for name in archived:
        d = tmp_path / "openspec" / "changes" / "archive" / f"2026-11-01-{name}"
        d.mkdir(parents=True, exist_ok=True)
        (d / "tasks.md").write_text("- [x] a\n", encoding="utf-8")
    return tmp_path


# --- AC3: stale status is visible (and still not pending) --------------------


def test_archived_with_stale_status_is_reported_not_hidden(tmp_path):
    _make_project(tmp_path, {"stale-one": "🟢 已批准·待立项"}, archived=["stale-one"])
    snap = collect_pending(str(tmp_path))

    assert [s.name for s in snap.suggestions] == []
    stale = [e for e in snap.errors if "stale status" in e]
    assert len(stale) == 1, snap.errors
    assert "stale-one" in stale[0]


def test_approved_with_stale_status_is_reported(tmp_path):
    _make_project(tmp_path, {"stale-two": "待立项"}, approved=["stale-two"])
    snap = collect_pending(str(tmp_path))

    assert [s.name for s in snap.suggestions] == []
    assert any("stale status" in e and "stale-two" in e for e in snap.errors)


def test_terminal_status_stays_silent(tmp_path):
    """A delivered item is not stale — it is simply not pending."""
    _make_project(tmp_path, {"done-one": "✅ **已归档**（2026-11-27）"},
                  archived=["done-one"])
    snap = collect_pending(str(tmp_path))

    assert [s.name for s in snap.suggestions] == []
    assert not [e for e in snap.errors if "stale status" in e]


def test_registry_token_is_terminal_and_not_pending(tmp_path):
    _make_project(tmp_path, {"landed": "✅ **已落地**（2026-11-27）"})
    snap = collect_pending(str(tmp_path))

    assert [s.name for s in snap.suggestions] == []
    assert not [e for e in snap.errors if "stale status" in e]


def test_real_pending_item_is_still_pending(tmp_path):
    _make_project(tmp_path, {"open-one": "待立项"})
    snap = collect_pending(str(tmp_path))

    assert [s.name for s in snap.suggestions] == ["open-one"]
    assert not snap.errors


# --- AC4: a broken front matter is located at field level --------------------


def test_broken_front_matter_reports_line_and_source(tmp_path):
    _make_project(tmp_path, {"broken-one": ("broken", None)})
    snap = collect_pending(str(tmp_path))

    errors = [e for e in snap.errors if "broken-one" in e]
    assert len(errors) == 1, snap.errors
    message = errors[0]
    assert "invalid YAML front matter" in message
    assert re.search(r"front-matter line \d+", message), message
    assert "状态" in message, message


# --- AC5: one definition point for the vocabulary ----------------------------


def test_help_renders_every_terminal_marker(capsys):
    from _lib.cli.status_cmd import cmd_status

    assert cmd_status(["--help"]) == 0
    out = capsys.readouterr().out
    for marker, _label in TERMINAL_MARKERS:
        assert marker in out, marker


#: The distinctive Chinese tokens — a copy of the vocabulary table would
#: necessarily contain them (the English ones are ordinary words elsewhere).
_DISTINCTIVE_MARKERS = ("已落地", "已拆分", "已取代")


def test_vocabulary_has_no_second_definition_point():
    """No second module may spell the vocabulary out again.

    Two shapes are forbidden: a copy of the table (⇒ the distinctive Chinese
    tokens appear twice) and a second table constant (⇒ another
    ``*TERMINAL*MARKER*`` name).
    """
    lib_root = Path(PROJECT_ROOT) / "_lib"
    offenders = []
    for path in lib_root.rglob("*.py"):
        if path.name == "improvement_status.py":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for marker in _DISTINCTIVE_MARKERS:
            if f'"{marker}"' in text or f"'{marker}'" in text:
                offenders.append(f"{path.relative_to(PROJECT_ROOT)}: token {marker}")
        for m in re.finditer(r"^([A-Z_]*TERMINAL[A-Z_]*MARKER[A-Z_]*)\s*[:=]", text, re.M):
            offenders.append(f"{path.relative_to(PROJECT_ROOT)}: constant {m.group(1)}")
    assert offenders == [], offenders


# --- AC3 (end-to-end): `rddf status` shows the stale entry -------------------


def test_status_view_shows_the_stale_entry(tmp_path, capsys, monkeypatch):
    from _lib.cli.status_cmd import cmd_status

    _make_project(tmp_path, {"stale-three": "🟢 已批准·待立项"}, archived=["stale-three"])
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))

    assert cmd_status([]) == 0
    out = capsys.readouterr().out
    assert "stale-three" in out
    assert "stale status" in out
