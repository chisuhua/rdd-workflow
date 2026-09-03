"""Tests for planner_sync (discover + render + apply)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from _lib.planner_sync import (
    SyncError,
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