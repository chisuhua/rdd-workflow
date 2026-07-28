"""Tests for rddf-session binding discovery methods (spec 2026-07-14)."""
import json
import time
from pathlib import Path

import pytest

from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator


@pytest.fixture
def sessions_file(tmp_path):
    return tmp_path / "sessions.json"


@pytest.fixture
def coordinator(sessions_file):
    return RddfSessionCoordinator(sessions_file=str(sessions_file))


def test_find_current_binding_returns_active_for_owner(coordinator):
    """Owner with one active session returns that session."""
    sid = coordinator.create_session(
        kind="stage_plan", owner_opencode_session_id="ses_owner1", goal={}
    )
    found = coordinator.find_current_binding("ses_owner1")
    assert found is not None
    assert found.session_id == sid
    assert found.state == "active"


def test_find_current_binding_returns_none_when_terminal(coordinator):
    """Owner with only completed/failed/abandoned returns None."""
    sid = coordinator.create_session(
        kind="stage_arch", owner_opencode_session_id="ses_owner1", goal={}
    )
    coordinator.update_session_status(sid, "completed", end_reason="arch-done")
    assert coordinator.find_current_binding("ses_owner1") is None


def test_find_current_binding_returns_none_for_different_owner(coordinator):
    """Active session owned by other owner returns None."""
    coordinator.create_session(
        kind="stage_plan", owner_opencode_session_id="ses_other", goal={}
    )
    assert coordinator.find_current_binding("ses_me") is None


def test_find_current_binding_picks_most_recent_of_multiple(coordinator, monkeypatch):
    """Two actives same owner => returns newer started_at."""
    monkeypatch.setenv("RDDF_ALLOW_CROSS_STAGE_PARALLEL", "yes")
    sid1 = coordinator.create_session(
        kind="stage_arch", owner_opencode_session_id="ses_owner", goal={}
    )
    time.sleep(0.05)  # ensure distinct started_at
    sid2 = coordinator.create_session(
        kind="stage_plan", owner_opencode_session_id="ses_owner", goal={}
    )
    found = coordinator.find_current_binding("ses_owner")
    assert found is not None
    assert found.session_id == sid2  # newer wins


def test_find_current_binding_empty_sessions_file(coordinator):
    """sessions.json with empty sessions[] => returns None."""
    assert coordinator.find_current_binding("anybody") is None


# -- Next recommendation tests (Task 2) --


def _force_orphaned(coordinator, sid):
    """Helper: bypass heartbeat check by directly setting state via update."""
    # update_session_status raises if state is already terminal; use find + modify
    # Simpler: use the public path that promotes via check_heartbeat_timeouts
    # by manipulating last_heartbeat to be far in the past.
    data = json.loads(coordinator._sessions_file.read_text())
    for s in data["sessions"]:
        if s["session_id"] == sid:
            s["last_heartbeat"] = "2020-01-01T00:00:00+00:00"
            break
    coordinator._atomic_write(data)
    coordinator.check_heartbeat_timeouts()


def test_find_next_recommendation_returns_most_recent_orphaned(coordinator, monkeypatch):
    """Three orphaned → returns newest started_at."""
    monkeypatch.setenv("RDDF_ALLOW_CROSS_STAGE_PARALLEL", "yes")
    s1 = coordinator.create_session(kind="stage_arch", owner_opencode_session_id="o1", goal={})
    time.sleep(0.05)
    s2 = coordinator.create_session(kind="stage_plan", owner_opencode_session_id="o1", goal={})
    time.sleep(0.05)
    s3 = coordinator.create_session(kind="stage_ship", owner_opencode_session_id="o1", goal={})
    _force_orphaned(coordinator, s1)
    _force_orphaned(coordinator, s2)
    _force_orphaned(coordinator, s3)
    found = coordinator.find_next_recommendation()
    assert found is not None
    assert found.session_id == s3


def test_find_next_recommendation_returns_none_when_no_orphaned(coordinator, monkeypatch):
    """Only active/completed → returns None."""
    monkeypatch.setenv("RDDF_ALLOW_CROSS_STAGE_PARALLEL", "yes")
    coordinator.create_session(kind="stage_arch", owner_opencode_session_id="o1", goal={})
    sid = coordinator.create_session(kind="stage_plan", owner_opencode_session_id="o1", goal={})
    coordinator.update_session_status(sid, "completed", end_reason="plan-done")
    assert coordinator.find_next_recommendation() is None


def test_find_next_recommendation_ignores_active_and_completed(coordinator, monkeypatch):
    """Mixed states → only orphaned considered."""
    monkeypatch.setenv("RDDF_ALLOW_CROSS_STAGE_PARALLEL", "yes")
    s_active = coordinator.create_session(
        kind="stage_arch", owner_opencode_session_id="o1", goal={}
    )
    s_done = coordinator.create_session(
        kind="stage_plan", owner_opencode_session_id="o1", goal={}
    )
    coordinator.update_session_status(s_done, "completed", end_reason="plan-done")
    s_orph = coordinator.create_session(
        kind="stage_ship", owner_opencode_session_id="o1", goal={}
    )
    _force_orphaned(coordinator, s_orph)
    found = coordinator.find_next_recommendation()
    assert found is not None
    assert found.session_id == s_orph
    assert found.session_id != s_active
    assert found.session_id != s_done


def test_find_next_recommendation_empty_sessions(coordinator):
    """Empty sessions.json → None."""
    assert coordinator.find_next_recommendation() is None


def test_check_heartbeat_then_find_current_returns_none(coordinator):
    """Active older than 30min → orphaned promoted → find_current_binding None."""
    sid = coordinator.create_session(
        kind="stage_plan", owner_opencode_session_id="ses_me", goal={}
    )
    data = json.loads(coordinator._sessions_file.read_text())
    for s in data["sessions"]:
        if s["session_id"] == sid:
            s["last_heartbeat"] = "2020-01-01T00:00:00+00:00"
    coordinator._atomic_write(data)
    coordinator.check_heartbeat_timeouts()
    assert coordinator.find_current_binding("ses_me") is None
    nxt = coordinator.find_next_recommendation()
    assert nxt is not None
    assert nxt.session_id == sid
