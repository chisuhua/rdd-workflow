"""Tests for the rdd-verifier v2.0 LLM Verification Protocol data layer.

Per ADR-0045 (inline-ac-verifier-into-rdd-verifier) Task 11:
- AC extraction regex (3 bullet formats + edge cases)
- Verdict JSON schema validation
- Reasoning-keyword contract (drift/gap)
- Cache file v2 write/read
- Audit log JSONL append semantics
- Agent context staging
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _lib.verifier.protocol import (
    DRIFT_KEYWORDS,
    GAP_KEYWORDS,
    VERDICT_SCHEMA,
    build_verification_context,
    parse_acs,
    stage_verification_context,
    validate_verdict_completeness,
    validate_verdict_items,
)
from _lib.verifier.cache import read_verdict_cache, verdict_cache, is_cache_fresh
from _lib.verifier.classify import classify_failure
from _lib.verifier.audit import read_events, write_event


def _write_proposal(tmp_path: Path, body: str) -> Path:
    d = tmp_path / "openspec" / "changes" / "ch-p"
    d.mkdir(parents=True, exist_ok=True)
    p = d / "proposal.md"
    p.write_text(body, encoding="utf-8")
    return p


# ============================================================================
# AC extraction (3 bullet formats + edge cases)
# ============================================================================


def test_parse_acs_plain_bullet(tmp_path):
    p = _write_proposal(tmp_path, "## 验收标准\n- AC one\n- AC two\n")
    acs = parse_acs(p)
    assert [a["ac_id"] for a in acs] == ["AC-1", "AC-2"]
    assert all(not a["has_checkbox"] for a in acs)


def test_parse_acs_unchecked_checkbox_bullet(tmp_path):
    p = _write_proposal(tmp_path, "## 验收标准\n- [ ] AC one\n")
    acs = parse_acs(p)
    assert acs[0]["has_checkbox"] is True
    assert acs[0]["description"] == "AC one"


def test_parse_acs_checked_checkbox_bullet(tmp_path):
    p = _write_proposal(tmp_path, "## 验收标准\n- [x] AC one\n")
    acs = parse_acs(p)
    assert acs[0]["has_checkbox"] is True


def test_parse_acs_english_header(tmp_path):
    p = _write_proposal(tmp_path, "## Acceptance Criteria\n- AC one\n")
    assert len(parse_acs(p)) == 1


def test_parse_acs_section_ends_at_next_header(tmp_path):
    p = _write_proposal(tmp_path, "## 验收标准\n- AC one\n## Capabilities\n- not an AC\n")
    acs = parse_acs(p)
    assert [a["description"] for a in acs] == ["AC one"]


def test_parse_acs_missing_section_returns_empty(tmp_path):
    p = _write_proposal(tmp_path, "# Proposal\nNo ACs here.\n")
    assert parse_acs(p) == []


def test_parse_acs_missing_file_returns_empty(tmp_path):
    assert parse_acs(tmp_path / "nope.md") == []


# ============================================================================
# Verdict schema validation
# ============================================================================


def test_validate_verdict_items_accepts_valid():
    # verifier-v2-hardening Phase 2: pass requires evidence ≥1 + reasoning ≥1.
    items = [{"ac_id": "AC-1", "status": "pass", "confidence": 0.9,
              "evidence": [{"tool": "Grep", "query": "x", "result_summary": "y"}],
              "reasoning": "Handler found in api.py"}]
    valid, problems = validate_verdict_items(items)
    assert problems == []
    assert len(valid) == 1


def test_validate_verdict_items_flags_invalid_status():
    items = [{"ac_id": "AC-1", "status": "uncertain", "confidence": 0.5,
              "evidence": [{"tool": "Grep", "query": "x", "result_summary": "y"}],
              "reasoning": "test"}]
    valid, problems = validate_verdict_items(items)
    assert len(problems) == 1
    assert "AC-1" in problems[0]


def test_validate_verdict_items_flags_bad_ac_id():
    items = [{"ac_id": "ac1", "status": "pass", "confidence": 0.5,
              "evidence": [{"tool": "Grep", "query": "x", "result_summary": "y"}],
              "reasoning": "test"}]
    _, problems = validate_verdict_items(items)
    assert len(problems) == 1
    assert "ac1" in problems[0]


def test_validate_verdict_items_pass_requires_evidence():
    items = [{"ac_id": "AC-1", "status": "pass", "confidence": 0.9,
              "evidence": [], "reasoning": "ok"}]
    _, problems = validate_verdict_items(items)
    assert any("evidence empty" in p for p in problems)


def test_validate_verdict_items_fail_requires_keyword():
    items = [{"ac_id": "AC-1", "status": "fail", "confidence": 0.9,
              "evidence": [{"tool": "Grep", "query": "x", "result_summary": "y"}],
              "reasoning": "Handler is broken"}]
    _, problems = validate_verdict_items(items)
    assert any("drift/gap keyword" in p for p in problems)


def test_validate_verdict_items_partial_requires_evidence_and_keyword():
    items = [{"ac_id": "AC-1", "status": "partial", "confidence": 0.9,
              "evidence": [], "reasoning": "almost works"}]
    _, problems = validate_verdict_items(items)
    assert any("evidence empty" in p for p in problems)
    assert any("drift/gap keyword" in p for p in problems)


def test_validate_verdict_items_fail_with_drift_keyword_ok():
    items = [{"ac_id": "AC-1", "status": "fail", "confidence": 0.9,
              "evidence": [{"tool": "Read", "query": "x", "result_summary": "y"}],
              "reasoning": "Code exists but does not match AC"}]
    _, problems = validate_verdict_items(items)
    assert problems == []


def test_validate_verdict_items_required_fields_missing():
    items = [{"ac_id": "AC-1", "status": "pass"}]  # no confidence, reasoning, no evidence
    _, problems = validate_verdict_items(items)
    assert len(problems) >= 2


def test_validate_verdict_items_non_array():
    valid, problems = validate_verdict_items({"not": "an array"})
    assert valid == []
    assert problems == ["verdict: not a JSON array"]


def test_verdict_schema_requires_core_fields():
    # verifier-v2-hardening Phase 2: reasoning now required (was optional).
    required = set(VERDICT_SCHEMA["items"]["required"])
    assert required == {"ac_id", "status", "confidence", "reasoning"}
    # evidence must have minItems=1
    assert VERDICT_SCHEMA["items"]["properties"]["evidence"]["minItems"] == 1
    assert VERDICT_SCHEMA["items"]["properties"]["reasoning"]["minLength"] == 1


# ============================================================================
# Reasoning-keyword contract (drift/gap) + classify interop
# ============================================================================


def test_drift_keyword_routes_proposal_drift():
    item = {"reasoning": "Code exists but does not match AC", "evidence": []}
    assert classify_failure(item) == "proposal_drift"


def test_gap_keyword_routes_implementation_gap():
    item = {"reasoning": "Method is missing from implementation", "evidence": []}
    assert classify_failure(item) == "implementation_gap"


def test_drift_keywords_take_priority_over_gap():
    item = {"reasoning": "Implementation missing; exists but mismatches AC", "evidence": []}
    assert classify_failure(item) == "proposal_drift"


def test_protocol_exports_keywords_matching_classifier():
    from _lib.verifier.classify import _DRIFT_KEYWORDS, _GAP_KEYWORDS
    assert tuple(DRIFT_KEYWORDS) == tuple(_DRIFT_KEYWORDS)
    assert tuple(GAP_KEYWORDS) == tuple(_GAP_KEYWORDS)


# ============================================================================
# Cache v2 write/read
# ============================================================================


def test_verdict_cache_roundtrip_v2(tmp_path):
    verdict_cache(tmp_path, "ch-x", "sha123",
                  [{"ac_id": "AC-1", "status": "pass"}],
                  ran_by="rdd-verifier",
                  verification_state="passed", failed_acs=[])
    cached = read_verdict_cache(tmp_path, "ch-x")
    assert cached["schema_version"] == 2
    assert cached["codebase_commit"] == "sha123"
    assert cached["ran_by"] == "rdd-verifier"


def test_cache_freshness_matches_commit(tmp_path):
    verdict_cache(tmp_path, "ch-x", "shaA", [], ran_by="rdd-verifier")
    assert is_cache_fresh(tmp_path, "ch-x", "shaA")
    assert not is_cache_fresh(tmp_path, "ch-x", "shaB")


def test_cache_read_corrupt_returns_none(tmp_path):
    (tmp_path / ".rddf" / "state").mkdir(parents=True)
    (tmp_path / ".rddf" / "state" / ".ac-verdict-ch-x.json").write_text("{broken")
    assert read_verdict_cache(tmp_path, "ch-x") is None


def test_read_verdict_cache_v1_returns_none(tmp_path):
    """verifier-v2-hardening Phase 5 (oracle risk #5): v1 cache fail-closed."""
    (tmp_path / ".rddf" / "state").mkdir(parents=True)
    (tmp_path / ".rddf" / "state" / ".ac-verdict-ch-x.json").write_text(
        json.dumps({"version": 1, "change": "ch-x", "codebase_commit": "abc",
                    "verdict": []})
    )
    assert read_verdict_cache(tmp_path, "ch-x") is None


def test_read_verdict_cache_unknown_version_returns_none(tmp_path):
    (tmp_path / ".rddf" / "state").mkdir(parents=True)
    (tmp_path / ".rddf" / "state" / ".ac-verdict-ch-x.json").write_text(
        json.dumps({"schema_version": 99, "change": "ch-x", "codebase_commit": "abc"})
    )
    assert read_verdict_cache(tmp_path, "ch-x") is None


def test_read_verdict_cache_missing_version_returns_none(tmp_path):
    (tmp_path / ".rddf" / "state").mkdir(parents=True)
    (tmp_path / ".rddf" / "state" / ".ac-verdict-ch-x.json").write_text(
        json.dumps({"change": "ch-x", "codebase_commit": "abc"})
    )
    assert read_verdict_cache(tmp_path, "ch-x") is None


# ============================================================================
# Audit log JSONL append semantics
# ============================================================================


def test_audit_events_append_in_order(tmp_path):
    write_event(tmp_path, "ch-x", "running", commit="a")
    write_event(tmp_path, "ch-x", "pending", commit="a", route="pending-agent")
    write_event(tmp_path, "ch-x", "archive-ready", commit="b")
    events = read_events(tmp_path, "ch-x")
    assert [e["event"] for e in events] == ["running", "pending", "archive-ready"]


def test_audit_pending_event_is_valid():
    from _lib.verifier.audit import VALID_EVENTS
    assert "pending" in VALID_EVENTS


def test_audit_invalid_event_raises(tmp_path):
    with pytest.raises(ValueError):
        write_event(tmp_path, "ch-x", "bogus-event")


# ============================================================================
# Agent context staging (build + stage)
# ============================================================================


def test_build_verification_context_shape(tmp_path):
    _write_proposal(tmp_path, "## 验收标准\n- [x] AC one\n- AC two\n")
    doc = build_verification_context("ch-p", tmp_path, codebase_commit="deadbeef")
    assert doc["ac_count"] == 2
    assert doc["codebase_commit"] == "deadbeef"
    assert doc["cache_path"].endswith(".ac-verdict-ch-p.json")
    assert doc["audit_log_path"].endswith(".ac-verification.jsonl")
    assert "LLM Verification Protocol" in doc["instruction"]
    assert doc["reasoning_keywords"]["drift"] == list(DRIFT_KEYWORDS)
    assert doc["expected_verdict_schema"] == VERDICT_SCHEMA


def test_build_verification_context_missing_proposal_returns_none(tmp_path):
    assert build_verification_context("ghost", tmp_path) is None


def test_stage_verification_context_writes_file(tmp_path):
    _write_proposal(tmp_path, "## 验收标准\n- AC one\n")
    out = stage_verification_context("ch-p", tmp_path)
    assert out is not None and out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["change"] == "ch-p"
    assert out.name == "rdd-verify-context-ch-p.json"


def test_stage_verification_context_atomic_no_tmp_leftover(tmp_path):
    """verifier-v2-hardening Phase 5 (oracle risk #5): temp + rename atomicity."""
    _write_proposal(tmp_path, "## 验收标准\n- AC one\n")
    stage_verification_context("ch-p", tmp_path)
    # The .tmp sibling must NOT exist (atomic replace ate it).
    leftover = tmp_path / ".rddf" / "state" / "rdd-verify-context-ch-p.json.tmp"
    assert not leftover.exists()


def test_zero_ac_context_pass_through(tmp_path):
    """verifier-v2-hardening Phase 6 (oracle Q2 #5): AC section but no bullets."""
    body = "## 验收标准\n\n(no bullets here)\n"
    p = _write_proposal(tmp_path, body)
    result = parse_acs(p)
    assert result == []
    assert build_verification_context("ch-p", tmp_path)["ac_count"] == 0


# ============================================================================
# verifier-v2-hardening Phase 6 (oracle Q2): verdict completeness + staged→pending
# ============================================================================


def test_validate_verdict_completeness_length_mismatch():
    acs = [{"ac_id": "AC-1"}, {"ac_id": "AC-2"}, {"ac_id": "AC-3"}]
    verdict = [{"ac_id": "AC-1", "status": "pass", "confidence": 0.9,
                "evidence": [{"tool": "x", "query": "y", "result_summary": "z"}],
                "reasoning": "ok"}]
    _, problems = validate_verdict_completeness(verdict, acs)
    assert any("missing AC-2" in p for p in problems)
    assert any("missing AC-3" in p for p in problems)


def test_validate_verdict_completeness_unknown_ac_id():
    acs = [{"ac_id": "AC-1"}]
    verdict = [{"ac_id": "AC-9", "status": "pass", "confidence": 0.9,
                "evidence": [{"tool": "x", "query": "y", "result_summary": "z"}],
                "reasoning": "ok"}]
    _, problems = validate_verdict_completeness(verdict, acs)
    assert any("AC-9: unknown" in p for p in problems)
    assert any("missing AC-1" in p for p in problems)


def test_validate_verdict_completeness_duplicate_ac_id():
    acs = [{"ac_id": "AC-1"}, {"ac_id": "AC-2"}]
    verdict = [
        {"ac_id": "AC-1", "status": "pass", "confidence": 0.9,
         "evidence": [{"tool": "x", "query": "y", "result_summary": "z"}],
         "reasoning": "ok"},
        {"ac_id": "AC-1", "status": "pass", "confidence": 0.9,
         "evidence": [{"tool": "x", "query": "y", "result_summary": "z"}],
         "reasoning": "ok"},
    ]
    _, problems = validate_verdict_completeness(verdict, acs)
    assert any("duplicate" in p and "AC-1" in p for p in problems)


def test_validate_verdict_completeness_full_match_ok():
    acs = [{"ac_id": "AC-1"}, {"ac_id": "AC-2"}]
    verdict = [
        {"ac_id": "AC-1", "status": "pass", "confidence": 0.9,
         "evidence": [{"tool": "x", "query": "y", "result_summary": "z"}],
         "reasoning": "ok"},
        {"ac_id": "AC-2", "status": "pass", "confidence": 0.9,
         "evidence": [{"tool": "x", "query": "y", "result_summary": "z"}],
         "reasoning": "ok"},
    ]
    _, problems = validate_verdict_completeness(verdict, acs)
    assert problems == []
