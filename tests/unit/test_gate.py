"""Tests for GateMechanism — phase-transition gate with two severity levels."""
import json
from pathlib import Path

import pytest
from skills._lib.gate import GateMechanism, Check
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
    """Default checks for arch_done include adr_exists + arch_alignment + adr_no_placeholders + arch_handoff_actionable.

    CHANGED 2026-09-30 (per ADR-0057): removed `gap_analysis_complete` and
    `arch_debt_recorded` checks (gap-analysis artifact type deleted;
    migration planning moved to rdd-planner per ADR-0057).
    """
    sv = make_state()
    sv.save(state_path)
    gate = GateMechanism(state_path=state_path, event_log_path=log_path, load_defaults=True)
    names = gate.get_registered_check_names()
    assert "adr_exists" in names
    assert "arch_alignment" in names


def test_default_arch_done_includes_quality_checks_adr0013(state_path, log_path):
    """ADR-0018 (modified by ADR-0057): arch_done must register qualitative checks (warning level by default).

    Per ADR-0057 (2026-09-30), `arch_debt_recorded` was removed when the
    gap-analysis artifact type was deleted. Remaining 3 quality checks
    (per ADR-0018): arch_alignment, adr_no_placeholders, arch_handoff_actionable.
    """
    sv = make_state()
    sv.save(state_path)
    gate = GateMechanism(state_path=state_path, event_log_path=log_path, load_defaults=True)
    names = gate.get_registered_check_names()
    for required in (
        "arch_alignment",
        "adr_no_placeholders",
        "arch_handoff_actionable",
    ):
        assert required in names, (
            f"arch_done must register {required} per ADR-0018+ADR-0057; "
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


def _seed_good_change_gate(root: str, name: str) -> None:
    from pathlib import Path
    change_dir = Path(root) / "openspec" / "changes" / name
    change_dir.mkdir(parents=True, exist_ok=True)
    proposal = (
        "## Why\n\n" + ("x" * 500) + "\n\nRefs ADR-0019.\n\n"
        "## In Scope\n\ndo thing\n\n## Out of Scope\n\nnot doing\n"
    )
    (change_dir / "proposal.md").write_text(proposal, encoding="utf-8")
    (change_dir / "tasks.md").write_text("## Tasks\n\n- [ ] one\n- [ ] two\n", encoding="utf-8")
    (Path(root) / "roadmap.md").write_text(f"# Roadmap\n\n- {name}\n", encoding="utf-8")


def test_plan_done_includes_propose_quality_checks(state_path, log_path):
    sv = make_state()
    sv.save(state_path)
    gate = GateMechanism(state_path=state_path, event_log_path=log_path, load_defaults=True)
    names = gate.get_registered_check_names()
    assert "propose_quality_checks" in names


def test_propose_quality_check_default_warning(state_path, log_path, tmp_path, monkeypatch):
    from skills._lib import gate as gate_mod
    _seed_good_change_gate(str(tmp_path), "c1")
    change_dir = tmp_path / "openspec" / "changes" / "c1"
    (change_dir / "proposal.md").write_text("## Why\n\nshort\n", encoding="utf-8")

    sv = make_state()
    sv.update_field("plan_side.active_change", "c1")
    sv.save(state_path)
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
    monkeypatch.delenv("STRICT_PROPOSE_GATE", raising=False)
    gate = gate_mod.GateMechanism(state_path=state_path, event_log_path=log_path, load_defaults=False)
    gate.register(gate_mod.Check(
        "propose_quality_checks",
        gate_mod.strict_wrap(gate_mod._check_propose_quality, env_var="STRICT_PROPOSE_GATE"),
        "propose quality checks failed",
        "Fix proposal/tasks content; see .rddf/state/propose-quality.json",
        "warning",
    ))
    result = gate.verify_transition("plan_done", {"project_root": str(tmp_path)})
    assert result.passed is True
    assert "propose_quality_checks" in result.warnings


def test_propose_quality_check_strict_error(state_path, log_path, tmp_path, monkeypatch):
    from skills._lib import gate as gate_mod
    _seed_good_change_gate(str(tmp_path), "c1")
    change_dir = tmp_path / "openspec" / "changes" / "c1"
    (change_dir / "proposal.md").write_text("## Why\n\nshort\n", encoding="utf-8")

    sv = make_state()
    sv.update_field("plan_side.active_change", "c1")
    sv.save(state_path)
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("STRICT_PROPOSE_GATE", "yes")
    gate = gate_mod.GateMechanism(state_path=state_path, event_log_path=log_path, load_defaults=False)
    gate.register(gate_mod.Check(
        "propose_quality_checks",
        gate_mod.strict_wrap(gate_mod._check_propose_quality, env_var="STRICT_PROPOSE_GATE"),
        "propose quality checks failed",
        "Fix proposal/tasks content; see .rddf/state/propose-quality.json",
        "warning",
    ))
    result = gate.verify_transition("plan_done", {"project_root": str(tmp_path)})
    assert result.passed is False
    assert "propose_quality_checks" in result.failed_checks


def test_propose_quality_check_missing_state_vector_skips(state_path, log_path):
    from skills._lib import gate as gate_mod
    passed, severity = gate_mod._check_propose_quality({})
    assert passed is True
    assert severity is None


def test_propose_quality_check_missing_state_file_reruns(state_path, log_path, tmp_path, monkeypatch):
    from skills._lib import gate as gate_mod
    _seed_good_change_gate(str(tmp_path), "c1")
    change_dir = tmp_path / "openspec" / "changes" / "c1"
    (change_dir / "proposal.md").write_text("## Why\n\nshort\n", encoding="utf-8")

    sv = make_state()
    sv.update_field("plan_side.active_change", "c1")
    sv.save(state_path)
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
    monkeypatch.delenv("STRICT_PROPOSE_GATE", raising=False)
    gate = gate_mod.GateMechanism(state_path=state_path, event_log_path=log_path, load_defaults=False)
    gate.register(gate_mod.Check(
        "propose_quality_checks",
        gate_mod.strict_wrap(gate_mod._check_propose_quality, env_var="STRICT_PROPOSE_GATE"),
        "propose quality checks failed",
        "Fix proposal/tasks content; see .rddf/state/propose-quality.json",
        "warning",
    ))
    result = gate.verify_transition("plan_done", {"project_root": str(tmp_path)})
    assert result.passed is True
    assert "propose_quality_checks" in result.warnings


# ── project_root anchoring for artifact checks (fix-path-anchoring-residue) ──
#
# These three checks are the only ones in gate.py that used bare cwd-relative
# paths ("openspec/changes/...", ".rddf/state/.deps-output.md") while the other
# checks in the same file already resolved through ctx["project_root"]. A gate
# that reads the wrong tree answers the wrong question — plan_done would pass
# an incomplete change whenever cwd != project_root.

def _seed_artifacts(root, name="c1", artifacts=("proposal.md", "design.md", "tasks.md")):
    change_dir = Path(root) / "openspec" / "changes" / name
    change_dir.mkdir(parents=True, exist_ok=True)
    for artifact in artifacts:
        (change_dir / artifact).write_text("## Why\n\nx\n", encoding="utf-8")
    return change_dir


def _ctx_with_change(project_root, name="c1"):
    sv = make_state()
    sv.update_field("arch_side.current_change", name)
    ctx = {"state_vector": sv}
    if project_root is not None:
        ctx["project_root"] = str(project_root)
    return ctx


def test_changes_committed_reads_project_root_not_cwd(tmp_path, monkeypatch):
    """AC-1: proposal.md lives under project_root, cwd has nothing → still passes."""
    from skills._lib import gate as gate_mod

    fake = tmp_path / "fake"
    _seed_artifacts(fake, "c1", ("proposal.md",))
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    assert gate_mod._check_changes_committed(_ctx_with_change(fake)) == (True, None)


def test_artifacts_complete_reads_project_root_not_cwd(tmp_path, monkeypatch):
    """AC-1: all three artifacts under project_root, cwd has nothing → passes."""
    from skills._lib import gate as gate_mod

    fake = tmp_path / "fake"
    _seed_artifacts(fake, "c1")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    assert gate_mod._check_artifacts_complete(_ctx_with_change(fake)) == (True, None)


def test_deps_analyzed_reads_project_root_not_cwd(tmp_path, monkeypatch):
    """AC-1: .deps-output.md under project_root is found; the openspec probe is
    stubbed out so the assertion is about the FILE LOOKUP, not about openspec."""
    from skills._lib import gate as gate_mod

    fake = tmp_path / "fake"
    deps_dir = fake / ".rddf" / "state"
    deps_dir.mkdir(parents=True)
    (deps_dir / ".deps-output.md").write_text("deps ok, long enough\n", encoding="utf-8")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    # openspec is not available in the sandbox: the check degrades to a warning.
    monkeypatch.setattr(
        gate_mod.subprocess, "run",
        lambda *a, **kw: (_ for _ in ()).throw(FileNotFoundError("openspec")),
    )

    passed, severity = gate_mod._check_deps_analyzed(_ctx_with_change(fake))
    assert passed is True
    assert severity == "warning"


def test_artifact_checks_default_to_cwd_when_project_root_absent(tmp_path, monkeypatch):
    """AC-2: ctx without project_root keeps the historical "." semantics."""
    from skills._lib import gate as gate_mod

    _seed_artifacts(tmp_path, "c1")
    monkeypatch.chdir(tmp_path)

    ctx = _ctx_with_change(None)
    assert gate_mod._check_changes_committed(ctx) == (True, None)
    assert gate_mod._check_artifacts_complete(ctx) == (True, None)
