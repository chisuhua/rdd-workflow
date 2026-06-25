"""Tests for skills._lib.tribunal — multi-agent cross-validation per ADR-0008.

The Tribunal coordinates two agents (Executor + Reviewer) for workflow
verification. Per ADR-0008 the judgment is weighted (0.4 exec / 0.6 review)
and passes only when the final score is high AND both individual scores
clear 0.5 AND the conflict between agents stays below 0.4.

These tests pin the contract: the formula, the pass conditions, the
sanitization pipeline, the same-agent warning, event-log recording, and
graceful degradation when an agent raises.
"""
from __future__ import annotations
import os
from typing import Any, Dict, List

import pytest


# ---------------------------------------------------------------------------
# Helpers — keep tests focused on Tribunal behavior, not on the
# callable scaffolding. The executor and reviewer are simple lambdas /
# closures that capture their inputs so we can assert what the Tribunal
# forwarded to them.
# ---------------------------------------------------------------------------


def _executor_stub(score: float, capture: Dict[str, Any] | None = None):
    """Build an executor callable returning ``score`` and optionally recording inputs."""
    def _exec(change_name: str, criteria: str, sanitized_context: dict) -> float:
        if capture is not None:
            capture["change_name"] = change_name
            capture["criteria"] = criteria
            capture["context"] = dict(sanitized_context)
        return score
    return _exec


def _reviewer_stub(score: float, capture: Dict[str, Any] | None = None):
    """Build a reviewer callable returning ``score`` and optionally recording inputs."""
    def _review(change_name: str, criteria: str, sanitized_context: dict) -> float:
        if capture is not None:
            capture["change_name"] = change_name
            capture["criteria"] = criteria
            capture["context"] = dict(sanitized_context)
        return score
    return _review


@pytest.fixture
def event_log_path(tmp_path):
    """Return a per-test event log path inside tmp_path (auto-cleaned)."""
    return str(tmp_path / "event-log.jsonl")


# ---------------------------------------------------------------------------
# Formula
# ---------------------------------------------------------------------------


def test_judge_formula_weighted():
    """_judge applies the weighted formula: 0.4 * exec + 0.6 * review.

    ADR-0008 weights reviewer (quality/correctness) higher than executor
    (task completion) because review is the more expensive signal.
    """
    from skills._lib.tribunal import Tribunal

    tribunal = Tribunal(executor=_executor_stub(0.0), reviewer=_executor_stub(0.0))
    final, conflict = tribunal._judge(exec_score=0.5, review_score=1.0)

    # 0.5 * 0.4 + 1.0 * 0.6 = 0.2 + 0.6 = 0.8
    assert final == pytest.approx(0.8)
    # Conflict is |exec - review| = 0.5
    assert conflict == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Pass conditions
# ---------------------------------------------------------------------------


def test_pass_when_high_both():
    """Both agents high → final ≥ 0.8, conflict < 0.4, both ≥ 0.5 → pass.

    ADR-0008 scenario 'High confidence passes': exec=0.9, review=0.95 →
    final = 0.93, no conflict, pass.
    """
    from skills._lib.tribunal import Tribunal

    tribunal = Tribunal(executor=_executor_stub(0.9), reviewer=_reviewer_stub(0.95))
    result = tribunal.verify("change-x", "criteria-y", {})

    assert result.passed is True
    assert result.exec_score == pytest.approx(0.9)
    assert result.review_score == pytest.approx(0.95)
    assert result.final_score == pytest.approx(0.93)
    assert result.conflict == pytest.approx(0.05)


def test_fail_when_low_final_score():
    """Final score below 0.8 → fail, even if both agents pass individually.

    ADR-0008 scenario 'Borderline final score': exec=0.7, review=0.85 →
    final = 0.79 (< 0.8 threshold).
    """
    from skills._lib.tribunal import Tribunal

    tribunal = Tribunal(executor=_executor_stub(0.7), reviewer=_reviewer_stub(0.85))
    result = tribunal.verify("change-x", "criteria-y", {})

    assert result.passed is False
    assert result.final_score == pytest.approx(0.79)


def test_fail_when_high_conflict():
    """Conflict ≥ 0.4 → fail regardless of final score.

    ADR-0008 scenario 'High conflict warns': exec=0.9, review=0.4 →
    conflict = 0.5 → fail with high disagreement.
    """
    from skills._lib.tribunal import Tribunal

    tribunal = Tribunal(executor=_executor_stub(0.9), reviewer=_reviewer_stub(0.4))
    result = tribunal.verify("change-x", "criteria-y", {})

    assert result.passed is False
    assert result.conflict == pytest.approx(0.5)
    # Final still computed correctly: 0.9 * 0.4 + 0.4 * 0.6 = 0.36 + 0.24 = 0.6
    assert result.final_score == pytest.approx(0.6)


