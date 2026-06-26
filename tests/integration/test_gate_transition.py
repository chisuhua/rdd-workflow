"""Integration tests: gate mechanism pass/fail/force transitions.

Exercises GateMechanism against the real Check registry and event log:
- PASS: a transition with all checks returning (True, _) → result.passed=True
- FAIL: a transition with any error-severity check returning False → result.passed=False
- FORCE: gate.force_transition() bypasses failure and records GATE_FORCED event

This locks the cross-component contract that the three phase boundaries
(arch_done, plan_done, ship_done) emit the correct events and produce
GateResult objects consumable by callers.
"""
import os
import json
import pytest

from skills._lib.gate import (
    GateMechanism,
    GateResult,
    Check,
    register_gate_check,
)
from skills._lib.state_vector import StateVector


# ---------- Fixtures ---------- #

@pytest.fixture
def state_path(tmp_path):
    return str(tmp_path / "state-vector.json")


@pytest.fixture
def log_path(tmp_path):
    return str(tmp_path / "event-log.jsonl")


@pytest.fixture
def state_vector_saved(state_path):
    """Persist a default state vector so the gate can load it for context."""
    sv = StateVector.create_default()
    sv.save(state_path)
    return sv


@pytest.fixture
def clean_gate(state_path, log_path):
    """Gate with NO default checks — full control over what runs."""
    return GateMechanism(
        state_path=state_path,
        event_log_path=log_path,
        load_defaults=False,
    )


@pytest.fixture
def default_gate(state_path, log_path):
    """Gate with default checks for arch_done/plan_done/ship_done."""
    return GateMechanism(
        state_path=state_path,
        event_log_path=log_path,
        load_defaults=True,
    )


def _always_pass(ctx):
    return (True, None)


def _always_fail_error(ctx):
    return (False, "error")


def _always_fail_warning(ctx):
    return (False, "warning")


# ---------- Pass / Fail transitions ---------- #

def test_gate_pass_when_all_checks_pass(clean_gate, state_vector_saved):
    """A clean checklist of (True, _) returns result.passed=True with no failures."""
    clean_gate.register(Check(
        name="tests_pass",
        condition=_always_pass,
        message="ok",
        suggestion="",
    ))
    clean_gate.register(Check(
        name="coverage_80",
        condition=_always_pass,
        message="ok",
        suggestion="",
    ))
    result = clean_gate.verify_transition("arch_done", {})
    assert isinstance(result, GateResult)
    assert result.passed is True
    assert result.failed_checks == []
    assert result.transition == "arch_done"


def test_gate_fail_when_error_check_fails(clean_gate, state_vector_saved):
    """An error-severity failure must block the transition and populate failed_checks."""
    clean_gate.register(Check(
        name="tests_pass",
        condition=_always_fail_error,
        message="tests failing",
        suggestion="Run: pytest tests/ -v",
    ))
    clean_gate.register(Check(
        name="coverage_80",
        condition=_always_pass,
        message="ok",
        suggestion="",
    ))
    result = clean_gate.verify_transition("plan_done", {})
    assert result.passed is False
    assert "tests_pass" in result.failed_checks
    assert "coverage_80" not in result.failed_checks
    assert result.transition == "plan_done"
    assert result.error is not None
    assert "tests_pass" in result.error


def test_gate_warning_allows_transition(clean_gate, state_vector_saved):
    """A warning-severity failure must allow the transition but record a warning."""
    clean_gate.register(Check(
        name="soft_warning",
        condition=_always_fail_warning,
        message="soft issue",
        suggestion="Consider fixing",
    ))
    result = clean_gate.verify_transition("arch_done", {})
    assert result.passed is True
    assert result.warnings == ["soft_warning"]
    assert "soft_warning" not in result.failed_checks


def test_gate_unknown_transition_returns_error(clean_gate, state_vector_saved):
    """An unknown transition name must return passed=False with explanatory error."""
    result = clean_gate.verify_transition("nonsense_phase", {})
    assert result.passed is False
    assert "Unknown transition" in (result.error or "")


# ---------- Force override ---------- #

