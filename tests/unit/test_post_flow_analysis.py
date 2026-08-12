"""Tests for ADR-0027 §1.2 post-flow-analysis three-way classifier.

Classifier priorities: usage-error → environment-error → flow-bug (DEFAULT-FAIL-OPEN).
Exit codes 130/143 (SIGINT/SIGTERM) are excluded from classification.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from unittest import mock

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT / "_lib"))

from post_flow_analysis import (  # type: ignore[import-not-found]
    PhaseOutcome,
    Classification,
    classify_phase_outcome,
    report_flow_bug,
    ROOT_CAUSE_USAGE,
    ROOT_CAUSE_ENV,
    ROOT_CAUSE_FLOW,
    REPORT_CATEGORY_FLOW,
    REPORT_CATEGORY_GATE,
    REPORT_CATEGORY_CRASH,
)


# ── 1.1 / 1.2: Dataclass + OK early-return ─────────────────────────────


def test_phase_outcome_dataclass_accepts_required_fields():
    outcome = PhaseOutcome(phase="execute", exit_code=0)
    assert outcome.phase == "execute"
    assert outcome.exit_code == 0
    assert outcome.stderr == ""
    assert outcome.stdout_tail == ""
    assert outcome.traceback == ""


def test_classify_exit_code_zero_returns_ok_no_report():
    """Success path: phase completed normally, no classification, no report."""
    outcome = PhaseOutcome(phase="guide-plan", exit_code=0)
    cls = classify_phase_outcome(phase="guide-plan", outcome=outcome)
    assert cls.should_report is False
    assert cls.root_cause == ROOT_CAUSE_FLOW  # OK placeholder
    assert cls.report_category is None


# ── 1.3-1.4: usage-error detection ────────────────────────────────────


def test_usage_error_u1_argparse_unrecognized_arguments():
    outcome = PhaseOutcome(
        phase="guide-plan", exit_code=2,
        stderr="usage: rddf report-issue [-h] description\nerror: unrecognized arguments: --bogus",
    )
    cls = classify_phase_outcome(phase="guide-plan", outcome=outcome)
    assert cls.root_cause == ROOT_CAUSE_USAGE
    assert cls.should_report is False
    assert cls.matched_rule == "U1"
    assert "用法" in cls.user_hint or "用法" in cls.description or "用法" in cls.user_hint.lower()


def test_usage_error_u2_argparse_argument_error_exception():
    """argparse.ArgumentError raised during phase → usage-error."""
    outcome = PhaseOutcome(
        phase="guide-arch", exit_code=2,
        stderr="argparse.ArgumentError: argument --required is required",
    )
    cls = classify_phase_outcome(phase="guide-arch", outcome=outcome)
    assert cls.root_cause == ROOT_CAUSE_USAGE
    assert cls.matched_rule in ("U1", "U2")


def test_usage_error_u4_missing_required_flag():
    outcome = PhaseOutcome(
        phase="execute", exit_code=2,
        stderr="Error: missing required flag --change-name",
    )
    cls = classify_phase_outcome(phase="execute", outcome=outcome)
    assert cls.root_cause == ROOT_CAUSE_USAGE
    assert cls.matched_rule == "U4"


def test_usage_error_chinese_run_x_first():
    """Chinese skill helper messages ('先执行') trigger U4."""
    outcome = PhaseOutcome(
        phase="guide-plan", exit_code=2,
        stderr="错误：请先执行 guide-arch，再做 plan",
    )
    cls = classify_phase_outcome(phase="guide-plan", outcome=outcome)
    assert cls.root_cause == ROOT_CAUSE_USAGE
    assert cls.matched_rule == "U4"


# ── 1.5-1.7: environment-error detection ─────────────────────────────


def test_env_error_e1_missing_tool_gh():
    outcome = PhaseOutcome(
        phase="guide-ship", exit_code=127,
        stderr="bash: gh: command not found",
    )
    cls = classify_phase_outcome(phase="guide-ship", outcome=outcome)
    assert cls.root_cause == ROOT_CAUSE_ENV
    assert cls.matched_rule == "E1"
    assert cls.should_report is False
    assert "gh" in cls.metadata.get("missing_tool", "") or "gh" in cls.description


def test_env_error_e2_permission_denied_outside_project():
    outcome = PhaseOutcome(
        phase="execute", exit_code=1,
        stderr="Permission denied: /etc/openspec/config.yaml",
    )
    cls = classify_phase_outcome(phase="execute", outcome=outcome)
    assert cls.root_cause == ROOT_CAUSE_ENV
    assert cls.matched_rule == "E2"


def test_env_error_e3_network_timeout():
    outcome = PhaseOutcome(
        phase="guide-ship", exit_code=1,
        stderr="Failed to connect to github.com: Connection timed out",
    )
    cls = classify_phase_outcome(phase="guide-ship", outcome=outcome)
    assert cls.root_cause == ROOT_CAUSE_ENV
    assert cls.matched_rule == "E3"


def test_env_error_e4_disk_full():
    outcome = PhaseOutcome(
        phase="guide-plan", exit_code=1,
        stderr="OSError: [Errno 28] No space left on device: '.rddf/'",
    )
    cls = classify_phase_outcome(phase="guide-plan", outcome=outcome)
    assert cls.root_cause == ROOT_CAUSE_ENV
    assert cls.matched_rule == "E4"


# ── 1.8 / 1.14: flow-bug detection ───────────────────────────────────


def test_flow_bug_f1_traceback_in_lib():
    """Traceback whose last frame is in _lib/ → flow-bug, fine-grained phase-crash."""
    tb = (
        "Traceback (most recent call last):\n"
        '  File "/workspace/project/rdd-workflow/_lib/issue_reporter.py", line 67, in detect_issue\n'
        "    category: One of the ADR-0027 §1 categories\n"
        "KeyError: 'flow-bug'\n"
    )
    outcome = PhaseOutcome(phase="execute", exit_code=1, stderr=tb, traceback=tb)
    cls = classify_phase_outcome(phase="execute", outcome=outcome)
    assert cls.root_cause == ROOT_CAUSE_FLOW
    assert cls.should_report is True
    assert cls.report_category == REPORT_CATEGORY_CRASH
    assert cls.matched_rule == "F1"
    assert len(cls.stack) > 0


def test_flow_bug_f3_state_machine_violation_english():
    outcome = PhaseOutcome(
        phase="guide-ship", exit_code=1,
        stderr="ERROR: invalid state — expected 'planned' but got 'archived'",
    )
    cls = classify_phase_outcome(phase="guide-ship", outcome=outcome)
    assert cls.root_cause == ROOT_CAUSE_FLOW
    assert cls.matched_rule == "F3"


def test_flow_bug_f3_state_machine_violation_chinese():
    outcome = PhaseOutcome(
        phase="guide-plan", exit_code=1,
        stderr="错误：状态机违反 — 当前状态无法转换到下一阶段",
    )
    cls = classify_phase_outcome(phase="guide-plan", outcome=outcome)
    assert cls.root_cause == ROOT_CAUSE_FLOW
    assert cls.matched_rule == "F3"


# ── 1.10: DEFAULT-FAIL-OPEN ──────────────────────────────────────────


def test_default_fail_open_unmatched_failure():
    """exit_code=1 + stderr empty + no U/E match → flow-bug (fail-open)."""
    outcome = PhaseOutcome(phase="execute", exit_code=1, stderr="some random text")
    cls = classify_phase_outcome(phase="execute", outcome=outcome)
    assert cls.root_cause == ROOT_CAUSE_FLOW
    assert cls.should_report is True
    assert cls.report_category == REPORT_CATEGORY_FLOW
    assert cls.matched_rule == "DEFAULT-FAIL-OPEN"


# ── 1.11 / 1.12: SIGINT/SIGTERM excluded ──────────────────────────────


def test_sigint_exit_130_no_classification():
    """Ctrl+C (exit 130) is user-cancelled, not a bug."""
    outcome = PhaseOutcome(phase="guide-plan", exit_code=130, stderr="KeyboardInterrupt")
    cls = classify_phase_outcome(phase="guide-plan", outcome=outcome)
    assert cls.should_report is False
    assert cls.matched_rule == "SIGINT-EXCLUDED"


def test_sigterm_exit_143_no_classification():
    outcome = PhaseOutcome(phase="guide-ship", exit_code=143, stderr="")
    cls = classify_phase_outcome(phase="guide-ship", outcome=outcome)
    assert cls.should_report is False
    assert cls.matched_rule == "SIGINT-EXCLUDED"


# ── 1.13: traceback but all stdlib frames → usage, not flow ─────────


def test_traceback_all_stdlib_frames_classified_as_usage():
    """argparse-only traceback is usage-error, not flow-bug."""
    tb = (
        "Traceback (most recent call last):\n"
        '  File "/usr/lib/python3.12/argparse.py", line 1850, in parse_args\n'
        "    self.error(msg)\n"
        '  File "/usr/lib/python3.12/argparse.py", line 2455, in error\n'
        "    self.exit(2, msg)\n"
        "SystemExit: 2\n"
    )
    outcome = PhaseOutcome(phase="guide-arch", exit_code=2, stderr=tb, traceback=tb)
    cls = classify_phase_outcome(phase="guide-arch", outcome=outcome)
    assert cls.root_cause == ROOT_CAUSE_USAGE
    assert cls.should_report is False


# ── report_flow_bug orchestration ─────────────────────────────────────


def test_report_flow_bug_writes_issue_file(tmp_path, monkeypatch):
    """report_flow_bug with flow-bug classification writes a local issue file."""
    from post_flow_analysis import PhaseOutcome, classify_phase_outcome, report_flow_bug
    tb = (
        "Traceback (most recent call last):\n"
        '  File "/workspace/project/rdd-workflow/_lib/foo.py", line 10, in bar\n'
        "    raise RuntimeError('boom')\n"
        "RuntimeError: boom\n"
    )
    outcome = PhaseOutcome(phase="execute", exit_code=1, stderr=tb, traceback=tb)
    cls = classify_phase_outcome(phase="execute", outcome=outcome)
    file_path = report_flow_bug(cls, project_root=str(tmp_path))
    assert file_path is not None
    assert file_path.exists()
    assert file_path.name.startswith("phase-crash-") or file_path.name.startswith("flow-bug-")


def test_report_flow_bug_returns_none_for_usage_error(tmp_path):
    """usage-error classification does NOT write any file."""
    from post_flow_analysis import PhaseOutcome, classify_phase_outcome, report_flow_bug
    outcome = PhaseOutcome(
        phase="guide-plan", exit_code=2,
        stderr="error: unrecognized arguments: --bogus",
    )
    cls = classify_phase_outcome(phase="guide-plan", outcome=outcome)
    file_path = report_flow_bug(cls, project_root=str(tmp_path))
    assert file_path is None
    issues_dir = tmp_path / ".rddf" / "issues"
    if issues_dir.exists():
        assert list(issues_dir.glob("*.md")) == []


def test_report_flow_bug_returns_none_for_env_error(tmp_path):
    """env-error classification does NOT write any file."""
    from post_flow_analysis import PhaseOutcome, classify_phase_outcome, report_flow_bug
    outcome = PhaseOutcome(phase="guide-ship", exit_code=127, stderr="bash: gh: command not found")
    cls = classify_phase_outcome(phase="guide-ship", outcome=outcome)
    file_path = report_flow_bug(cls, project_root=str(tmp_path))
    assert file_path is None


# ── _should_auto_submit three-gate logic (ADR-0027 design gap fix) ───


def test_should_auto_submit_disabled_by_default(monkeypatch):
    """Without any RDDF_REPORT_* env vars set, auto-submit is off (L1 only)."""
    monkeypatch.delenv("RDDF_REPORT_ENABLED", raising=False)
    monkeypatch.delenv("RDDF_REPORT_AUTO_SUBMIT", raising=False)
    monkeypatch.delenv("RDDF_REPORT_SUBMIT_CATEGORIES", raising=False)
    from post_flow_analysis import _should_auto_submit
    assert _should_auto_submit("phase-crash") is False


def test_should_auto_submit_requires_both_enabled_and_auto_submit(monkeypatch):
    """Both RDDF_REPORT_ENABLED=yes AND RDDF_REPORT_AUTO_SUBMIT=yes required."""
    monkeypatch.delenv("RDDF_REPORT_ENABLED", raising=False)
    monkeypatch.delenv("RDDF_REPORT_AUTO_SUBMIT", raising=False)
    monkeypatch.delenv("RDDF_REPORT_SUBMIT_CATEGORIES", raising=False)
    from post_flow_analysis import _should_auto_submit
    monkeypatch.setenv("RDDF_REPORT_ENABLED", "yes")
    assert _should_auto_submit("phase-crash") is False
    monkeypatch.setenv("RDDF_REPORT_AUTO_SUBMIT", "yes")
    assert _should_auto_submit("phase-crash") is True


def test_should_auto_submit_per_category_filter(monkeypatch):
    """RDDF_REPORT_SUBMIT_CATEGORIES limits which categories submit."""
    monkeypatch.setenv("RDDF_REPORT_ENABLED", "yes")
    monkeypatch.setenv("RDDF_REPORT_AUTO_SUBMIT", "yes")
    monkeypatch.setenv("RDDF_REPORT_SUBMIT_CATEGORIES", "flow-bug,gate-failure")
    from post_flow_analysis import _should_auto_submit
    assert _should_auto_submit("flow-bug") is True
    assert _should_auto_submit("gate-failure") is True
    assert _should_auto_submit("phase-crash") is False
    assert _should_auto_submit("manual") is False


def test_should_auto_submit_disabled_in_ci_environment(monkeypatch):
    """CI markers disable L2 submission even with both env vars set."""
    monkeypatch.setenv("RDDF_REPORT_ENABLED", "yes")
    monkeypatch.setenv("RDDF_REPORT_AUTO_SUBMIT", "yes")
    monkeypatch.setenv("CI", "true")
    from post_flow_analysis import _should_auto_submit
    assert _should_auto_submit("phase-crash") is False
    monkeypatch.delenv("CI")
    assert _should_auto_submit("phase-crash") is True


def test_report_flow_bug_auto_submits_when_enabled(tmp_path, monkeypatch):
    """End-to-end: enabled+auto_submit triggers gh submission and updates file."""
    monkeypatch.setenv("RDDF_REPORT_ENABLED", "yes")
    monkeypatch.setenv("RDDF_REPORT_AUTO_SUBMIT", "yes")
    monkeypatch.setenv("RDDF_REPORT_GH_REPO", "owner/repo")
    monkeypatch.setenv("CI", "")  # ensure not CI

    fake_proc = mock.Mock(returncode=0, stdout="https://github.com/owner/repo/issues/42", stderr="")
    with mock.patch("subprocess.run", return_value=fake_proc) as m:
        from post_flow_analysis import PhaseOutcome, classify_phase_outcome, report_flow_bug
        tb = (
            "Traceback (most recent call last):\n"
            '  File "/workspace/project/rdd-workflow/_lib/foo.py", line 10, in bar\n'
            "    raise RuntimeError('x')\n"
            "RuntimeError: x\n"
        )
        outcome = PhaseOutcome(phase="execute", exit_code=1, stderr=tb, traceback=tb)
        cls = classify_phase_outcome(phase="execute", outcome=outcome)
        file_path = report_flow_bug(cls, project_root=str(tmp_path))

    assert file_path is not None
    content = file_path.read_text()
    assert "submitted: true" in content
    assert "https://github.com/owner/repo/issues/42" in content
    # Verify gh CLI was called with the right label set
    gh_calls = [c for c in m.call_args_list if "issue" in str(c) and "create" in str(c)]
    assert any("auto-reported" in str(c) and "phase-crash" in str(c) and "needs-triage" in str(c) for c in gh_calls)
