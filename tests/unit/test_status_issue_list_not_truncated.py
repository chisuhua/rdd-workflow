"""`rddf status` must not truncate the issue list it reports.

Regression background (fix-status-issue-list-truncation): the status view
printed the **true count** in the heading but only the first five entries
(`for err in snapshot.errors[:5]`) ⇒ the sixth issue was invisible — the same
"silent failure" class that fix-rddf-status-terminal-markers had just removed
one layer up. Measured on CppTLM (2026-11-27): "6 improvement issue(s)" with
5 lines printed.

Two rules are pinned here:
1. every reported issue is listed — or the remainder is announced explicitly;
2. a status snippet is trimmed at a safe boundary (no half-open quotes).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from _lib.dashboard import collect_pending  # noqa: E402
from _lib.dashboard.improvement_status import clean_status_snippet  # noqa: E402


def _write_improvement(root: Path, name: str, status: str) -> None:
    imp_dir = root / ".rddf" / "improvements"
    imp_dir.mkdir(parents=True, exist_ok=True)
    (imp_dir / f"{name}.md").write_text(
        "---\n优先级: P1\n"
        f"状态: {status}\n"
        "---\n\n"
        f"# {name}\n",
        encoding="utf-8",
    )


def _make_stale_project(tmp_path, count: int, status: str = "🟢 已批准·待立项"):
    """`count` archived improvements whose status line is not terminal."""
    for i in range(count):
        name = f"stale-{i:02d}"
        _write_improvement(tmp_path, name, status)
        d = tmp_path / "openspec" / "changes" / "archive" / f"2026-11-01-{name}"
        d.mkdir(parents=True, exist_ok=True)
        (d / "tasks.md").write_text("- [x] a\n", encoding="utf-8")
    (tmp_path / "improvement-approved.md").write_text(
        "## 已批准提案\n\n| 提案 | 优先级 | 批准时间 | 批准者 |\n|---|---|---|---|\n",
        encoding="utf-8",
    )
    return tmp_path


def _status_output(tmp_path, monkeypatch, capsys):
    from _lib.cli.status_cmd import cmd_status

    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    assert cmd_status([]) == 0
    return capsys.readouterr().out


# --- AC1: every issue is listed; the heading count matches ------------------


def test_six_issues_are_all_listed(tmp_path, monkeypatch, capsys):
    _make_stale_project(tmp_path, 6)
    out = _status_output(tmp_path, monkeypatch, capsys)

    listed = [line for line in out.splitlines() if line.strip().startswith("- stale-")]
    assert len(listed) == 6, out
    assert "6 improvement issue(s)" in out
    # No silent remainder: everything the heading promises is on screen.
    assert "还有" not in out


def test_no_issue_section_when_there_is_nothing_to_report(tmp_path, monkeypatch, capsys):
    _write_improvement(tmp_path, "open-one", "待立项")
    out = _status_output(tmp_path, monkeypatch, capsys)
    assert "improvement issue(s)" not in out


# --- AC2: beyond the limit the remainder is announced explicitly -------------


def test_beyond_limit_announces_the_remainder(tmp_path, monkeypatch, capsys):
    _make_stale_project(tmp_path, 30)
    out = _status_output(tmp_path, monkeypatch, capsys)

    listed = [line for line in out.splitlines() if line.strip().startswith("- stale-")]
    assert len(listed) == 20, out
    assert "还有 10 条未展开" in out
    assert "rddf dashboard" in out
    # The heading must not pretend that all 30 were listed.
    assert "30 improvement issue(s)" in out
    assert "列出前 20" in out


def test_the_limit_is_pinned_by_a_test(tmp_path, monkeypatch, capsys):
    """The threshold is a contract, not a magic number that can shrink silently."""
    from _lib.cli import status_cmd

    assert status_cmd.STATUS_ISSUE_LIST_LIMIT == 20


# --- AC3: snippets are trimmed at a safe boundary ---------------------------


def test_long_status_snippet_is_trimmed_at_a_safe_boundary(tmp_path, monkeypatch, capsys):
    # The 「 lands inside the 40-char window, its 」 does not ⇒ a naive
    # `raw[:40]` would leave a half-open quote on screen.
    long_status = ("🟢 **已批准·待立项**(2026-11-26 · 用户批准 5 段设计 ·"
                   "「700」 · 后续说明继续延伸以超出长度上限)")
    _make_stale_project(tmp_path, 1, status=long_status)
    out = _status_output(tmp_path, monkeypatch, capsys)

    snippet_lines = [line for line in out.splitlines() if "stale status —" in line]
    assert snippet_lines, out
    line = snippet_lines[0]
    assert "…" in line, line
    assert line.count("「") == line.count("」"), line
    assert line.count("**") % 2 == 0, line


def test_short_status_snippet_is_untouched():
    """A short status is cleaned (markup stripped) but NOT truncated."""
    assert clean_status_snippet("🟢 **已批准·待立项**(2026-11-26)", 40) == (
        "🟢 已批准·待立项 (2026-11-26)"
    )


def test_snippet_never_leaves_a_half_open_quote():
    raw = "「" + "x" * 80 + "」"
    snippet = clean_status_snippet(raw, 40)
    assert snippet.endswith("…")
    assert snippet.count("「") == snippet.count("」")


# --- AC5: one cleaning implementation ---------------------------------------


def test_snippet_cleaner_is_the_shared_one():
    from _lib.dashboard import improvement_status

    assert collect_pending.__module__  # module import sanity
    import _lib.dashboard as dashboard

    assert dashboard.clean_status_snippet is improvement_status.clean_status_snippet


def test_no_second_cleaner_definition():
    lib_root = Path(PROJECT_ROOT) / "_lib"
    definitions = [
        str(path.relative_to(PROJECT_ROOT))
        for path in lib_root.rglob("*.py")
        if re.search(r"^def clean_status_snippet", path.read_text(encoding="utf-8"), re.M)
    ]
    assert definitions == ["_lib/dashboard/improvement_status.py"], definitions
