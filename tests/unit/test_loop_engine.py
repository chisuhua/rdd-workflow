"""Tests for LoopEngine — main 5-block cycle + safety mechanisms."""
import pytest
from skills.loop_engine import LoopEngine, LoopStatus
from skills._lib.state_vector import StateVector
from skills._lib.event_log import EventLog


@pytest.fixture
def engine(tmp_path):
    """Create a LoopEngine backed by tmp state vector + event log."""
    sv_path = str(tmp_path / "state-vector.json")
    el_path = str(tmp_path / "event-log.jsonl")
    # CORRECT API: StateVector.load(path) or StateVector.create_default()
    # (constructor takes dict, not path string)
    sv = StateVector.load(sv_path)
    el = EventLog(el_path)
    return LoopEngine(state=sv, event_log=el)


def test_verify_goal_with_predicate_returns_true_when_met(engine):
    """verify_goal returns True when dotted-path predicate is satisfied."""
    # CORRECT FIELD: plan_side.active_change (singular — schema constraint)
    engine.state.update_field("plan_side.active_change", None)
    assert engine.verify_goal("plan_side['active_change'] is None") is True


def test_verify_goal_with_predicate_returns_false_when_unmet(engine):
    """verify_goal returns False when predicate is not satisfied."""
    engine.state.update_field("plan_side.active_change", "v2-loop-engine")
    assert engine.verify_goal("plan_side['active_change'] is None") is False


def test_max_iterations_exceeded_triggers_stop(tmp_path):
    """Loop exits with max_iterations_exceeded when iterations hit cap."""
    sv_path = str(tmp_path / "state-vector.json")
    el_path = str(tmp_path / "event-log.jsonl")
    # CORRECT API: StateVector.load(path) — constructor takes dict, not path string
    engine = LoopEngine(state=StateVector.load(sv_path), event_log=EventLog(el_path))
    engine.safety["max_iterations"] = 3
    # Unachievable goal — never true (dotted-path predicate)
    status = engine.run(goal_predicate="plan_side['active_change'] == 'IMPOSSIBLE_VALUE'", max_iterations=3)
    assert status == LoopStatus.MAX_ITERATIONS_EXCEEDED


def test_oscillation_detected_with_5_same_states(tmp_path):
    """Loop exits with oscillation_detected when last 5 states are ≤ 2 distinct."""
    sv_path = str(tmp_path / "state-vector.json")
    el_path = str(tmp_path / "event-log.jsonl")
    engine = LoopEngine(state=StateVector.load(sv_path), event_log=EventLog(el_path))
    engine.safety["max_iterations"] = 20
    # Simulate stuck state
    for _ in range(5):
        engine.loop_state.detections = [{"type": "x", "data": {}, "message": "x"}]
        engine.loop_state.recent_state_hashes.append(engine.loop_state.snapshot_hash())
    # Provide a custom run path that always oscillates
    def fake_scan(): pass
    def fake_plan(): pass
    def fake_execute(): pass
    def fake_verify_results(): return False
    def fake_adapt(): pass
    engine.scan_state = fake_scan
    engine.generate_plan = fake_plan
    engine.execute_plan = fake_execute
    engine.verify_results = fake_verify_results
    engine.adapt = fake_adapt
    engine.loop_state.detections = [{"type": "x", "data": {}, "message": "x"}]
    status = engine.run(goal_predicate="plan_side['active_change'] == 'NEVER'")
    assert status == LoopStatus.OSCILLATION_DETECTED


def test_loop_engine_scan_uses_detectors(tmp_path, monkeypatch):
    """scan_state() invokes all built-in detectors."""
    sv_path = str(tmp_path / "state-vector.json")
    el_path = str(tmp_path / "event-log.jsonl")
    engine = LoopEngine(state=StateVector.load(sv_path), event_log=EventLog(el_path))
    engine.scan_state()
    assert len(engine.loop_state.detections) == 8  # all 8 built-ins


def test_loop_engine_accepts_mode_parameter(tmp_path):
    """LoopEngine accepts interaction mode at construction time."""
    sv_path = str(tmp_path / "state-vector.json")
    el_path = str(tmp_path / "event-log.jsonl")
    from skills._lib.interaction_modes import make_mode, LoopMode
    from skills._lib.human_nodes import HumanNodeRegistry
    registry = HumanNodeRegistry()
    engine = LoopEngine(
        state=StateVector.load(sv_path),
        event_log=EventLog(el_path),
        mode=LoopMode(registry),
    )
    assert engine.mode.name == "loop"