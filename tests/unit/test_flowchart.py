"""Tests for FlowchartGenerator — ASCII real-time progress display."""
import time
import pytest
from skills._lib.flowchart import FlowchartGenerator
from skills._lib.state_vector import StateVector
from skills._lib.event_log import EventLog


@pytest.fixture
def env(tmp_path):
    sv = StateVector.load(str(tmp_path / "state-vector.json"))
    el = EventLog(str(tmp_path / "event-log.jsonl"))
    return sv, el


def test_flowchart_includes_phase_and_iteration(env):
    """Generated flowchart shows current phase + iteration count."""
    sv, el = env
    fc = FlowchartGenerator(state=sv, event_log=el)
    sv.update_field("loop_state.current_phase", "execute_plan")
    sv.update_field("loop_state.iteration", 7)
    chart = fc.render()
    assert "execute_plan" in chart
    assert "7" in chart


def test_flowchart_includes_event_log_errors(env):
    """Flowchart summarizes recent errors from event log."""
    from skills._lib.event_types import EventType, Severity
    sv, el = env
    el.record(
        event_type=EventType.ERROR_OCCURRED,
        severity=Severity.ERROR,
        message="boom",
    )
    fc = FlowchartGenerator(state=sv, event_log=el)
    chart = fc.render()
    assert "error" in chart.lower() or "ERROR" in chart


def test_flowchart_renders_under_100ms(env):
    """Flowchart regeneration completes in < 100ms."""
    sv, el = env
    fc = FlowchartGenerator(state=sv, event_log=el)
    # Warm-up
    fc.render()
    start = time.perf_counter()
    chart = fc.render()
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert elapsed_ms < 100, f"Render took {elapsed_ms:.1f}ms"
    assert len(chart) > 0
