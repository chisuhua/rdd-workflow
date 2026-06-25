"""Tests for GateMechanism — phase-transition gate with two severity levels."""
import os
import pytest
from skills._lib.gate import GateMechanism, Check, GateResult, GateError, register_gate_check
from skills._lib.state_vector import StateVector


@pytest.fixture
def state_path(tmp_path):
    return str(tmp_path / "state-vector.json")


@pytest.fixture
def log_path(tmp_path):
    return str(tmp_path / "event-log.jsonl")


def make_state(**overrides):
    sv = StateVector.create_default()
    for k, v in overrides.items():
        sv.update_field(k, v)
    return sv


def test_error_check_blocks_transition(state_path, log_path):
    """A check returning (False, 'error') blocks the transition."""
    sv = make_state()
    sv.save(state_path)
    gate = GateMechanism(state_path=state_path, event_log_path=log_path)
    gate.register(Check(
        name="always_fails_error",
        condition=lambda ctx: (False, "error"),
        message="hard fail",
        suggestion="Fix the thing",
    ))
    result = gate.verify_transition("arch_done", {})
    assert result.passed is False
    assert "always_fails_error" in result.failed_checks
    assert result.error is not None


def test_warning_check_allows_with_notice(state_path, log_path):
    """A check returning (False, 'warning') allows transition but logs warning."""
    sv = make_state()
    sv.save(state_path)
    gate = GateMechanism(state_path=state_path, event_log_path=log_path)
    gate.register(Check(
        name="soft_warning",
        condition=lambda ctx: (False, "warning"),
        message="soft issue",
        suggestion="Consider fixing",
    ))
    result = gate.verify_transition("arch_done", {})
    assert result.passed is True
    assert "soft_warning" in result.warnings


def test_force_transition_records_event(state_path, log_path):
    """force_transition() records a GATE_FORCED event."""
    sv = make_state()
    sv.save(state_path)
    gate = GateMechanism(state_path=state_path, event_log_path=log_path)
    gate.register(Check(
        name="blocker",
        condition=lambda ctx: (False, "error"),
        message="blocked",
        suggestion="Fix it",
    ))
    forced = gate.force_transition("arch_done", {}, reason="user override")
    assert forced is True
    # Verify event log
    import json
    with open(log_path) as f:
        events = [json.loads(line) for line in f]
    assert any(e["event_type"] == "gate_forced" for e in events)


def test_plugin_register_via_public_api(state_path, log_path):
    """register_gate_check() module-level function adds to default checks."""
    from skills._lib import gate as gate_mod
    sv = make_state()
    sv.save(state_path)
    gate = gate_mod.GateMechanism(state_path=state_path, event_log_path=log_path)
    # Add a custom check
    gate_mod.register_gate_check(Check(
        name="custom_plugin_check",
        condition=lambda ctx: (True, None),
        message="ok",
        suggestion="",
    ))
    assert "custom_plugin_check" in gate.get_registered_check_names()


def test_suggestion_contains_command(state_path, log_path):
    """Each failed check's message+severity is reported; suggestion must include a command."""
    sv = make_state()
    sv.save(state_path)
    gate = GateMechanism(state_path=state_path, event_log_path=log_path)
    gate.register(Check(
        name="needs_cmd",
        condition=lambda ctx: (False, "error"),
        message="blocked",
        suggestion="Run: pytest tests/",
    ))
    result = gate.verify_transition("arch_done", {})
    assert "pytest tests/" in result.suggestion or "Run:" in (result.suggestion or "")


def test_default_arch_done_checks_present(state_path, log_path):
    """Default checks for arch_done include adr_exists, roadmap_defined, gap_analysis_complete."""
    sv = make_state()
    sv.save(state_path)
    gate = GateMechanism(state_path=state_path, event_log_path=log_path, load_defaults=True)
    names = gate.get_registered_check_names()
    assert "adr_exists" in names
    assert "roadmap_defined" in names
    assert "gap_analysis_complete" in names


def test_default_plan_done_checks_present(state_path, log_path):
    """Default checks for plan_done include changes_committed, artifacts_complete, deps_analyzed."""
    sv = make_state()
    sv.save(state_path)
    gate = GateMechanism(state_path=state_path, event_log_path=log_path, load_defaults=True)
    names = gate.get_registered_check_names()
    assert "changes_committed" in names
    assert "artifacts_complete" in names
    assert "deps_analyzed" in names


def test_default_ship_done_checks_present(state_path, log_path):
    """Default checks for ship_done include worktrees_empty, archive_empty, tests_pass."""
    sv = make_state()
    sv.save(state_path)
    gate = GateMechanism(state_path=state_path, event_log_path=log_path, load_defaults=True)
    names = gate.get_registered_check_names()
    assert "worktrees_empty" in names
    assert "archive_empty" in names
    assert "tests_pass" in names


def test_get_suggestion_returns_aggregated_text(state_path, log_path):
    """get_suggestion() joins all failed-check suggestions into one string."""
    sv = make_state()
    sv.save(state_path)
    gate = GateMechanism(state_path=state_path, event_log_path=log_path)
    gate.register(Check("a", lambda ctx: (False, "error"), "a failed", "Fix A: run cmd-a"))
    gate.register(Check("b", lambda ctx: (False, "error"), "b failed", "Fix B: run cmd-b"))
    gate.verify_transition("arch_done", {})
    sug = gate.get_suggestion("arch_done")
    assert "cmd-a" in sug
    assert "cmd-b" in sug
