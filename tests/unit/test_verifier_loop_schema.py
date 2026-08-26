"""Tests for .verifier-loop.json schema v1.

Per ADR-0034 §4.2: state file structure for rdd-verifier loop tracking.
"""
import json
from pathlib import Path

import jsonschema
import pytest

SCHEMA = json.loads(
    Path("_lib/schemas/verifier_loop_schema.json").read_text(encoding="utf-8")
)


def test_schema_loads():
    assert SCHEMA["version"] == 1
    assert "properties" in SCHEMA


def test_valid_minimal_doc():
    doc = {
        "version": 1,
        "change": "test-change",
        "loop_count": 0,
        "max_loops": 3,
        "classification_history": [],
        "codebase_commit_at_last_run": "abc1234",
        "route": "archive-ready",
        "halt_reason": None,
        "updated_at": "2026-08-26T00:00:00Z",
    }
    jsonschema.validate(doc, SCHEMA)  # must not raise


def test_valid_classification_history():
    doc = {
        "version": 1,
        "change": "test-change",
        "loop_count": 2,
        "max_loops": 3,
        "classification_history": [
            {"loop": 1, "label": "implementation_gap", "user_confirmed": True,
             "at": "2026-08-26T01:00:00Z"},
            {"loop": 2, "label": "proposal_drift", "user_confirmed": False,
             "at": "2026-08-26T02:00:00Z"},
        ],
        "codebase_commit_at_last_run": "abc1234567",
        "route": "guide-plan",
        "halt_reason": None,
        "updated_at": "2026-08-26T02:00:00Z",
    }
    jsonschema.validate(doc, SCHEMA)


def test_invalid_loop_count_negative():
    doc = {
        "version": 1, "change": "x", "loop_count": -1, "max_loops": 3,
        "classification_history": [], "codebase_commit_at_last_run": "x",
        "route": "archive-ready", "halt_reason": None, "updated_at": "x",
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(doc, SCHEMA)


def test_invalid_route():
    doc = {
        "version": 1, "change": "x", "loop_count": 0, "max_loops": 3,
        "classification_history": [], "codebase_commit_at_last_run": "x",
        "route": "INVALID_ROUTE", "halt_reason": None, "updated_at": "x",
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(doc, SCHEMA)


def test_invalid_classification_label():
    doc = {
        "version": 1, "change": "x", "loop_count": 1, "max_loops": 3,
        "classification_history": [
            {"loop": 1, "label": "BAD_LABEL", "user_confirmed": True, "at": "x"}
        ],
        "codebase_commit_at_last_run": "x",
        "route": "archive-ready", "halt_reason": None, "updated_at": "x",
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(doc, SCHEMA)