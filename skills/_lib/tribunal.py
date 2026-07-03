"""Multi-agent cross-validation Tribunal per ADR-0008.

The Tribunal coordinates two independent agents (Executor + Reviewer) to
verify workflow decisions with weighted judgment. It is the backend for
``VerificationMode.MULTI_MODEL`` in :mod:`skills._lib.human_nodes`.

Key invariants (per ADR-0008):
- Formula:    ``final_score = exec_score * 0.4 + review_score * 0.6``
- Pass when:  ``final_score ≥ 0.8 AND exec_score ≥ 0.5
                AND review_score ≥ 0.5 AND conflict < 0.4``
- Sanitize:   the input context is run through
              :func:`skills._lib.sanitizer.sanitize` before being
              forwarded to either agent (data privacy across model
              boundaries).
- Same-agent: when executor and reviewer are the same object, a warning
              is recorded but the verification still runs (caller
              decides whether to trust a non-cross-validated result).
- Graceful:   an exception in either agent is caught, surfaced as a
              warning, and degrades that agent's score to 0.0 so the
              overall verification fails safely.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from skills._lib.event_log import EventLog  # noqa: F401  (type hint for clarity)
from skills._lib.event_types import EventType, Severity
from skills._lib.sanitizer import sanitize as _default_sanitize


# ---------------------------------------------------------------------------
# Constants — the ADR-0008 contract, exposed as module-level names so
# callers and tests can reference them without hard-coding magic numbers.
# ---------------------------------------------------------------------------

EXEC_WEIGHT: float = 0.4
"""Weight applied to the executor's score in the final judgment."""

REVIEW_WEIGHT: float = 0.6
"""Weight applied to the reviewer's score in the final judgment."""

PASS_FINAL_THRESHOLD: float = 0.8
"""Minimum final_score required to pass."""

PASS_MIN_AGENT_SCORE: float = 0.5
"""Per-agent floor; a single sub-0.5 score is a veto."""

PASS_MAX_CONFLICT: float = 0.4
"""Maximum |exec_score − review_score| allowed for a pass."""


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class TribunalResult:
    """Outcome of a single Tribunal verification.

    Attributes:
        passed: True iff all four pass conditions hold (see module docstring).
        exec_score: Raw score returned by the executor agent (0.0-1.0).
        review_score: Raw score returned by the reviewer agent (0.0-1.0).
        final_score: Weighted combination per ADR-0008 formula.
        conflict: |exec_score − review_score| — disagreement signal.
        warnings: Non-fatal issues observed during the run (same-agent
            reuse, agent exceptions, etc.).
    """

    passed: bool
    exec_score: float
    review_score: float
    final_score: float
    conflict: float
    warnings: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public type aliases — executor and reviewer are simple callables.
# ---------------------------------------------------------------------------

# A verifier returns a score in [0.0, 1.0]. It MUST be a pure function of
# (change_name, criteria, sanitized_context); no I/O, no globals, no
# side effects beyond returning a float.
Verifier = Callable[[str, str, Dict[str, Any]], float]
"""Signature: (change_name, criteria, sanitized_context) -> score in [0.0, 1.0]."""


# Optional sanitizer hook: signature (dict) -> dict. The Tribunal also
# accepts None and falls back to the module-level :func:`sanitize`
# (applied to every string value in the input context).
ContextSanitizer = Callable[[Dict[str, Any]], Dict[str, Any]]


# ---------------------------------------------------------------------------
# Tribunal
# ---------------------------------------------------------------------------


