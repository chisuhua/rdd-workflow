"""Tests for planner_state (atomic state I/O)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from _lib.planner_state import (
    PlannerStateError,
    SchemaMismatchError,
    current_sprint_id,
    read_state,
    write_state,
    STATE_FILENAME,
    SCHEMA_VERSION,
)


def test_current_sprint_id_format():
    """current_sprint_id returns YYYY-MM sprint id."""
    sid = current_sprint_id()
    import re
    assert re.match(r"^sprint-\d{4}-\d{2}$", sid)


def test_read_state_returns_empty_when_missing(tmp_path):
    """read_state on missing file returns default empty state."""
    state = read_state(tmp_path)
    assert state["version"] == 1
    assert state["current_sprint"].startswith("sprint-")
    assert state["active_projects"] == []


def test_write_then_read_state_roundtrip(tmp_path):
    """write_state then read_state returns identical dict."""
    sample = {
        "version": 1,
        "current_sprint": "sprint-2026-09",
        "last_sync_at": "2026-09-03T10:30:00+08:00",
        "active_projects": [
            {
                "project_id": "foo",
                "phase": "phase-2",
                "priority": "P1",
                "status": "active",
            }
        ],
        "unmapped_proposals": ["bar"],
        "synced_proposals": ["foo"],
    }
    write_state(tmp_path, sample)
    loaded = read_state(tmp_path)
    assert loaded == sample


def test_write_state_validates_against_schema(tmp_path):
    """write_state rejects invalid data."""
    bad = {"version": 1, "current_sprint": "not-a-sprint-id", "last_sync_at": "2026-09-03T10:30:00+08:00"}
    with pytest.raises(PlannerStateError, match="validation failed"):
        write_state(tmp_path, bad)


def test_read_state_rejects_wrong_version(tmp_path):
    """read_state raises SchemaMismatchError for v2 state."""
    state_path = tmp_path / ".rddf" / "state" / STATE_FILENAME
    state_path.parent.mkdir(parents=True)
    state_path.write_text(json.dumps({"version": 2, "current_sprint": "sprint-2026-09", "last_sync_at": "2026-09-03T10:30:00+08:00"}))
    with pytest.raises(SchemaMismatchError, match="version 2"):
        read_state(tmp_path)


def test_write_state_creates_parent_directory(tmp_path):
    """write_state creates .rddf/state/ if missing."""
    sample = {"version": 1, "current_sprint": "sprint-2026-09", "last_sync_at": "2026-09-03T10:30:00+08:00"}
    write_state(tmp_path, sample)
    expected = tmp_path / ".rddf" / "state" / STATE_FILENAME
    assert expected.exists()


def test_write_state_atomic_creates_lock_file(tmp_path):
    """write_state acquires FileLock during write."""
    import _lib.planner_state as state_mod
    sample = {"version": 1, "current_sprint": "sprint-2026-09", "last_sync_at": "2026-09-03T10:30:00+08:00"}
    called = []
    original = state_mod.FileLock
    def spy(*args, **kw):
        called.append(args)
        return original(*args, **kw)
    state_mod.FileLock = spy
    try:
        write_state(tmp_path, sample)
    finally:
        state_mod.FileLock = original
    assert any(str(tmp_path / ".rddf" / "state" / ".planner-state.json.lock") in str(a) for a in called)


def test_default_state_has_all_required_fields(tmp_path):
    """_default_state contains all required schema fields."""
    state = read_state(tmp_path)
    assert state["version"] == 1
    assert "current_sprint" in state
    assert "last_sync_at" in state
    assert isinstance(state["active_projects"], list)
    assert isinstance(state["unmapped_proposals"], list)
    assert isinstance(state["synced_proposals"], list)


def test_update_state_modifies_under_lock(tmp_path):
    from _lib.planner_state import write_state, read_state, update_state
    initial = read_state(tmp_path)
    write_state(tmp_path, initial)

    def mutator(state):
        state["current_sprint"] = "sprint-2026-10"
        return state

    res = update_state(tmp_path, mutator)
    assert res["current_sprint"] == "sprint-2026-10"
    loaded = read_state(tmp_path)
    assert loaded["current_sprint"] == "sprint-2026-10"


def test_update_state_fails_if_no_state_file(tmp_path):
    from _lib.planner_state import update_state, PlannerStateError
    with pytest.raises(PlannerStateError, match="No state file found"):
        update_state(tmp_path, lambda s: s)