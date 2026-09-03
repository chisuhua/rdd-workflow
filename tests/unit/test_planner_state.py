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