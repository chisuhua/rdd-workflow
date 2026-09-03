"""Tests for planner_sync (discover + render + apply)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from _lib.planner_sync import (
    SyncError,
    apply_state,
    discover_projects,
    parse_feedback_status,
    render_state,
)


def _make_improvement(parent: Path, name: str, *, priority: str = "P2", roadmap_ref: dict | None = None, feedback_block: str = ""):
    imp_dir = parent / ".rddf" / "improvements"
    imp_dir.mkdir(parents=True, exist_ok=True)
    f = imp_dir / f"{name}.md"
    fm = f"---\nname: {name}\npriority: {priority}\n"
    if roadmap_ref:
        fm += f"roadmap_ref: {json.dumps(roadmap_ref)}\n"
    fm += "---\n# proposal\n"
    if feedback_block:
        fm += "\n## Feedback\n\n" + feedback_block
    f.write_text(fm)
    return f


def test_discover_projects_returns_all_improvements(tmp_path):
    """discover_projects scans all *.md in .rddf/improvements/."""
    _make_improvement(tmp_path, "foo")
    _make_improvement(tmp_path, "bar")
    projects = discover_projects(tmp_path)
    names = {p["proposal"] for p in projects}
    assert names == {"foo", "bar"}


def test_discover_projects_extracts_roadmap_ref(tmp_path):
    """discover_projects reads frontmatter.roadmap_ref when present."""
    _make_improvement(tmp_path, "mapped", roadmap_ref={"project_id": "p1", "phase": "phase-2", "theme": "t1"})
    projects = discover_projects(tmp_path)
    p = next(p for p in projects if p["proposal"] == "mapped")
    assert p["project_id"] == "p1"
    assert p["phase"] == "phase-2"
    assert p["theme"] == "t1"
    assert p["mapped"] is True


def test_discover_projects_marks_unmapped(tmp_path):
    """discover_projects flags proposals without roadmap_ref as mapped=False."""
    _make_improvement(tmp_path, "unmapped")
    projects = discover_projects(tmp_path)
    p = next(p for p in projects if p["proposal"] == "unmapped")
    assert p["mapped"] is False
    assert p["phase"] == "unmapped"


def test_parse_feedback_status_returns_none_when_no_feedback(tmp_path):
    """parse_feedback_status returns 'none' when ## Feedback section absent."""
    f = _make_improvement(tmp_path, "x")
    assert parse_feedback_status(f) == "none"


def test_parse_feedback_status_detects_needs_revision(tmp_path):
    """parse_feedback_status returns 'needs-revision' when ## Feedback has that kind."""
    f = _make_improvement(tmp_path, "x", feedback_block="### fb\n- **kind**: needs-revision\n- **resolution**: open\n")
    assert parse_feedback_status(f) == "needs-revision"


def test_parse_feedback_status_detects_rejected(tmp_path):
    f = _make_improvement(tmp_path, "x", feedback_block="### fb\n- **kind**: rejected\n- **resolution**: open\n")
    assert parse_feedback_status(f) == "rejected"


def test_parse_feedback_status_detects_ac_fail(tmp_path):
    f = _make_improvement(tmp_path, "x", feedback_block="### fb\n- **kind**: ac-fail\n- **resolution**: open\n")
    assert parse_feedback_status(f) == "needs-revision"


def test_render_state_returns_valid_dict(tmp_path):
    """render_state returns a dict with all required keys."""
    _make_improvement(tmp_path, "foo", roadmap_ref={"project_id": "p1", "phase": "phase-2", "theme": "t"})
    state = render_state(tmp_path)
    assert state["version"] == 1
    assert state["current_sprint"].startswith("sprint-")
    assert isinstance(state["active_projects"], list)
    assert len(state["active_projects"]) == 1
    assert state["active_projects"][0]["project_id"] == "p1"


def test_render_state_separates_unmapped(tmp_path):
    """render_state populates unmapped_proposals for files without roadmap_ref."""
    _make_improvement(tmp_path, "unmapped1")
    _make_improvement(tmp_path, "unmapped2")
    _make_improvement(tmp_path, "mapped", roadmap_ref={"project_id": "p1", "phase": "phase-1"})
    state = render_state(tmp_path)
    assert set(state["unmapped_proposals"]) == {"unmapped1", "unmapped2"}
    assert len(state["active_projects"]) == 1


def test_render_state_warn_when_unmapped(tmp_path):
    """render_state sets last_sync_status=warn when unmapped proposals exist."""
    _make_improvement(tmp_path, "u1")
    state = render_state(tmp_path)
    assert state["last_sync_status"] == "warn"


def test_render_state_ok_when_all_mapped(tmp_path):
    """render_state sets last_sync_status=ok when no unmapped proposals."""
    _make_improvement(tmp_path, "m", roadmap_ref={"project_id": "p", "phase": "phase-1"})
    state = render_state(tmp_path)
    assert state["last_sync_status"] == "ok"


def test_apply_state_writes_planner_state_and_roadmap(tmp_path):
    """apply_state writes both .planner-state.json and updates roadmap.md."""
    _make_improvement(tmp_path, "x", roadmap_ref={"project_id": "p", "phase": "phase-1"})
    roadmap = tmp_path / ".rddf" / "roadmap.md"
    roadmap.write_text("# Roadmap\n\n## Phase Skeleton\n| Phase | Theme |\n|-------|-------|\n| phase-1 | t |\n\n<!-- AUTO-INDEX -->\n")
    state = render_state(tmp_path)
    apply_state(tmp_path, state)
    assert (tmp_path / ".rddf" / "state" / ".planner-state.json").exists()
    updated = roadmap.read_text()
    assert "<!-- AUTO-SPRINT-START -->" in updated
    assert "<!-- AUTO-SPRINT-END -->" in updated
    assert "Phase Skeleton" in updated