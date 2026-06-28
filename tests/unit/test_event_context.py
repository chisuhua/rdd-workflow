"""Tests for skills/_lib/event_context.py — context snapshot for events."""
import pytest
from skills._lib.event_context import current_context, DEFAULT_STATE_PATH
from skills._lib.state_vector import StateVector


def test_current_context_returns_dict(tmp_path):
    """current_context() must return a dict snapshot (never raise on missing state)."""
    ctx = current_context(str(tmp_path / "missing.json"))
    assert isinstance(ctx, dict)
    # When no state file exists, load() falls back to defaults — snapshot
    # should still expose the well-known keys with non-None values where applicable.
    assert "goal" in ctx
    assert "loop_iteration" in ctx
    assert ctx["loop_iteration"] == 0


def test_current_context_reflects_saved_state(tmp_path):
    """After saving a state vector, current_context must surface its fields."""
    state_path = str(tmp_path / "state-vector.json")
    sv = StateVector.create_default()
    sv.update_field("goal", "ship v2.0")
    sv.update_field("loop_state.iteration", 7)
    sv.save(state_path)

    ctx = current_context(state_path)

    assert isinstance(ctx, dict)
    assert ctx["goal"] == "ship v2.0"
    assert ctx["loop_iteration"] == 7


def test_default_state_path_is_a_string():
    """DEFAULT_STATE_PATH is a non-empty string used as the default argument."""
    assert isinstance(DEFAULT_STATE_PATH, str)
    assert DEFAULT_STATE_PATH
    assert DEFAULT_STATE_PATH.endswith(".json")