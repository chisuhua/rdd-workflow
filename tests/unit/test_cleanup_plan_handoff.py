"""Tests for clean-stale-plan-handoff-on-ship-done: 4 Python branches in cleanup_plan_handoff()."""
from __future__ import annotations

import json
from pathlib import Path


def _load_cleanup_function():
    """Source-load the module under test.

    ship_archive.sh has an inline Python block inside a bash function.
    To test it, we call the extracted Python module that the inline
    block now delegates to (skills._lib.cleanup_plan_handoff).
    """
    from skills._lib.cleanup_plan_handoff import cleanup_plan_handoff
    return cleanup_plan_handoff


def test_branch1_current_change_matches_change_name(tmp_path: Path) -> None:
    """Branch 1: change_name == current_change → current_change becomes None."""
    cleanup = _load_cleanup_function()
    handoff = tmp_path / ".plan-handoff.json"
    handoff.write_text(json.dumps({
        "plan_complete_at": "2026-08-22T12:00:00+00:00",
        "active_changes": 1,
        "all_artifacts_committed": True,
        "ship_started_at": "2026-08-22T13:00:00+00:00",
        "current_change": "fix-foo",
        "execution_mode_decisions": {"fix-foo": "worktree"},
        "archived_changes": [],
    }))

    cleanup(handoff, "fix-foo")

    result = json.loads(handoff.read_text())
    assert result["active_changes"] == 0
    assert result["current_change"] is None
    assert result["archived_changes"] == ["fix-foo"]
    # execution_mode_decisions preserved (historical)
    assert result["execution_mode_decisions"] == {"fix-foo": "worktree"}


def test_branch2_active_changes_zero_resets_ship_started_at(tmp_path: Path) -> None:
    """Branch 2: active_changes reaches 0 → ship_started_at becomes None."""
    cleanup = _load_cleanup_function()
    handoff = tmp_path / ".plan-handoff.json"
    handoff.write_text(json.dumps({
        "active_changes": 1,
        "current_change": "fix-foo",
        "ship_started_at": "2026-08-22T13:00:00+00:00",
        "archived_changes": [],
    }))

    cleanup(handoff, "fix-foo")

    result = json.loads(handoff.read_text())
    assert result["active_changes"] == 0
    assert result["ship_started_at"] is None


def test_branch3_current_change_mismatch_preserved(tmp_path: Path) -> None:
    """Branch 3: change_name != current_change → current_change preserved."""
    cleanup = _load_cleanup_function()
    handoff = tmp_path / ".plan-handoff.json"
    handoff.write_text(json.dumps({
        "active_changes": 2,
        "current_change": "fix-foo",
        "ship_started_at": "2026-08-22T13:00:00+00:00",
        "archived_changes": [],
    }))

    cleanup(handoff, "fix-bar")

    result = json.loads(handoff.read_text())
    assert result["active_changes"] == 1
    assert result["current_change"] == "fix-foo", "must NOT clobber"
    assert result["archived_changes"] == ["fix-bar"]


def test_branch4_idempotent_when_already_zero(tmp_path: Path) -> None:
    """Branch 4: active_changes already 0 → stay 0, no negatives."""
    cleanup = _load_cleanup_function()
    handoff = tmp_path / ".plan-handoff.json"
    handoff.write_text(json.dumps({
        "active_changes": 0,
        "current_change": None,
        "ship_started_at": None,
        "archived_changes": ["fix-prior"],
    }))

    cleanup(handoff, "fix-new")

    result = json.loads(handoff.read_text())
    assert result["active_changes"] == 0
    assert result["archived_changes"] == ["fix-prior", "fix-new"]