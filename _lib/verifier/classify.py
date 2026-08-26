"""Heuristic failure classification for rdd-verifier.

Per ADR-0034 §5.1 + Oracle review §E: classify AC failures without new LLM calls.
Reuses ac-verifier verdict JSON evidence + reasoning fields.

Pure function — no I/O, no globals. Easily unit-testable with mock verdicts.
"""
from __future__ import annotations

# Keywords are matched case-insensitively.
# Order matters: drift check first because it implies documentation-level fix
# (cheaper than code rewrite) — conservative default per Oracle §E.
_DRIFT_KEYWORDS = ("exists but", "discrepan", "mismatch", "differs from ac")
_GAP_KEYWORDS = ("not implement", "missing", "absent", "todo: implement")


def classify_failure(verdict_item: dict) -> str:
    """Classify a single AC verdict as `implementation_gap` or `proposal_drift`.

    Args:
        verdict_item: dict with at least `reasoning` (str) and `evidence` (list) keys.
                      Matches the shape produced by ac-verifier skill.

    Returns:
        One of `implementation_gap` or `proposal_drift`.

    Notes:
        - Conservative default (ambiguous → `implementation_gap`) because
          guide-ship re-run cost < guide-plan proposal rewrite cost.
        - Pure function. No I/O, no LLM.
    """
    reasoning = (verdict_item.get("reasoning") or "").lower()

    for kw in _DRIFT_KEYWORDS:
        if kw in reasoning:
            return "proposal_drift"

    for kw in _GAP_KEYWORDS:
        if kw in reasoning:
            return "implementation_gap"

    return "implementation_gap"