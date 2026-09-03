"""Tests for planner_audit."""
from __future__ import annotations

import pytest

from _lib.planner_audit import AuditRow, build_audit_rows, render_markdown, suggest_project_id


def _setup_roadmap(parent, themes):
    rmp = parent / ".rddf" / "roadmap.md"
    rmp.parent.mkdir(parents=True, exist_ok=True)
    rows = "\n".join(f"| phase-1 | {t} | active | | |" for t in themes)
    rmp.write_text(f"# Roadmap\n\n## Phase Skeleton\n| Phase | Theme | Status | Started | Done |\n|-------|-------|--------|---------|------|\n{rows}\n\n<!-- AUTO-INDEX -->\n")


def _setup_improvement(parent, name, *, priority="P2", feedback_block="", last_feedback_id=None):
    imp = parent / ".rddf" / "improvements" / f"{name}.md"
    imp.parent.mkdir(parents=True, exist_ok=True)
    fm = f"---\nname: {name}\npriority: {priority}\n"
    if last_feedback_id:
        fm += f"last_feedback_id: {last_feedback_id}\n"
    fm += "---\n# proposal\n"
    if feedback_block:
        fm += f"\n## Feedback\n\n{feedback_block}"
    imp.write_text(fm)


def test_suggest_project_id_exact_substring_match():
    assert suggest_project_id("add-foo-bar", ["foo bar", "baz"]) == "foo bar"


def test_suggest_project_id_no_match_returns_none():
    assert suggest_project_id("xyzzy-1234", ["foo bar"]) is None


def test_build_audit_rows_includes_unmapped_with_suggestion(tmp_path):
    _setup_roadmap(tmp_path, themes=["foo bar"])
    _setup_improvement(tmp_path, "add-foo-bar-baz")
    rows = build_audit_rows(tmp_path)
    assert len(rows) == 1
    r = rows[0]
    assert r.propro == "add-foo-bar-baz"
    assert r.priority == "P2"
    assert r.suggested_project_id == "foo bar"


def test_build_audit_rows_groups_by_priority(tmp_path):
    _setup_roadmap(tmp_path, themes=["foo bar"])
    _setup_improvement(tmp_path, "a", priority="P0")
    _setup_improvement(tmp_path, "b", priority="P2")
    rows = build_audit_rows(tmp_path)
    priorities = [r.priority for r in rows]
    assert priorities[0] == "P0"


def test_build_audit_rows_marks_feedback_status(tmp_path):
    _setup_roadmap(tmp_path, themes=["foo bar"])
    _setup_improvement(tmp_path, "needs-rev", priority="P1",
                       feedback_block="### fb-x\n- **kind**: needs-revision\n- **resolution**: open\n",
                       last_feedback_id="fb-x")
    rows = build_audit_rows(tmp_path)
    assert rows[0].feedback_status == "needs-revision"


def test_build_audit_rows_excludes_mapped_proposals(tmp_path):
    _setup_roadmap(tmp_path, themes=["foo bar"])
    _setup_improvement(tmp_path, "mapped", priority="P2", feedback_block="",
                       last_feedback_id=None)
    (tmp_path / ".rddf" / "improvements" / "mapped.md").write_text(
        "---\nname: mapped\npriority: P2\nroadmap_ref:\n  project_id: foo bar\n  phase: phase-1\n---\n# x\n"
    )
    rows = build_audit_rows(tmp_path)
    assert rows == []


def test_render_markdown_outputs_human_table():
    rows = [
        AuditRow(propro="x", priority="P2", feedback_status="none", suggested_project_id="foo bar"),
        AuditRow(propro="y", priority="P0", feedback_status="needs-revision", suggested_project_id=None),
    ]
    md = render_markdown(rows)
    assert "| Proposal | Priority | Feedback | Suggested project_id |" in md
    assert "| x | P2 | none | foo bar |" in md
    assert "| y | P0 | needs-revision | _(manual)_ |" in md


def test_render_markdown_empty():
    md = render_markdown([])
    assert "_No unmapped proposals._" in md