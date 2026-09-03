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


def _make_improvement(parent: Path, name: str, *, priority: str = "P2", roadmap_ref: dict | None = None, feedback_block: str = "", last_feedback_id: str | None = None):
    imp_dir = parent / ".rddf" / "improvements"
    imp_dir.mkdir(parents=True, exist_ok=True)
    f = imp_dir / f"{name}.md"
    fm = f"---\nname: {name}\npriority: {priority}\n"
    if roadmap_ref:
        fm += f"roadmap_ref: {json.dumps(roadmap_ref)}\n"
    if last_feedback_id:
        fm += f"last_feedback_id: {last_feedback_id}\n"
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


def test_apply_state_delegates_to_roadmap_sprint_update_roadmap(monkeypatch, tmp_path):
    """apply_state calls roadmap_sprint.update_roadmap with table='project'."""
    from _lib import roadmap_sprint as rs_mod
    captured = {}
    def fake_update(roadmap_path, data, *, table="changes"):
        captured["path"] = roadmap_path
        captured["data"] = data
        captured["table"] = table
        return None
    monkeypatch.setattr(rs_mod, "update_roadmap", fake_update)
    roadmap = tmp_path / ".rddf" / "roadmap.md"
    roadmap.parent.mkdir(parents=True)
    roadmap.write_text("# R\n")
    state = {
        "version": 1,
        "current_sprint": "sprint-2026-09",
        "last_sync_at": "2026-09-03T10:30:00+00:00",
        "last_sync_status": "ok",
        "active_projects": [],
        "unmapped_proposals": [],
        "synced_proposals": [],
    }
    apply_state(tmp_path, state)
    assert captured["table"] == "project"
    assert captured["data"]["current_sprint"] == "sprint-2026-09"


def test_parse_feedback_status_uses_last_feedback_id(tmp_path):
    """Historical needs-revision followed by resolved current entry -> resolved."""
    f = _make_improvement(tmp_path, "x",
        feedback_block=(
            "### feedback-20260101-001\n- **kind**: needs-revision\n- **resolution**: open\n\n"
            "### feedback-20260202-001\n- **kind**: needs-revision\n- **resolution**: resolved\n"
        ),
        last_feedback_id="feedback-20260202-001",
    )
    assert parse_feedback_status(f) == "resolved"


def test_parse_feedback_status_returns_noted_for_blocked(tmp_path):
    f = _make_improvement(tmp_path, "x",
        feedback_block="### feedback-x\n- **kind**: blocked\n- **resolution**: open\n",
        last_feedback_id="feedback-x",
    )
    assert parse_feedback_status(f) == "noted"


def test_parse_feedback_status_stops_at_next_top_level_section(tmp_path):
    f = _make_improvement(tmp_path, "x",
        feedback_block=(
            "### feedback-x\n- **kind**: needs-revision\n- **resolution**: open\n\n"
            "## Unrelated\n\n- **kind**: rejected\n"
        ),
        last_feedback_id="feedback-x",
    )
    assert parse_feedback_status(f) == "needs-revision"


def test_parse_feedback_status_fails_closed_on_missing_pointer_entry(tmp_path):
    f = _make_improvement(tmp_path, "x",
        feedback_block="### feedback-20260101-001\n- **kind**: needs-revision\n- **resolution**: open\n",
        last_feedback_id="feedback-does-not-exist",
    )
    assert parse_feedback_status(f) == "none"


def test_apply_state_accepts_noted_feedback(tmp_path):
    """sync --apply must accept noted feedback_status (schema includes 'noted')."""
    _make_improvement(tmp_path, "mapped",
        roadmap_ref={"project_id": "p", "phase": "phase-2"},
        feedback_block="### feedback-x\n- **kind**: blocked\n- **resolution**: open\n",
        last_feedback_id="feedback-x",
    )
    state = render_state(tmp_path)
    apply_state(tmp_path, state)


def test_diff_state_no_baseline_returns_empty_diff(tmp_path):
    from _lib.planner_sync import diff_state
    diff = diff_state(project_root=tmp_path)
    assert diff["has_baseline"] is False
    assert diff["unmapped_diff"] == {"added": [], "removed": []}
    assert diff["projects_diff"] == {}


