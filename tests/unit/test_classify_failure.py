"""Tests for heuristic failure classifier.

Per ADR-0034 §5.1 + Oracle §E: pure function, no LLM call.
Reuses ac-verifier verdict JSON evidence + reasoning fields.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _lib.verifier.classify import classify_failure


def test_implementation_gap_keywords():
    for kw in ["not implemented", "missing", "absent", "TODO: implement"]:
        assert classify_failure({"reasoning": f"Function is {kw}",
                                  "evidence": []}) == "implementation_gap"


def test_proposal_drift_keywords():
    for kw in ["exists but", "discrepan", "mismatch", "differs from ac"]:
        assert classify_failure({"reasoning": f"Code {kw} the spec",
                                  "evidence": []}) == "proposal_drift"


def test_ambiguous_fallback_to_implementation_gap():
    """Oracle §E: conservative default = implementation_gap
    (回 guide-ship 代价低于回 guide-plan 重写 proposal).
    """
    assert classify_failure({"reasoning": "Unclear", "evidence": []}) == "implementation_gap"
    assert classify_failure({"reasoning": "", "evidence": []}) == "implementation_gap"
    assert classify_failure({}) == "implementation_gap"


def test_case_insensitive_matching():
    assert classify_failure({"reasoning": "MISSING function",
                              "evidence": []}) == "implementation_gap"
    assert classify_failure({"reasoning": "Code EXISTS BUT with bugs",
                              "evidence": []}) == "proposal_drift"


def test_priority_proposal_drift_over_gap():
    """When both signals present, prefer proposal_drift
    (more conservative to fix docs than code)."""
    assert classify_failure({"reasoning": "missing implementation, exists but mismatched",
                              "evidence": []}) == "proposal_drift"


def test_return_type_is_string():
    """Defensive: ensure return type contract is honored."""
    result = classify_failure({"reasoning": "missing", "evidence": []})
    assert isinstance(result, str)
    assert result in ("implementation_gap", "proposal_drift")