def test_fail_when_one_agent_low():
    """If either agent < 0.5 the result fails even if the other is 1.0.

    A single very-low score is a veto per ADR-0008 — the bar is meant to
    guard against agent collapse (e.g. one model returning 0.1 by mistake).
    """
    from skills._lib.tribunal import Tribunal

    tribunal = Tribunal(executor=_executor_stub(0.1), reviewer=_reviewer_stub(1.0))
    result = tribunal.verify("change-x", "criteria-y", {})

    assert result.passed is False
    assert result.exec_score == pytest.approx(0.1)
    # Final = 0.1 * 0.4 + 1.0 * 0.6 = 0.04 + 0.6 = 0.64 (well below 0.8 too,
    # but the per-agent floor is the formal reason)
    assert result.final_score == pytest.approx(0.64)


# ---------------------------------------------------------------------------
# Same-agent warning
# ---------------------------------------------------------------------------


def test_warn_when_same_agent():
    """If executor is the same callable as reviewer, emit a warning.

    The verification still runs (it does not fail), but the caller is
    alerted that cross-validation has been disabled. ADR-0008 mandates
    that Executor and Reviewer MUST be different agents.
    """
    from skills._lib.tribunal import Tribunal

    agent = _executor_stub(0.9)
    tribunal = Tribunal(executor=agent, reviewer=agent)
    result = tribunal.verify("change-x", "criteria-y", {})

    assert any("same" in w.lower() for w in result.warnings)


# ---------------------------------------------------------------------------
# Sanitization
# ---------------------------------------------------------------------------


def test_sanitize_context_before_invocation():
    """Secrets in the input context are redacted before reaching either agent.

    The executor and reviewer MUST see sanitized context, not the raw
    payload. We capture what each agent actually receives and assert that
    the API key no longer appears.
    """
    from skills._lib.tribunal import Tribunal

    exec_capture: Dict[str, Any] = {}
    review_capture: Dict[str, Any] = {}

    tribunal = Tribunal(
        executor=_executor_stub(0.9, exec_capture),
        reviewer=_reviewer_stub(0.95, review_capture),
    )

    secret = "sk-abc123def456ghi789jkl012mno"
    context = {"api_key": secret, "safe": "hello"}
    tribunal.verify("change-x", "criteria-y", context)

    # The redacted placeholder must have replaced the secret in both payloads.
    assert exec_capture["context"]["api_key"] != secret
    assert "<REDACTED>" in exec_capture["context"]["api_key"]
    assert review_capture["context"]["api_key"] != secret
    assert "<REDACTED>" in review_capture["context"]["api_key"]
    # Non-secret values are preserved.
    assert exec_capture["context"]["safe"] == "hello"


# ---------------------------------------------------------------------------
# Event log
# ---------------------------------------------------------------------------


def test_record_verification_event(event_log_path):
    """When an event log is provided, the Tribunal records the verification result.

    The recorded event captures the change_name, passed flag, and final_score
    in its context so downstream tools (status report, audit log) can read
    verification outcomes from the event log without re-running the Tribunal.
    """
    from skills._lib.event_log import EventLog
    from skills._lib.tribunal import Tribunal

    log = EventLog(event_log_path)
    tribunal = Tribunal(
        executor=_executor_stub(0.9),
        reviewer=_reviewer_stub(0.95),
        event_log=log,
    )
    result = tribunal.verify("change-x", "criteria-y", {"note": "no secrets"})

    events = log.query()
    assert len(events) == 1
    event = events[0]
    assert event.context.get("change_name") == "change-x"
    assert event.context.get("passed") is True
    assert event.context.get("final_score") == pytest.approx(0.93)


# ---------------------------------------------------------------------------
# Graceful degradation
# ---------------------------------------------------------------------------


def test_graceful_degradation_on_exception():
    """When an agent raises, the Tribunal does not propagate the exception.

    The verification returns a result (with a warning) instead of crashing
    the whole workflow. ADR-0008 mandates falling back to single-agent
    verification when cross-validation cannot proceed.
    """
    from skills._lib.tribunal import Tribunal

    def broken_executor(change_name: str, criteria: str, context: dict) -> float:
        raise RuntimeError("executor crashed: agent offline")

    def good_reviewer(change_name: str, criteria: str, context: dict) -> float:
        return 0.9

    tribunal = Tribunal(executor=broken_executor, reviewer=good_reviewer)

    # Must not raise.
    result = tribunal.verify("change-x", "criteria-y", {})

    # Result is still a TribunalResult, with at least one warning describing
    # the failure.
    assert result is not None
    assert any(
        ("executor" in w.lower() or "crash" in w.lower() or "fail" in w.lower())
        for w in result.warnings
    )
    # The verification itself fails (broken agent yields 0.0 or low score)
    # — that is the point: callers know to retry or escalate.
    assert result.passed is False