def test_diff_state_identical_when_stored_equals_computed(tmp_path):
    from _lib.planner_state import write_state
    _make_improvement(tmp_path, "m", roadmap_ref={"project_id": "p", "phase": "phase-2"})
    state = render_state(tmp_path)
    write_state(tmp_path, state)
    from _lib.planner_sync import diff_state
    diff = diff_state(project_root=tmp_path)
    assert diff["has_baseline"] is True
    assert diff["unmapped_diff"] == {"added": [], "removed": []}
    assert diff["projects_diff"] == {}


def test_diff_state_detects_newly_unmapped(tmp_path):
    from _lib.planner_state import write_state
    _make_improvement(tmp_path, "u1")
    write_state(tmp_path, render_state(tmp_path))
    _make_improvement(tmp_path, "u2")
    from _lib.planner_sync import diff_state
    diff = diff_state(project_root=tmp_path)
    assert "u2" in diff["unmapped_diff"]["added"]
    assert diff["unmapped_diff"]["removed"] == []


def test_apply_state_with_warnings_emits_newly_unmapped(tmp_path, capsys):
    """Second sync warns only about newly added unmapped proposals."""
    _make_improvement(tmp_path, "u1")
    from _lib.planner_sync import apply_state_with_warnings
    apply_state_with_warnings(tmp_path, render_state(tmp_path))
    capsys.readouterr()
    _make_improvement(tmp_path, "u2")
    msg = apply_state_with_warnings(tmp_path, render_state(tmp_path))
    assert "u2" in msg
    assert "u1" not in msg


def test_apply_state_with_warnings_no_warning_when_baseline_equals_current(tmp_path, capsys):
    """First run suppresses full-list warning (baseline == current)."""
    _make_improvement(tmp_path, "u1")
    _make_improvement(tmp_path, "u2")
    from _lib.planner_sync import apply_state_with_warnings
    msg = apply_state_with_warnings(tmp_path, render_state(tmp_path))
    assert msg == ""
    captured = capsys.readouterr()
    assert "newly unmapped" not in captured.out.lower()


def test_advance_sprint_enforces_forward_only(tmp_path):
    from _lib.planner_state import write_state
    from _lib.planner_sync import advance_sprint, SyncError
    write_state(tmp_path, {
        "version": 1,
        "current_sprint": "sprint-2026-09",
        "last_sync_at": "2026-09-03T10:00:00Z",
        "sprint_started_at": "2026-09-01T00:00:00Z",
        "active_projects": [],
        "unmapped_proposals": [],
        "synced_proposals": [],
    })
    with pytest.raises(SyncError, match="must move forward"):
        advance_sprint(tmp_path, to_sprint="sprint-2026-08")


def test_advance_sprint_success_records_history_and_updates_state(tmp_path):
    from _lib.planner_state import write_state, read_state
    from _lib.planner_history import read_history
    from _lib.planner_sync import advance_sprint
    rm_file = tmp_path / ".rddf" / "roadmap.md"
    rm_file.parent.mkdir(parents=True, exist_ok=True)
    rm_file.write_text("# Roadmap\n## Phase Skeleton\n<!-- AUTO-INDEX -->\n")
    write_state(tmp_path, {
        "version": 1,
        "current_sprint": "sprint-2026-09",
        "last_sync_at": "2026-09-03T10:00:00Z",
        "sprint_started_at": "2026-09-01T00:00:00Z",
        "active_projects": [{"project_id": "p1", "phase": "p", "priority": "P1", "status": "active", "proposal": "pr1"}],
        "unmapped_proposals": [],
        "synced_proposals": ["pr1"],
    })

    res = advance_sprint(tmp_path, to_sprint="sprint-2026-10")
    assert res["old_sprint"] == "sprint-2026-09"
    assert res["new_sprint"] == "sprint-2026-10"

    entries, _ = read_history(tmp_path)
    assert len(entries) == 1
    assert entries[0].sprint == "sprint-2026-09"

    st = read_state(tmp_path)
    assert st["current_sprint"] == "sprint-2026-10"
    assert st["sprint_started_at"] != "2026-09-01T00:00:00Z"


def test_parse_feedback_status_logs_when_pointer_missing(tmp_path, caplog):
    """When last_feedback_id points to a missing block, parser logs a warning."""
    import logging
    f = _make_improvement(tmp_path, "x",
        feedback_block="### feedback-20260101-001\n- **kind**: needs-revision\n- **resolution**: open\n",
        last_feedback_id="feedback-does-not-exist",
    )
    with caplog.at_level(logging.WARNING, logger="_lib.planner_sync"):
        result = parse_feedback_status(f)
    assert result == "none"
    assert any("feedback-does-not-exist" in r.message for r in caplog.records)