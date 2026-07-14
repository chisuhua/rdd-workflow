"""Tests for rddf-session binding discovery methods (spec 2026-07-14)."""
import json
import time
from pathlib import Path

import pytest

from skills._lib.rddf_session import RddfSessionCoordinator


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


def test_find_current_binding_picks_most_recent_of_multiple(coordinator):
    """Two actives same owner => returns newer started_at."""
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
