"""Tests for SessionManager — parallel session execution (ADR-0010 v2.1)."""
import pytest
from skills._lib.session_manager import SessionManager
from skills._lib.state_vector import StateVector
from skills._lib.event_log import EventLog


@pytest.fixture
def sv(tmp_path):
    return StateVector.load(str(tmp_path / "sv.json"))


@pytest.fixture
def el(tmp_path):
    return EventLog(str(tmp_path / "el.jsonl"))


@pytest.fixture
def mgr(sv, el):
    return SessionManager(state_vector=sv, event_log=el)


def test_create_session_returns_session_id(mgr):
    sid = mgr.create_session(goal="test", mode="loop")
    assert sid.startswith("sess_")


def test_find_session_returns_session(mgr):
    sid = mgr.create_session(goal="find-me")
    s = mgr.find_session(sid)
    assert s is not None and s.goal == "find-me"


def test_update_status_valid_transition(mgr):
    sid = mgr.create_session(goal="status-test")
    mgr.update_session_status(sid, "paused")
    assert mgr.find_session(sid).state.value == "paused"


def test_update_status_invalid_transition_raises(mgr):
    sid = mgr.create_session(goal="inv")
    mgr.update_session_status(sid, "completed")
    with pytest.raises(Exception):
        mgr.update_session_status(sid, "active")


def test_list_sessions_returns_all(mgr):
    s1 = mgr.create_session(goal="a")
    s2 = mgr.create_session(goal="b")
    assert len(mgr.list_sessions()) == 2


def test_create_session_with_parent(mgr):
    p = mgr.create_session(goal="parent")
    c = mgr.create_session(goal="child", parent_session=p)
    assert mgr.find_session(c).parent_session_id == p