def test_force_override_records_event(clean_gate, state_vector_saved, log_path):
    """gate.force_transition() must return True and record a gate_forced event."""
    # Force a transition even with no failing checks — force should succeed
    # and record the override reason.
    forced = clean_gate.force_transition(
        "arch_done", {}, reason="urgent hotfix"
    )
    assert forced is True
    # Verify the event log captured the override with the reason.
    with open(log_path) as f:
        events = [json.loads(line) for line in f if line.strip()]
    forced_events = [e for e in events if e.get("event_type") == "gate_forced"]
    assert len(forced_events) == 1
    assert forced_events[0]["context"]["reason"] == "urgent hotfix"
    assert forced_events[0]["context"]["transition"] == "arch_done"


def test_force_override_despite_blocking_check(
    clean_gate, state_vector_saved, log_path
):
    """force_transition() must succeed even when a blocking check is registered."""
    clean_gate.register(Check(
        name="blocker",
        condition=_always_fail_error,
        message="blocked",
        suggestion="Fix it",
    ))
    # Force transition past the blocker
    forced = clean_gate.force_transition(
        "plan_done", {}, reason="emergency deploy"
    )
    assert forced is True
    # The gate_forced event is the audit trail of the override.
    with open(log_path) as f:
        events = [json.loads(line) for line in f if line.strip()]
    assert any(
        e.get("event_type") == "gate_forced"
        and e["context"]["reason"] == "emergency deploy"
        for e in events
    )


# ---------- Three transition types share the same contract ---------- #

@pytest.mark.parametrize("transition", ["arch_done", "plan_done", "ship_done"])
def test_all_three_transitions_have_default_checks(default_gate, state_vector_saved, transition):
    """Default gate must expose arch_done, plan_done, ship_done transitions."""
    names = default_gate.get_registered_check_names()
    assert isinstance(names, list)
    assert len(names) > 0
    # The transition itself should be verifiable without raising.
    result = default_gate.verify_transition(transition, {})
    assert isinstance(result, GateResult)
    assert result.transition == transition


def test_default_arch_done_has_adr_and_roadmap_checks(default_gate, state_vector_saved):
    """arch_done default checks include adr_exists + roadmap_defined."""
    names = default_gate.get_registered_check_names()
    assert "adr_exists" in names
    assert "roadmap_defined" in names


def test_default_plan_done_has_artifacts_checks(default_gate, state_vector_saved):
    """plan_done default checks include changes_committed + artifacts_complete."""
    names = default_gate.get_registered_check_names()
    assert "changes_committed" in names
    assert "artifacts_complete" in names


def test_default_ship_done_has_test_and_archive_checks(default_gate, state_vector_saved):
    """ship_done default checks include worktrees_empty + archive_empty + tests_pass."""
    names = default_gate.get_registered_check_names()
    assert "worktrees_empty" in names
    assert "archive_empty" in names
    assert "tests_pass" in names


# ---------- Pass/Fail events recorded in the event log ---------- #

def test_pass_records_gate_transition_event(clean_gate, state_vector_saved, log_path):
    """A successful verify_transition() must emit a gate_transition event."""
    clean_gate.register(Check(
        name="ok_check", condition=_always_pass, message="ok", suggestion=""
    ))
    clean_gate.verify_transition("arch_done", {})
    with open(log_path) as f:
        events = [json.loads(line) for line in f if line.strip()]
    assert any(e.get("event_type") == "gate_transition" for e in events)


def test_fail_records_gate_failed_event(clean_gate, state_vector_saved, log_path):
    """A failed verify_transition() must emit a gate_failed event."""
    clean_gate.register(Check(
        name="bad_check", condition=_always_fail_error, message="bad", suggestion=""
    ))
    clean_gate.verify_transition("arch_done", {})
    with open(log_path) as f:
        events = [json.loads(line) for line in f if line.strip()]
    assert any(e.get("event_type") == "gate_failed" for e in events)


# ---------- Plugin registration ---------- #

def test_register_gate_check_via_module_api(state_path, log_path, state_vector_saved):
    """register_gate_check() at module level adds to all transitions."""
    from skills._lib import gate as gate_mod
    gate_mod.register_gate_check(Check(
        name="custom_plugin_check",
        condition=_always_pass,
        message="ok",
        suggestion="",
    ))
    gate = gate_mod.GateMechanism(state_path=state_path, event_log_path=log_path)
    assert "custom_plugin_check" in gate.get_registered_check_names()
