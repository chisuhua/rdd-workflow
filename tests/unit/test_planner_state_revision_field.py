"""Tests for state_revision field semantics in .planner-state.json.

state_revision is bumped by write_state/update_state when the semantic hash
(excluding timestamps + revision itself) differs from prior.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from _lib.planner_state import (
    STATE_FILENAME,
    SCHEMA_VERSION,
    _default_state,
    read_state,
    update_state,
    write_state,
)
from _lib.planner_feedback import _current_planner_state_revision


def test_default_state_has_state_revision_zero():
    """Fresh default state has state_revision=0."""
    state = _default_state()
    assert state.get("state_revision") == 0


def test_write_state_increments_on_semantic_change(tmp_path: Path):
    """Modifying unmapped_proposals → write → state_revision bumps."""
    state = _default_state()
    write_state(tmp_path, state)
    initial_rev = read_state(tmp_path)["state_revision"]

    def _mutate(s):
        s["unmapped_proposals"] = ["feat-x", "feat-y"]
        return s

    update_state(tmp_path, _mutate)
    after = read_state(tmp_path)
    assert after["state_revision"] == initial_rev + 1
    assert after["unmapped_proposals"] == ["feat-x", "feat-y"]


def test_write_state_no_increment_on_timestamp_only(tmp_path: Path):
    """Modifying only last_sync_at → write → state_revision unchanged."""
    state = _default_state()
    write_state(tmp_path, state)
    initial_rev = read_state(tmp_path)["state_revision"]

    def _bump_timestamp_only(s):
        s["last_sync_at"] = "2099-12-31T23:59:59+00:00"
        s["last_sync_status"] = "ok"
        return s

    update_state(tmp_path, _bump_timestamp_only)
    after = read_state(tmp_path)
    assert after["state_revision"] == initial_rev
    assert after["last_sync_at"] == "2099-12-31T23:59:59+00:00"


def test_write_state_no_increment_on_identical_content(tmp_path: Path):
    """Two writes of identical content → state_revision unchanged (second call)."""
    state = _default_state()
    state["unmapped_proposals"] = ["feat-a"]
    write_state(tmp_path, state)
    after_first = read_state(tmp_path)["state_revision"]

    write_state(tmp_path, state)
    after_second = read_state(tmp_path)["state_revision"]
    assert after_second == after_first


def test_current_planner_state_revision_reader_returns_real_value(tmp_path: Path):
    """_current_planner_state_revision returns real state_revision from disk."""
    assert _current_planner_state_revision(str(tmp_path)) == 0

    state = _default_state()
    state["unmapped_proposals"] = ["feat-z"]
    write_state(tmp_path, state)
    update_state(tmp_path, lambda s: s)  # no-op, semantic identical

    actual = _current_planner_state_revision(str(tmp_path))
    loaded = read_state(tmp_path)["state_revision"]
    assert actual == loaded
    assert actual >= 1


def test_schema_accepts_state_revision_field(tmp_path: Path):
    """Schema (v1) accepts state_revision as optional additive field."""
    state = _default_state()
    assert "state_revision" in state
    assert isinstance(state["state_revision"], int)
    write_state(tmp_path, state)
    loaded = read_state(tmp_path)
    assert "state_revision" in loaded
    assert isinstance(loaded["state_revision"], int)
    assert loaded["state_revision"] >= 1  # baseline transition bumps 0→1


def test_schema_accepts_legacy_state_without_state_revision(tmp_path: Path):
    """Legacy state file (no state_revision field) still validates + reads."""
    state_path = tmp_path / ".rddf" / "state" / STATE_FILENAME
    state_path.parent.mkdir(parents=True, exist_ok=True)
    legacy = {
        "version": SCHEMA_VERSION,
        "current_sprint": "sprint-2026-09",
        "last_sync_at": "2026-09-03T10:30:00+08:00",
        "active_projects": [],
        "unmapped_proposals": [],
        "synced_proposals": [],
    }
    state_path.write_text(json.dumps(legacy))

    loaded = read_state(tmp_path)
    assert _current_planner_state_revision(str(tmp_path)) == 0
    assert loaded.get("state_revision", 0) == 0