class Tribunal:
    """Coordinate Executor + Reviewer for multi-agent cross-validation.

    The Tribunal is the runtime realization of the ADR-0008 specification.
    It is intentionally a small class: configuration in the constructor,
    single entry point :meth:`verify`, and one private helper
    :meth:`_judge` that computes the weighted score and the conflict.

    Example:
        >>> from skills._lib.tribunal import Tribunal
        >>> t = Tribunal(
        ...     executor=lambda n, c, ctx: 0.9,
        ...     reviewer=lambda n, c, ctx: 0.95,
        ... )
        >>> r = t.verify("my-change", "ships green tests", {"note": "no secrets"})
        >>> r.passed
        True
    """

    def __init__(
        self,
        executor: Verifier,
        reviewer: Verifier,
        sanitizer: Optional[ContextSanitizer] = None,
        event_log: Optional["EventLog"] = None,
    ) -> None:
        if not callable(executor):
            raise TypeError("executor must be a callable (change_name, criteria, context) -> float")
        if not callable(reviewer):
            raise TypeError("reviewer must be a callable (change_name, criteria, context) -> float")
        self.executor: Verifier = executor
        self.reviewer: Verifier = reviewer
        # If no sanitizer is provided we use the project-wide one, which
        # redacts API keys, passwords, and sensitive paths in every string
        # value of the input context. The hook is injectable for tests and
        # for callers that want a different redaction policy.
        self.sanitizer: ContextSanitizer = sanitizer or self._default_sanitize
        self.event_log: Optional["EventLog"] = event_log

    # ── Public API ──────────────────────────────────────────────────────

    def verify(
        self,
        change_name: str,
        criteria: str,
        context: Dict[str, Any],
    ) -> TribunalResult:
        """Run cross-validation for ``change_name`` against ``criteria``.

        Steps:
            1. Warn if executor and reviewer are the same object.
            2. Sanitize ``context`` (defaults to the project sanitizer).
            3. Invoke both agents in a try/except (graceful degradation).
            4. Compute final_score and conflict via :meth:`_judge`.
            5. Decide pass/fail from the four ADR-0008 conditions.
            6. Optionally record a verification event to ``self.event_log``.

        Args:
            change_name: Identifier of the change being verified.
            criteria: Human-readable success criteria the agents score against.
            context: Arbitrary context dict forwarded (sanitized) to both agents.

        Returns:
            :class:`TribunalResult` with all computed scores and any warnings.
        """
        warnings: List[str] = []

        # Step 1 — same-agent warning (per ADR-0008 § same-agent warning).
        if self.executor is self.reviewer:
            warnings.append(
                "executor and reviewer are the same agent; cross-validation disabled"
            )

        # Step 2 — sanitize the context before any cross-model boundary.
        sanitized_context: Dict[str, Any] = self.sanitizer(context)

        # Step 3 — invoke both agents with graceful degradation.
        # change_name and criteria are routing metadata, not payload, so
        # they bypass sanitization (only context values are redacted).
        exec_score: float = self._invoke_agent(
            self.executor, "executor", change_name, criteria, sanitized_context, warnings,
        )
        review_score: float = self._invoke_agent(
            self.reviewer, "reviewer", change_name, criteria, sanitized_context, warnings,
        )

        # Step 4 — compute the weighted judgment.
        final_score: float
        conflict: float
        final_score, conflict = self._judge(exec_score, review_score)

        # Step 5 — decide pass/fail. The per-agent floor (PASS_MIN_AGENT_SCORE)
        # is the *formal* reason for a low single-agent score; the
        # final_score check is what catches the borderline-weighted case.
        passed: bool = (
            final_score >= PASS_FINAL_THRESHOLD
            and exec_score >= PASS_MIN_AGENT_SCORE
            and review_score >= PASS_MIN_AGENT_SCORE
            and conflict < PASS_MAX_CONFLICT
        )

        result = TribunalResult(
            passed=passed,
            exec_score=exec_score,
            review_score=review_score,
            final_score=final_score,
            conflict=conflict,
            warnings=list(warnings),
        )

        # Step 6 — record the verification event (best-effort; do not fail
        # the verification if logging itself raises).
        if self.event_log is not None:
            self._record_event(change_name, criteria, result)

        return result

    def _judge(self, exec_score: float, review_score: float) -> Tuple[float, float]:
        """Compute ``(final_score, conflict)`` per the ADR-0008 formula.

        Conflict is the absolute disagreement between the two agents
        (``|exec − review|``), a leading indicator of one of them being
        wrong about the change.

        Args:
            exec_score: Raw score from the executor (0.0-1.0).
            review_score: Raw score from the reviewer (0.0-1.0).

        Returns:
            Tuple of ``(final_score, conflict)``.
        """
        final_score = exec_score * EXEC_WEIGHT + review_score * REVIEW_WEIGHT
        conflict = abs(exec_score - review_score)
        return final_score, conflict

    # ── Internals ───────────────────────────────────────────────────────

    def _invoke_agent(
        self,
        agent: Verifier,
        agent_label: str,
        change_name: str,
        criteria: str,
        sanitized_context: Dict[str, Any],
        warnings: List[str],
    ) -> float:
        """Invoke a verifier callable, catching any exception as graceful degradation.

        On exception the agent's score is set to 0.0 (a guaranteed fail) and
        a warning is appended. Returning 0.0 means the Tribunal's overall
        pass check will trip on the per-agent floor (PASS_MIN_AGENT_SCORE).
        """
        try:
            score = agent(change_name, criteria, sanitized_context)
        except Exception as exc:  # noqa: BLE001 — any failure must degrade gracefully
            warnings.append(
                f"{agent_label} agent invocation failed: {type(exc).__name__}: {exc}"
            )
            return 0.0
        # Clamp to [0.0, 1.0] so a misbehaving agent cannot tilt the math.
        try:
            score = float(score)
        except (TypeError, ValueError):
            warnings.append(f"{agent_label} returned a non-numeric score; using 0.0")
            return 0.0
        if score < 0.0:
            return 0.0
        if score > 1.0:
            return 1.0
        return score

    def _record_event(
        self,
        change_name: str,
        criteria: str,
        result: TribunalResult,
    ) -> None:
        """Record the verification result to ``self.event_log`` (best-effort).

        Uses ``LOOP_ITERATION_COMPLETED`` as the event type — verification
        is semantically a one-shot loop iteration. Callers distinguish
        verification events via the message ("Tribunal verification
        completed: …") and the ``change_name`` / ``passed`` context fields.
        """
        if self.event_log is None:
            return
        try:
            self.event_log.record(
                event_type=EventType.LOOP_ITERATION_COMPLETED,
                severity=Severity.INFO,
                message=(
                    f"Tribunal verification completed for {change_name}: "
                    f"passed={result.passed}, final_score={result.final_score:.3f}"
                ),
                context={
                    "change_name": change_name,
                    "criteria": criteria,
                    "passed": result.passed,
                    "final_score": result.final_score,
                    "exec_score": result.exec_score,
                    "review_score": result.review_score,
                    "conflict": result.conflict,
                },
                metadata={"warnings": list(result.warnings)},
            )
        except Exception:  # noqa: BLE001 — logging must never break verification
            # Swallow: a logging failure should not propagate as a
            # verification failure. The Tribunal's contract is to return
            # a result; the event log is observational.
            return

    @staticmethod
    def _default_sanitize(context: Dict[str, Any]) -> Dict[str, Any]:
        """Default context sanitizer: redact every string value via the project sanitizer.

        Non-string values (numbers, bools, lists, nested dicts) are passed
        through unchanged. This is intentionally shallow — the Tribunal
        receives only metadata about the change, not deeply nested
        user-supplied payloads. If a future caller needs deeper
        sanitization, they can inject their own ``ContextSanitizer``.
        """
        sanitized: Dict[str, Any] = {}
        for key, value in context.items():
            if isinstance(value, str):
                result = _default_sanitize(value)
                sanitized[key] = result.sanitized_text
            else:
                sanitized[key] = value
        return sanitized
