"""Tests for .ac-verdict-<name>.json schema v1.

Per ADR-0034 §7.2 + Oracle §C: SHA-fingerprint verdict cache to avoid
double LLM calls between rdd-verifier and archive_gate_check.
"""
import json
from pathlib import Path

import jsonschema
import pytest

SCHEMA = json.loads(
    Path("_lib/schemas/ac_verdict_cache_schema.json").read_text(encoding="utf-8")
)


def test_schema_loads():
    assert SCHEMA["version"] == 1


def test_valid_doc():
    doc = {
        "version": 1,
        "change": "test-change",
        "codebase_commit": "abc1234567",
        "verdict": [
            {"ac_id": "AC-1", "status": "pass", "confidence": 0.95,
             "evidence": ["file:tests/test_foo.py:10"], "reasoning": "All good"}
        ],
        "ran_at": "2026-08-26T00:00:00Z",
        "ran_by": "rdd-verifier",
    }
    jsonschema.validate(doc, SCHEMA)


def test_valid_multi_ac_verdict():
    doc = {
        "version": 1,
        "change": "test-change",
        "codebase_commit": "abc1234567",
        "verdict": [
            {"ac_id": "AC-1", "status": "pass", "confidence": 0.9,
             "evidence": [], "reasoning": "ok"},
            {"ac_id": "AC-2", "status": "fail", "confidence": 0.7,
             "evidence": ["file:src/foo.py:50"], "reasoning": "mismatch"},
        ],
        "ran_at": "2026-08-26T00:00:00Z",
        "ran_by": "archive_gate_check",
    }
    jsonschema.validate(doc, SCHEMA)


def test_invalid_status():
    doc = {
        "version": 1, "change": "x", "codebase_commit": "abc1234",
        "verdict": [{"ac_id": "AC-1", "status": "unknown", "confidence": 0.5,
                     "evidence": [], "reasoning": ""}],
        "ran_at": "x", "ran_by": "rdd-verifier",
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(doc, SCHEMA)


def test_invalid_ran_by():
    doc = {
        "version": 1, "change": "x", "codebase_commit": "abc1234",
        "verdict": [], "ran_at": "x", "ran_by": "INVALID",
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(doc, SCHEMA)


def test_invalid_ac_id_pattern():
    doc = {
        "version": 1, "change": "x", "codebase_commit": "abc1234",
        "verdict": [{"ac_id": "BAD-ID", "status": "pass", "confidence": 0.5,
                     "evidence": [], "reasoning": ""}],
        "ran_at": "x", "ran_by": "rdd-verifier",
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(doc, SCHEMA)


def test_invalid_confidence_out_of_range():
    doc = {
        "version": 1, "change": "x", "codebase_commit": "abc1234",
        "verdict": [{"ac_id": "AC-1", "status": "pass", "confidence": 1.5,
                     "evidence": [], "reasoning": ""}],
        "ran_at": "x", "ran_by": "rdd-verifier",
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(doc, SCHEMA)