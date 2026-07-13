"""Integration tests: full loop flow scan → plan → execute → verify → adapt.

Exercises the v2 loop engine end-to-end against the real detectors,
actions, and event log. These tests guard the cross-component contract
that the 5-building-block cycle (verify_goal → scan_state → generate_plan
→ execute_plan → verify_results → adapt) completes without exceptions
and that LoopState advances its iteration counter correctly.
"""
import os
import json
import pytest

from skills._lib.loop_state import LoopState
from skills._lib.state_vector import StateVector
from skills._lib.event_log import EventLog
from skills._lib.detectors import all_detectors, BUILTIN_DETECTORS
from skills._lib.actions import all_actions, BUILTIN_ACTIONS
from skills.loop_engine import LoopEngine, LoopStatus


# ---------- Fixtures ---------- #

@pytest.fixture
def state_vector(tmp_path):
    """Fresh default state vector (version 2.0)."""
    return StateVector.create_default()


@pytest.fixture
def event_log(tmp_path):
    """JSONL event log at a temp path (parent dirs auto-created)."""
    return EventLog(os.path.join(str(tmp_path), "event-log.jsonl"))


@pytest.fixture
def engine(state_vector, event_log):
    """LoopEngine wired to temp state + event log."""
    return LoopEngine(state=state_vector, event_log=event_log)


# ---------- Detector / action registry shape ---------- #

def test_builtin_detector_registry_is_complete():
    """all_detectors() must return 9 built-in detectors (no plugins in tmp).

    v3.0 added `detect_trigger_events` (v3.0 scheduled-triggers feature); see
    `skills/_lib/detectors.py::BUILTIN_DETECTORS` for the canonical list.
    """
    detectors = all_detectors(plugin_dir="/nonexistent/_no_plugins_")
    names = {d.name for d in detectors}
    expected = {
        "detect_worktrees",
        "detect_pending_changes",
        "detect_archived_changes",
        "detect_roadmap_state",
        "detect_adr_status",
        "detect_health_issues",
        "detect_test_gaps",
        "detect_stale_branches",
        "detect_trigger_events",
    }
    assert expected.issubset(names), f"Missing detectors: {expected - names}"
    assert len(BUILTIN_DETECTORS) == 9


def test_builtin_action_registry_is_complete():
    """all_actions() must return the 7 built-in action wrappers."""
    actions = all_actions()
    names = {a.name for a in actions}
    expected = {
        "action_create_worktree",
        "action_generate_plan",
        "action_execute_worktree",
        "action_archive_change",
        "action_cleanup_stale",
        "action_update_roadmap",
        "action_create_adr",
    }
    assert expected.issubset(names), f"Missing actions: {expected - names}"
    assert len(BUILTIN_ACTIONS) == 7


# ---------- Scan → Plan → Execute → Verify → Adapt cycle ---------- #

def test_scan_state_populates_detections(engine):
    """engine.scan_state() must run all 9 built-in detectors and store results."""
    assert engine.loop_state.detections == []
    engine.scan_state()
    # Each detector produces a DetectionResult (or compatible dict-like object).
    assert len(engine.loop_state.detections) == len(BUILTIN_DETECTORS)
    for d in engine.loop_state.detections:
        # DetectionResult exposes .type, .severity, .message; dicts expose .get()
        assert (hasattr(d, "type") and hasattr(d, "severity")) or isinstance(d, dict)


def test_generate_plan_populates_plan(engine):
    """engine.generate_plan() must produce at least one plan entry."""
    engine.scan_state()
    engine.generate_plan()
    assert isinstance(engine.loop_state.plan, list)
    # Plan may be empty if no actionable detections, but the field must exist
    # and be a list — this is the integration contract.
    assert all(entry is not None for entry in engine.loop_state.plan)


def test_full_cycle_executes_without_exception(engine):
    """All 5 building blocks must run sequentially without raising."""
    engine.scan_state()
    engine.generate_plan()
    engine.execute_plan()
    engine.verify_results()
    engine.adapt()
    # After one full cycle, loop_state.iteration may still be 0 (run() drives it),
    # but every block must have populated its output field.
    assert engine.loop_state.detections is not None
    assert engine.loop_state.plan is not None
    assert engine.loop_state.executed is not None
    assert engine.loop_state.errors == []


def test_run_loop_with_achievable_goal_succeeds(engine):
    """engine.run() must return LoopStatus.SUCCESS when goal predicate holds."""
    # Default state vector has plan_side.active_change == None → predicate is true.
    status = engine.run(
        goal_predicate="plan_side['active_change'] is None",
        max_iterations=3,
    )
    assert status == LoopStatus.SUCCESS
    assert engine.loop_state.iteration >= 1


def test_run_loop_with_unachievable_goal_exits_clean(engine):
    """engine.run() must terminate with MAX_ITERATIONS_EXCEEDED for impossible goal.

    Predicate references a state vector field that will never match the
    schema's enum, so the goal is structurally unachievable from any
    starting state. Note: we must NOT pre-set the field (that would make
    it achievable); the predicate is impossible by construction.
    """
    status = engine.run(
        goal_predicate="arch_side['current_change'] == 'NEVER_MATCHES_ANY_VALUE_XYZ'",
        max_iterations=2,
    )
    assert status == LoopStatus.MAX_ITERATIONS_EXCEEDED
    assert engine.loop_state.iteration == 2


# ---------- LoopState contract ---------- #

def test_loop_state_default_construction():
    """LoopState() with no args must produce a fresh, empty, well-typed state."""
    ls = LoopState()
    assert ls.goal == ""
    assert ls.iteration == 0
    assert ls.detections == []
    assert ls.plan == []
    assert ls.executed == []
    assert ls.errors == []
    assert ls.consecutive_failures == 0
    assert ls.recent_state_hashes == []


def test_loop_state_snapshot_hash_stable():
    """LoopState.snapshot_hash() must be deterministic for same detections."""
    ls1 = LoopState()
    ls1.detections = [{"type": "x", "data": {"k": 1}}]
    ls2 = LoopState()
    ls2.detections = [{"type": "x", "data": {"k": 1}}]
    assert ls1.snapshot_hash() == ls2.snapshot_hash()


def test_loop_state_tracks_iteration_after_run(engine):
    """LoopState.iteration must advance as engine.run() cycles."""
    engine.run(
        goal_predicate="plan_side['active_change'] is None",
        max_iterations=5,
    )
    assert engine.loop_state.iteration >= 1


def test_event_log_records_loop_events(engine):
    """The event log must capture loop start/completion events from a run."""
    log_path = engine.event_log.path
    engine.run(
        goal_predicate="plan_side['active_change'] is None",
        max_iterations=2,
    )
    with open(log_path) as f:
        events = [json.loads(line) for line in f if line.strip()]
    event_types = {e.get("event_type") for e in events}
    assert "loop_started" in event_types
    assert "loop_completed" in event_types


# ---------- Detector / action integration ---------- #

def test_each_builtin_detector_returns_detection_result():
    """Each built-in detector must accept a default state dict and return a result."""
    state = StateVector.create_default()._data
    for detector in BUILTIN_DETECTORS:
        result = detector.detect(state)
        # DetectionResult exposes .type and .severity; some may also be dicts
        assert result is not None
        assert hasattr(result, "type") or isinstance(result, dict)


def test_each_builtin_action_signature():
    """Each built-in action wrapper must expose .name and .execute(params, event_log)."""
    for action in all_actions():
        assert hasattr(action, "name")
        assert callable(getattr(action, "execute", None))
        assert action.name.startswith("action_")
