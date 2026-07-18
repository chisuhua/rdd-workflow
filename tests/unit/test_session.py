"""Tests for SessionCoordinator — lightweight v2.0 sequential session coordination.

v2.0 stores session data in-memory within the coordinator instance, backed
by a reference to the state vector for context. The v2.0 state vector
schema (`state_vector_schema.json`) has `additionalProperties: false` at
root and `loop_state` levels, so direct persistence under `session_info` /
`sub_sessions` would fail schema validation. A future schema extension
(task 5.1 in `openspec/changes/v2-advanced-features/tasks.md`) will move
the storage into the state vector proper. The API surface is unchanged.
"""
import pytest

from skills._lib.core.state_vector import StateVector


@pytest.fixture
def state_vector():
    """Fresh default state vector (in-memory, not saved to disk)."""
    return StateVector.create_default()


# ---------------------------------------------------------------------------
# Required tests (per plan Task 4)
# ---------------------------------------------------------------------------


def test_create_session_writes_to_state_vector(state_vector):
    """create_session() persists the session so it can be retrieved via the
    state-vector-backed coordinator, and the returned session is fully
    populated (session_id, state=ACTIVE, timestamps)."""
    # Late import: module does not exist yet → ImportError (RED)
    from skills._lib.session import SessionCoordinator, SessionState

    coord = SessionCoordinator(state_vector)
    s = coord.create_session("implement feature X")

    # Session is queryable from the coordinator (state-vector backed)
    found = coord.find_session(s.session_id)
    assert found is not None
    assert found.goal == "implement feature X"
    assert found.state == SessionState.ACTIVE
    assert found.session_id  # non-empty
    assert found.started_at  # timestamp populated
    assert found.updated_at  # timestamp populated


def test_find_session_returns_created(state_vector):
    """find_session() returns the exact Session instance for a known id, and
    None for unknown ids."""
    from skills._lib.session import SessionCoordinator

    coord = SessionCoordinator(state_vector)
    s = coord.create_session("test goal")

    # Known id: returns the same Session
    found = coord.find_session(s.session_id)
    assert found is not None
    assert found.session_id == s.session_id
    assert found.goal == "test goal"

    # Unknown id: returns None
    assert coord.find_session("sess_does_not_exist") is None


def test_update_session_status_validates_transition(state_vector):
    """update_session_status() applies a valid state transition (active → paused)
    and updates `updated_at` to reflect the change."""
    from skills._lib.session import SessionCoordinator, SessionState

    coord = SessionCoordinator(state_vector)
    s = coord.create_session("test")
    original_updated_at = s.updated_at

    coord.update_session_status(s.session_id, SessionState.PAUSED)

    found = coord.find_session(s.session_id)
    assert found is not None
    assert found.state == SessionState.PAUSED
    # updated_at is refreshed (or at least not regressed)
    assert found.updated_at >= original_updated_at


def test_list_sessions_filters_by_parent(state_vector):
    """list_sessions(parent_session_id=...) returns only direct children of
    the given parent. With no filter, returns all sessions."""
    from skills._lib.session import SessionCoordinator

    coord = SessionCoordinator(state_vector)
    parent = coord.create_session("parent goal")
    child1 = coord.create_session("child 1", parent_session_id=parent.session_id)
    child2 = coord.create_session("child 2", parent_session_id=parent.session_id)
    unrelated = coord.create_session("unrelated")

    # No filter → all 4 sessions
    all_sessions = coord.list_sessions()
    assert len(all_sessions) == 4

    # Filter by parent → only the 2 children
    children = coord.list_sessions(parent_session_id=parent.session_id)
    assert len(children) == 2
    child_ids = {c.session_id for c in children}
    assert child_ids == {child1.session_id, child2.session_id}
    # Unrelated session is NOT in the filtered list
    assert unrelated.session_id not in child_ids


def test_parent_child_relationship_tracked(state_vector):
    """Sub-sessions track their parent_session_id; top-level sessions have
    parent_session_id == None."""
    from skills._lib.session import SessionCoordinator

    coord = SessionCoordinator(state_vector)
    parent = coord.create_session("parent")
    child = coord.create_session("child", parent_session_id=parent.session_id)
    grandchild = coord.create_session(
        "grandchild", parent_session_id=child.session_id
    )

    found_parent = coord.find_session(parent.session_id)
    found_child = coord.find_session(child.session_id)
    found_grandchild = coord.find_session(grandchild.session_id)

    # Parent has no parent
    assert found_parent.parent_session_id is None
    # Child's parent is the parent
    assert found_child.parent_session_id == parent.session_id
    # Grandchild's parent is the child (not the grandparent)
    assert found_grandchild.parent_session_id == child.session_id


def test_session_state_transitions_validated(state_vector):
    """All transitions defined in the spec are accepted:
    active → paused → active, active → completed, active → failed,
    paused → completed."""
    from skills._lib.session import SessionCoordinator, SessionState

    coord = SessionCoordinator(state_vector)

    # 1) active → paused → active
    s1 = coord.create_session("s1")
    coord.update_session_status(s1.session_id, SessionState.PAUSED)
    coord.update_session_status(s1.session_id, SessionState.ACTIVE)
    assert coord.find_session(s1.session_id).state == SessionState.ACTIVE

    # 2) active → completed
    s2 = coord.create_session("s2")
    coord.update_session_status(s2.session_id, SessionState.COMPLETED)
    assert coord.find_session(s2.session_id).state == SessionState.COMPLETED

    # 3) active → failed
    s3 = coord.create_session("s3")
    coord.update_session_status(s3.session_id, SessionState.FAILED)
    assert coord.find_session(s3.session_id).state == SessionState.FAILED

    # 4) paused → completed
    s4 = coord.create_session("s4")
    coord.update_session_status(s4.session_id, SessionState.PAUSED)
    coord.update_session_status(s4.session_id, SessionState.COMPLETED)
    assert coord.find_session(s4.session_id).state == SessionState.COMPLETED


def test_invalid_transition_raises(state_vector):
    """Transitions from terminal states (completed, failed) raise
    InvalidTransitionError. Same applies to undefined transitions like
    active → failed via paused."""
    from skills._lib.session import (
        SessionCoordinator,
        SessionState,
        InvalidTransitionError,
    )

    coord = SessionCoordinator(state_vector)

    # completed → active → raises
    s1 = coord.create_session("s1")
    coord.update_session_status(s1.session_id, SessionState.COMPLETED)
    with pytest.raises(InvalidTransitionError):
        coord.update_session_status(s1.session_id, SessionState.ACTIVE)
    with pytest.raises(InvalidTransitionError):
        coord.update_session_status(s1.session_id, SessionState.PAUSED)

    # failed → active → raises
    s2 = coord.create_session("s2")
    coord.update_session_status(s2.session_id, SessionState.FAILED)
    with pytest.raises(InvalidTransitionError):
        coord.update_session_status(s2.session_id, SessionState.ACTIVE)
    with pytest.raises(InvalidTransitionError):
        coord.update_session_status(s2.session_id, SessionState.PAUSED)

    # failed → completed → raises
    with pytest.raises(InvalidTransitionError):
        coord.update_session_status(s2.session_id, SessionState.COMPLETED)
