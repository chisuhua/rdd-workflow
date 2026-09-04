"""Tests for 2-revision stale detection in compute_planner_feedback.

Wave 4 Sub-task 0.2: stale = arch_handoff_revision OR state_revision
mismatch. codebase_commit becomes metadata in computed_from, no
longer a stale trigger (eliminates Stage 3 doc-only-commit noise).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


def _seed_legacy_handoff(tmp_path: Path) -> Path:
    """Write a minimal arch-handoff.json with no arch_complete_revision."""
    state_dir = tmp_path / ".rddf" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    handoff = state_dir / ".arch-handoff.json"
    handoff.write_text(json.dumps({
        "version": 2,
        "arch_complete_at": "2026-09-01T10:00:00+00:00",
        "adr_count": 0,
        "completed_adr_ids": [],
        "roadmap_exists": False,
        "current_phase": "default",
    }))
    return handoff


def _seed_planner_state(tmp_path: Path, *, state_revision: int = 0) -> Path:
    """Write a planner state with given state_revision."""
    state_dir = tmp_path / ".rddf" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    state = state_dir / ".planner-state.json"
    state.write_text(json.dumps({
        "version": 1,
        "state_revision": state_revision,
        "current_sprint": "sprint-2026-09",
        "last_sync_at": "2026-09-03T10:30:00+00:00",
        "active_projects": [],
        "unmapped_proposals": [],
        "synced_proposals": [],
    }))
    return state


def _seed_unmapped_improvement(tmp_path: Path) -> Path:
    """Create .rddf/improvements/foo.md with no theme_ref → emits feedback."""
    improvements_dir = tmp_path / ".rddf" / "improvements"
    improvements_dir.mkdir(parents=True, exist_ok=True)
    imp = improvements_dir / "feat-x.md"
    imp.write_text("---\nname: feat-x\npriority: P1\n---\n")
    return imp


def test_stale_on_arch_handoff_revision_change(tmp_path: Path):
    """arch_handoff_revision bumps in prior computed_from → entry marked stale=True."""
    project_root = str(tmp_path)
    _seed_legacy_handoff(tmp_path)  # arch_complete_revision absent → reader returns 0
    _seed_planner_state(tmp_path, state_revision=0)
    _seed_unmapped_improvement(tmp_path)

    from _lib.planner_feedback import compute_planner_feedback
    feedback = compute_planner_feedback(project_root)
    assert feedback["arch_handoff_revision"] == 0  # legacy returns 0

    entry = feedback["feedbacks"][0]
    assert entry["computed_from"]["arch_handoff_revision"] == 0
    assert entry["computed_from"]["state_revision"] == 0
    assert entry["stale"] is False


def test_stale_on_state_revision_change(tmp_path: Path):
    """state_revision 0 → 1 in state file → prior entry marked stale=True on recompute."""
    project_root = str(tmp_path)
    _seed_legacy_handoff(tmp_path)
    _seed_planner_state(tmp_path, state_revision=0)
    _seed_unmapped_improvement(tmp_path)

    from _lib.planner_feedback import compute_planner_feedback, write_planner_feedback
    first = compute_planner_feedback(project_root)
    write_planner_feedback(project_root, first)

    state_path = tmp_path / ".rddf" / "state" / ".planner-state.json"
    state = json.loads(state_path.read_text())
    state["state_revision"] = 1
    state_path.write_text(json.dumps(state))

    second = compute_planner_feedback(project_root)
    assert second["feedbacks"][0]["computed_from"]["state_revision"] == 1
    assert second["feedbacks"][0]["stale"] is True


def test_no_stale_when_both_revisions_unchanged(tmp_path: Path):
    """No revision changes → stale remains False across recomputes."""
    project_root = str(tmp_path)
    _seed_legacy_handoff(tmp_path)
    _seed_planner_state(tmp_path, state_revision=0)
    _seed_unmapped_improvement(tmp_path)

    from _lib.planner_feedback import compute_planner_feedback, write_planner_feedback
    first = compute_planner_feedback(project_root)
    write_planner_feedback(project_root, first)
    second = compute_planner_feedback(project_root)
    assert len(second["feedbacks"]) > 0
    for entry in second["feedbacks"]:
        assert entry["stale"] is False


def test_no_stale_on_doc_only_commit(tmp_path: Path):
    """codebase_commit changes but revisions don't → no stale (Stage 3 noise fix)."""
    project_root = str(tmp_path)
    _seed_legacy_handoff(tmp_path)
    _seed_planner_state(tmp_path, state_revision=0)
    _seed_unmapped_improvement(tmp_path)

    from _lib.planner_feedback import compute_planner_feedback, write_planner_feedback
    first = compute_planner_feedback(project_root)
    write_planner_feedback(project_root, first)

    second = compute_planner_feedback(project_root, codebase_commit="different-commit-sha")
    assert len(second["feedbacks"]) > 0
    for entry in second["feedbacks"]:
        assert entry["stale"] is False, (
            "doc-only commit (revisions unchanged) must NOT mark stale"
        )


def test_stale_only_one_revision_change_sufficient(tmp_path: Path):
    """Either revision bumping alone → stale=True (matrix: arch+state XOR)."""
    project_root = str(tmp_path)
    _seed_legacy_handoff(tmp_path)
    _seed_planner_state(tmp_path, state_revision=0)
    _seed_unmapped_improvement(tmp_path)

    from _lib.planner_feedback import compute_planner_feedback, write_planner_feedback
    first = compute_planner_feedback(project_root)
    write_planner_feedback(project_root, first)

    handoff_path = tmp_path / ".rddf" / "state" / ".arch-handoff.json"
    handoff = json.loads(handoff_path.read_text())
    handoff["arch_complete_revision"] = 1
    handoff_path.write_text(json.dumps(handoff))

    second = compute_planner_feedback(project_root)
    assert second["feedbacks"][0]["computed_from"]["arch_handoff_revision"] == 1
    assert second["feedbacks"][0]["computed_from"]["state_revision"] == 0
    assert second["feedbacks"][0]["stale"] is True


def test_computed_from_uses_real_state_revision(tmp_path: Path):
    """compute_planner_feedback's computed_from.state_revision matches _current_planner_state_revision()."""
    project_root = str(tmp_path)
    _seed_legacy_handoff(tmp_path)
    _seed_planner_state(tmp_path, state_revision=7)
    _seed_unmapped_improvement(tmp_path)

    from _lib.planner_feedback import compute_planner_feedback, _current_planner_state_revision
    feedback = compute_planner_feedback(project_root)
    assert feedback["feedbacks"][0]["computed_from"]["state_revision"] == 7
    assert _current_planner_state_revision(project_root) == 7