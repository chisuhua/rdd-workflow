"""Unit tests for DesignPhase (pre-loop Goal/Verification/Control design)."""
import pytest
from skills._lib.design_phase import DesignPhase, DesignResult
from skills._lib.state_vector import StateVector
from skills._lib.event_log import EventLog


@pytest.fixture
def env(tmp_path):
    sv = StateVector.load(str(tmp_path / "state-vector.json"))
    el = EventLog(str(tmp_path / "event-log.jsonl"))
    return sv, el


def test_design_phase_has_three_dimensions(env):
    """Design phase covers Goal, Verification, Control dimensions."""
    sv, el = env
    dp = DesignPhase(state=sv, event_log=el)
    dims = dp.list_dimensions()
    assert "goal" in dims
    assert "verification" in dims
    assert "control" in dims


def test_design_phase_default_goal_dim(env):
    """Default goal design includes deliverables + completion_criteria."""
    sv, el = env
    dp = DesignPhase(state=sv, event_log=el)
    goal = dp.default_for("goal")
    assert "deliverables" in goal
    assert "completion_criteria" in goal


def test_design_phase_persists_to_state_vector(env):
    """Design result saved to state vector under loop_state.design."""
    sv, el = env
    dp = DesignPhase(state=sv, event_log=el)
    result = DesignResult(
        goal={"deliverables": ["x"], "completion_criteria": "x == done"},
        verification={"executor": "deep", "reviewer": "oracle"},
        control={"max_iterations": 50, "max_retries": 2, "oscillation_threshold": 3},
    )
    dp.apply(result)
    saved = sv.to_dict()
    assert "design" in saved["loop_state"]
    assert saved["loop_state"]["design"]["control"]["max_iterations"] == 50
