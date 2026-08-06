"""Tests for .design-handoff.json JSON Schema (v2).

These tests lock the schema contract before any consumer reads from it.
v2 adds `changes_pre_created: [name, ...]` so guide-plan intake can skip
already-created changes. v1 payloads are explicitly rejected (version const=2
+ new required field).
"""
import json
import pytest
from pathlib import Path
from jsonschema import Draft7Validator

SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "_lib"
    / "schemas"
    / "design_handoff_schema.json"
)


@pytest.fixture
def schema():
    assert SCHEMA_PATH.exists(), f"Schema file missing: {SCHEMA_PATH}"
    return json.loads(SCHEMA_PATH.read_text())


@pytest.fixture
def validator(schema):
    return Draft7Validator(schema)


def _v2_base():
    """Canonical v2 payload (success case)."""
    return {
        "design_complete_at": "2026-08-01T10:00:00+00:00",
        "proposals_reviewed": 3,
        "all_proposals_have_decision": True,
        "version": 2,
        "changes_pre_created": ["move-proposal-creation-to-design"],
    }


def test_schema_declares_version_2(schema):
    """Schema must pin version 2 for design-handoff contract (v1 is legacy)."""
    assert schema["properties"]["version"]["const"] == 2


def test_valid_v2_payload_passes(validator):
    """Canonical v2 payload with all fields must validate (positive case)."""
    errors = list(validator.iter_errors(_v2_base()))
    assert errors == [], f"Expected no errors, got: {[e.message for e in errors]}"


def test_valid_v2_payload_empty_changes_pre_created_passes(validator):
    """v2 with empty changes_pre_created array is valid (no design-created changes)."""
    payload = _v2_base()
    payload["changes_pre_created"] = []
    errors = list(validator.iter_errors(payload))
    assert errors == [], f"Expected no errors, got: {[e.message for e in errors]}"


def test_missing_required_field_fails(validator):
    """Each required field missing must produce a validation error."""
    full = _v2_base()
    for required_field in ["design_complete_at", "proposals_reviewed",
                           "all_proposals_have_decision", "version",
                           "changes_pre_created"]:
        payload = {k: v for k, v in full.items() if k != required_field}
        errors = list(validator.iter_errors(payload))
        assert len(errors) >= 1, f"Expected error for missing field: {required_field}"


def test_extra_fields_rejected(validator):
    """additionalProperties: false must reject unknown fields."""
    payload = _v2_base()
    payload["extra_field"] = "should_not_be_allowed"
    errors = list(validator.iter_errors(payload))
    assert len(errors) >= 1, "Expected error for extra field"


def test_proposals_reviewed_non_negative(validator):
    """proposals_reviewed must be >= 0."""
    payload = _v2_base()
    payload["proposals_reviewed"] = -1
    errors = list(validator.iter_errors(payload))
    assert len(errors) >= 1, "Expected error for negative proposals_reviewed"


def test_proposals_reviewed_zero_is_valid(validator):
    """Edge case: 0 proposals reviewed should pass (e.g., skip all)."""
    payload = _v2_base()
    payload["proposals_reviewed"] = 0
    errors = list(validator.iter_errors(payload))
    assert errors == [], f"Expected no errors for 0 proposals, got: {[e.message for e in errors]}"


def test_v2_rejects_unknown_field(validator):
    """v2 schema must keep additionalProperties: false even with changes_pre_created."""
    payload = _v2_base()
    payload["extra_unknown"] = "bad"
    errors = list(validator.iter_errors(payload))
    assert len(errors) >= 1, "Expected error for extra field in v2"


def test_valid_v1_payload_fails_on_v2_schema(validator):
    """v2 schema must reject v1 payloads (version const=2 + new required)."""
    payload = {
        "design_complete_at": "2026-07-30T10:00:00+00:00",
        "proposals_reviewed": 3,
        "all_proposals_have_decision": True,
        "version": 1,
    }
    errors = list(validator.iter_errors(payload))
    assert len(errors) >= 1, "v2 schema must reject v1 payload"


def test_v2_rejects_version_3(validator):
    """v2 schema constrains version to exactly 2 (forward compat is a separate bump)."""
    payload = _v2_base()
    payload["version"] = 3
    errors = list(validator.iter_errors(payload))
    assert len(errors) >= 1, "v2 schema must reject version=3"


def test_changes_pre_created_items_non_empty_strings(validator):
    """changes_pre_created items must be non-empty strings."""
    payload = _v2_base()
    payload["changes_pre_created"] = [""]  # empty string
    errors = list(validator.iter_errors(payload))
    assert len(errors) >= 1, "Expected error for empty string in changes_pre_created"


def test_changes_pre_created_items_must_be_strings(validator):
    """changes_pre_created items must be strings (not numbers, nulls, etc.)."""
    payload = _v2_base()
    payload["changes_pre_created"] = [123]  # int, not str
    errors = list(validator.iter_errors(payload))
    assert len(errors) >= 1, "Expected error for non-string item in changes_pre_created"