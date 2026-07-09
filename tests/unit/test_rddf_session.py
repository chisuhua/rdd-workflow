"""Tests for RddfSessionCoordinator — user-perspective workflow session persistence (ADR-0017)."""
import json
import os
import time
from pathlib import Path

import jsonschema
import pytest

from skills._lib.rddf_session import RddfSessionCoordinator, RddfSessionError


@pytest.fixture
def sessions_file(tmp_path):
    return tmp_path / "sessions.json"


@pytest.fixture
def coordinator(sessions_file):
    return RddfSessionCoordinator(sessions_file=str(sessions_file))


def test_create_session_returns_valid_id(coordinator):
    """create_session MUST return id matching rds_<12 hex chars>."""
    sid = coordinator.create_session(
        kind="stage_plan",
        owner_opencode_session_id="ses_test123",
        goal={"intent": "guide-plan", "subject": "change-auth", "expected_outcome": "plan-done"},
    )
    assert sid.startswith("rds_")
    assert len(sid) == 16  # "rds_" + 12 hex


def test_create_session_persists_to_file(coordinator, sessions_file):
    """After create_session, sessions.json MUST contain the new entry."""
    sid = coordinator.create_session(
        kind="stage_arch",
        owner_opencode_session_id="ses_abc",
        goal={"intent": "guide-arch"},
    )
    assert sessions_file.exists()
    data = json.loads(sessions_file.read_text())
    assert len(data["sessions"]) == 1
    assert data["sessions"][0]["session_id"] == sid
    assert data["sessions"][0]["state"] == "active"
    assert data["sessions"][0]["kind"] == "stage_arch"


def test_create_session_writes_valid_schema(coordinator, sessions_file):
    """sessions.json output MUST pass sessions_schema.json validation."""
    sid = coordinator.create_session(
        kind="stage_ship",
        owner_opencode_session_id="ses_xyz",
        goal={"intent": "guide-ship", "subject": "change-x"},
    )
    schema_path = Path(__file__).resolve().parents[2] / "skills" / "_lib" / "schemas" / "sessions_schema.json"
    schema = json.loads(schema_path.read_text())
    data = json.loads(sessions_file.read_text())
    jsonschema.validate(instance=data, schema=schema)


def test_find_session_returns_session(coordinator):
    """find_session MUST return RddfSession for valid id, None otherwise."""
    sid = coordinator.create_session(kind="stage_plan", owner_opencode_session_id="ses_a", goal={})
    found = coordinator.find_session(sid)
    assert found is not None
    assert found.session_id == sid
    assert found.state == "active"


def test_find_session_returns_none_for_unknown(coordinator):
    assert coordinator.find_session("rds_nonexistent") is None


def test_list_sessions_returns_all(coordinator):
    """list_sessions MUST return all sessions, optionally filtered by kind.

    Note: only ONE active session per kind is allowed (cross-owner creates
    raise ConflictError), so this test uses distinct kinds for each session.
    """
    coordinator.create_session(kind="stage_arch", owner_opencode_session_id="ses_a", goal={})
    coordinator.create_session(kind="stage_plan", owner_opencode_session_id="ses_a", goal={})
    coordinator.create_session(kind="stage_ship", owner_opencode_session_id="ses_b", goal={})
    all_sessions = coordinator.list_sessions()
    assert len(all_sessions) == 3
    plan_only = coordinator.list_sessions(kind="stage_plan")
    assert len(plan_only) == 1
    assert all(s.kind == "stage_plan" for s in plan_only)


def test_update_session_status_valid(coordinator):
    """update_session_status MUST transition active → completed/failed."""
    sid = coordinator.create_session(kind="stage_arch", owner_opencode_session_id="ses_a", goal={})
    coordinator.update_session_status(sid, "completed", end_reason="arch-done")
    found = coordinator.find_session(sid)
    assert found.state == "completed"
    assert found.end_reason == "arch-done"
    assert found.ended_at is not None


def test_update_session_status_terminal_blocks(coordinator):
    """update_session_status MUST NOT allow transitions from terminal states (completed/failed/abandoned)."""
    sid = coordinator.create_session(kind="stage_arch", owner_opencode_session_id="ses_a", goal={})
    coordinator.update_session_status(sid, "completed", end_reason="x")
    with pytest.raises(RddfSessionError):
        coordinator.update_session_status(sid, "active")