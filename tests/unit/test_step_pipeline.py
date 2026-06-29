"""Tests for StepPipeline — phase step execution engine (ADR-0011).

The StepPipeline loads phase templates from YAML, tracks step completion
in state, and supports interruption recovery via `get_pending_steps()`.

These tests lock the public surface used by the loop engine and the
ship-side executor:
- list_steps(phase) — ordered list of step dicts from the template
- get_pending_steps(phase) — steps that have not been completed yet
- is_step_completed(step_id) — boolean completion lookup
- mark_step_completed(step_id) — record a step as done
- reset() — clear all completion state
"""
from __future__ import annotations

import os
import pytest

from skills._lib.step_pipeline import StepPipeline, PipelineEvent
from skills._lib.state_vector import StateVector


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def state_vector():
    """A default in-memory StateVector (no file I/O)."""
    return StateVector.create_default()


@pytest.fixture
def templates_path(tmp_path):
    """Write a small phase-template YAML file to tmp_path and return its path.

    Contains two phases:
      - test_phase: 2 steps (used by most tests)
      - empty_phase: 0 steps
    """
    yaml_content = (
        "templates:\n"
        "  test_phase:\n"
        "    description: \"Test phase for unit tests\"\n"
        "    steps:\n"
        "      - id: \"step-1\"\n"
        "        action: \"do_thing_one\"\n"
        "        description: \"First test step\"\n"
        "      - id: \"step-2\"\n"
        "        action: \"do_thing_two\"\n"
        "        description: \"Second test step\"\n"
        "  empty_phase:\n"
        "    description: \"Phase with no steps\"\n"
        "    steps: []\n"
    )
    path = tmp_path / "phase_templates.yaml"
    path.write_text(yaml_content)
    return str(path)


@pytest.fixture
def pipeline(state_vector, templates_path):
    """StepPipeline wired to a default state vector and tmp YAML templates."""
    return StepPipeline(state_vector=state_vector, templates_path=templates_path)


# ---------------------------------------------------------------------------
# Tests — 7 cases (ADR-0011 surface)
# ---------------------------------------------------------------------------

def test_list_steps_returns_expected(pipeline):
    """list_steps loads the test phase and returns 2 steps with the right ids."""
    steps = pipeline.list_steps("test_phase")
    assert isinstance(steps, list)
    assert len(steps) == 2
    ids = [s["id"] for s in steps]
    assert ids == ["step-1", "step-2"]


def test_list_steps_unknown_phase_returns_empty(pipeline):
    """list_steps for a phase not in the template returns an empty list."""
    steps = pipeline.list_steps("does_not_exist")
    assert steps == []


def test_is_step_completed_initial_state(pipeline):
    """is_step_completed returns False for a step that has not been marked done."""
    assert pipeline.is_step_completed("step-1") is False
    assert pipeline.is_step_completed("step-2") is False


def test_mark_step_completed_then_check(pipeline):
    """After mark_step_completed, is_step_completed returns True for that step."""
    pipeline.mark_step_completed("step-1")
    assert pipeline.is_step_completed("step-1") is True
    # Other step remains uncompleted (no cross-contamination)
    assert pipeline.is_step_completed("step-2") is False


def test_skip_completed_removes_done_steps(pipeline):
    """get_pending_steps filters out completed steps, leaving the rest pending."""
    pipeline.mark_step_completed("step-1")
    pending = pipeline.get_pending_steps("test_phase")
    pending_ids = [s["id"] for s in pending]
    assert "step-1" not in pending_ids
    assert "step-2" in pending_ids
    assert len(pending) == 1


def test_get_pending_steps_all_if_none_done(pipeline):
    """get_pending_steps returns all steps initially (none completed)."""
    pending = pipeline.get_pending_steps("test_phase")
    pending_ids = [s["id"] for s in pending]
    assert pending_ids == ["step-1", "step-2"]


def test_reset_clears_completed(pipeline):
    """reset() clears all completed steps; is_step_completed goes back to False."""
    pipeline.mark_step_completed("step-1")
    pipeline.mark_step_completed("step-2")
    assert pipeline.is_step_completed("step-1") is True
    assert pipeline.is_step_completed("step-2") is True

    pipeline.reset()

    assert pipeline.is_step_completed("step-1") is False
    assert pipeline.is_step_completed("step-2") is False
    # Pending should be the full step list again
    pending_ids = [s["id"] for s in pipeline.get_pending_steps("test_phase")]
    assert pending_ids == ["step-1", "step-2"]
