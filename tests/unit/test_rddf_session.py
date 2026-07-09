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


def test_attach_change(coordinator):
    """attach_change MUST add change_name to session's attached_changes."""
    sid = coordinator.create_session(kind="stage_plan", owner_opencode_session_id="ses_a", goal={})
    coordinator.attach_change(sid, "change-auth")
    coordinator.attach_change(sid, "change-user-profile")
    found = coordinator.find_session(sid)
    assert "change-auth" in found.attached_changes
    assert "change-user-profile" in found.attached_changes
    assert len(found.attached_changes) == 2


def test_attach_change_idempotent(coordinator):
    """attach_change MUST NOT duplicate existing entries."""
    sid = coordinator.create_session(kind="stage_plan", owner_opencode_session_id="ses_a", goal={})
    coordinator.attach_change(sid, "change-auth")
    coordinator.attach_change(sid, "change-auth")
    found = coordinator.find_session(sid)
    assert found.attached_changes.count("change-auth") == 1


def test_detach_change(coordinator):
    """detach_change MUST remove change_name from attached_changes."""
    sid = coordinator.create_session(kind="stage_plan", owner_opencode_session_id="ses_a", goal={})
    coordinator.attach_change(sid, "change-auth")
    coordinator.detach_change(sid, "change-auth")
    found = coordinator.find_session(sid)
    assert "change-auth" not in found.attached_changes


def test_refresh_heartbeat(coordinator):
    """refresh_heartbeat MUST update last_heartbeat to now."""
    sid = coordinator.create_session(kind="stage_plan", owner_opencode_session_id="ses_a", goal={})
    before = coordinator.find_session(sid).last_heartbeat
    time.sleep(0.01)
    coordinator.refresh_heartbeat(sid)
    after = coordinator.find_session(sid).last_heartbeat
    assert after >= before


def test_check_heartbeat_timeouts_marks_orphaned(coordinator, sessions_file):
    """Sessions with last_heartbeat > 30min ago MUST be marked orphaned."""
    sid = coordinator.create_session(kind="stage_plan", owner_opencode_session_id="ses_a", goal={})
    # Manually backdate last_heartbeat to 2020 (well past 30min)
    data = json.loads(sessions_file.read_text())
    for s in data["sessions"]:
        if s["session_id"] == sid:
            s["last_heartbeat"] = "2020-01-01T00:00:00+00:00"
    sessions_file.write_text(json.dumps(data))
    newly_orphaned = coordinator.check_heartbeat_timeouts()
    assert sid in newly_orphaned
    found = coordinator.find_session(sid)
    assert found.state == "orphaned"
    assert found.end_reason == "heartbeat-timeout"


def test_check_heartbeat_timeouts_keeps_fresh(coordinator):
    """Sessions with fresh heartbeat MUST NOT be marked orphaned."""
    sid = coordinator.create_session(kind="stage_plan", owner_opencode_session_id="ses_a", goal={})
    newly_orphaned = coordinator.check_heartbeat_timeouts()
    assert sid not in newly_orphaned
    found = coordinator.find_session(sid)
    assert found.state == "active"


def test_detect_conflict_none_when_no_active(coordinator):
    """detect_conflict MUST return None when no active session of that kind exists."""
    result = coordinator.detect_conflict("stage_plan", owner_opencode_session_id="ses_a")
    assert result is None


def test_detect_conflict_none_when_same_owner(coordinator):
    """detect_conflict MUST return None when active session owned by same opencode session."""
    coordinator.create_session(kind="stage_plan", owner_opencode_session_id="ses_a", goal={})
    result = coordinator.detect_conflict("stage_plan", owner_opencode_session_id="ses_a")
    assert result is None


def test_detect_conflict_returns_session_when_different_owner(coordinator):
    """detect_conflict MUST return existing session when owned by different opencode session."""
    coordinator.create_session(kind="stage_plan", owner_opencode_session_id="ses_a", goal={})
    result = coordinator.detect_conflict("stage_plan", owner_opencode_session_id="ses_b")
    assert result is not None
    assert result.owner_opencode_session_id == "ses_a"
    assert result.state == "active"


def test_transfer_ownership(coordinator):
    """transfer_ownership MUST update owner_opencode_session_id and refresh heartbeat."""
    sid = coordinator.create_session(kind="stage_plan", owner_opencode_session_id="ses_a", goal={})
    coordinator.transfer_ownership(sid, "ses_b")
    found = coordinator.find_session(sid)
    assert found.owner_opencode_session_id == "ses_b"


def test_transfer_ownership_terminal_blocked(coordinator):
    """transfer_ownership MUST reject transfers on terminal sessions."""
    sid = coordinator.create_session(kind="stage_plan", owner_opencode_session_id="ses_a", goal={})
    coordinator.update_session_status(sid, "completed", end_reason="x")
    with pytest.raises(RddfSessionError):
        coordinator.transfer_ownership(sid, "ses_b")


def test_abandon(coordinator):
    """abandon MUST transition state to abandoned with end_reason user-abandoned."""
    sid = coordinator.create_session(kind="stage_plan", owner_opencode_session_id="ses_a", goal={})
    coordinator.abandon(sid)
    found = coordinator.find_session(sid)
    assert found.state == "abandoned"
    assert found.end_reason == "user-abandoned"
    assert found.ended_at is not None


def test_abandon_terminal_blocked(coordinator):
    """abandon MUST reject abandoning an already-terminal session."""
    sid = coordinator.create_session(kind="stage_plan", owner_opencode_session_id="ses_a", goal={})
    coordinator.update_session_status(sid, "completed", end_reason="x")
    with pytest.raises(RddfSessionError):
        coordinator.abandon(sid)


def test_archive_history(coordinator, sessions_file):
    """archive_history MUST move old completed/failed/abandoned sessions to .archive.json, keep recent N."""
    sids = []
    for i in range(5):
        sid = coordinator.create_session(
            kind="stage_arch",
            owner_opencode_session_id=f"ses_{i}",
            goal={"intent": "guide-arch", "subject": f"change-{i}"},
        )
        sids.append(sid)
        # Complete first 4 immediately so next create does not conflict
        # (only one active session per kind is allowed)
        if i < 4:
            coordinator.update_session_status(sid, "completed", end_reason="x")

    archived_count = coordinator.archive_history(keep=2)
    assert archived_count == 2

    remaining = coordinator.list_sessions()
    assert len(remaining) == 3  # 2 most-recent completed + 1 active

    archive_path = sessions_file.with_suffix(".archive.json")
    assert archive_path.exists()
    archive_data = json.loads(archive_path.read_text())
    assert len(archive_data["sessions"]) == 2