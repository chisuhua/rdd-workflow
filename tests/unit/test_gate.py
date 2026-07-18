"""Tests for GateMechanism — phase-transition gate with two severity levels."""
import json
import os
import pytest
from skills._lib.gate import GateMechanism, Check, GateResult, GateError, register_gate_check
from skills._lib.core.state_vector import StateVector


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


def test_default_arch_done_includes_quality_checks_adr0013(state_path, log_path):
    """ADR-0018: arch_done must register 4 qualitative checks (warning level by default)."""
    sv = make_state()
    sv.save(state_path)
    gate = GateMechanism(state_path=state_path, event_log_path=log_path, load_defaults=True)
    names = gate.get_registered_check_names()
    for required in (
        "arch_alignment",
        "arch_debt_recorded",
        "adr_no_placeholders",
        "arch_handoff_actionable",
    ):
        assert required in names, (
            f"arch_done must register {required} per ADR-0018; "
            f"registered: {names}"
        )


def test_default_plan_done_checks_present(state_path, log_path):
    """Default checks for plan_done include changes_committed, artifacts_complete, deps_analyzed."""
    sv = make_state()
    sv.save(state_path)
    gate = GateMechanism(state_path=state_path, event_log_path=log_path, load_defaults=True)
    names = gate.get_registered_check_names()
    assert "changes_committed" in names
    assert "artifacts_complete" in names
    assert "deps_analyzed" in names


def test_default_plan_done_includes_change_alignment_checks_adr0019(state_path, log_path):
    """ADR-0019: plan_done must register 3 change-alignment checks with STRICT_CHANGE_GATE upgrade."""
    sv = make_state()
    sv.save(state_path)
    gate = GateMechanism(state_path=state_path, event_log_path=log_path, load_defaults=True)
    names = gate.get_registered_check_names()
    for required in (
        "change_adr_refs_valid",
        "change_no_contradiction",
        "change_task_traceability",
    ):
        assert required in names, (
            f"plan_done must register {required} per ADR-0019; "
            f"registered: {names}"
        )


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


# --- ADR-0015: openspec_validate as plan-critic ---


def test_check_openspec_validate_passes_when_json_clean(monkeypatch):
    """`_check_openspec_validate` returns (True, None) when openspec JSON summary shows 0 failed."""
    from skills._lib import gate as gate_mod

    clean_report = {
        "items": [
            {"id": "test-capability", "type": "spec", "valid": True, "issues": []},
        ],
        "summary": {"totals": {"items": 1, "passed": 1, "failed": 0}, "byType": {"spec": {"items": 1, "passed": 1, "failed": 0}}},
        "version": "1.0",
    }

    class _FakeRun:
        returncode = 0
        stdout = json.dumps(clean_report)
        stderr = ""

    monkeypatch.setattr(gate_mod.subprocess, "run", lambda *a, **kw: _FakeRun())

    passed, severity = gate_mod._check_openspec_validate({})
    assert passed is True
    assert severity is None


def test_check_openspec_validate_fails_when_summary_has_failures(monkeypatch):
    """`_check_openspec_validate` returns (False, 'error') when JSON summary shows failed > 0."""
    from skills._lib import gate as gate_mod

    failing_report = {
        "items": [
            {
                "id": "broken-spec",
                "type": "spec",
                "valid": False,
                "issues": [{"level": "ERROR", "path": "file", "message": "Missing ## Purpose"}],
            }
        ],
        "summary": {"totals": {"items": 1, "passed": 0, "failed": 1}, "byType": {"spec": {"items": 1, "passed": 0, "failed": 1}}},
        "version": "1.0",
    }

    class _FakeRun:
        returncode = 1
        stdout = json.dumps(failing_report)
        stderr = ""

    monkeypatch.setattr(gate_mod.subprocess, "run", lambda *a, **kw: _FakeRun())

    passed, severity = gate_mod._check_openspec_validate({})
    assert passed is False
    assert severity == "error"


def test_check_openspec_validate_degrades_to_warning_when_cli_unavailable(monkeypatch):
    """`_check_openspec_validate` returns (True, 'warning') when openspec CLI is not on PATH."""
    from skills._lib import gate as gate_mod

    def _raise_file_not_found(*a, **kw):
        raise FileNotFoundError("openspec not found")

    monkeypatch.setattr(gate_mod.subprocess, "run", _raise_file_not_found)

    passed, severity = gate_mod._check_openspec_validate({})
    assert passed is True
    assert severity == "warning"


def test_default_plan_done_checks_include_openspec_validate(state_path, log_path):
    """plan_done default checks must include the new openspec_validate check (ADR-0015)."""
    sv = make_state()
    sv.save(state_path)
    gate = GateMechanism(state_path=state_path, event_log_path=log_path, load_defaults=True)
    names = gate.get_registered_check_names()
    assert "openspec_validate" in names, (
        "plan_done must now enforce OpenSpec schema via openspec_validate check; "
        "see ADR-0015. plan_done checks were: " + ", ".join(names)
    )
