"""Tests for .design-handoff.json JSON Schema (v1).

These tests lock the schema contract before any consumer reads from it.
Red phase: schema file is missing → all tests fail with FileNotFoundError.
Green phase: schema file present and correct → all tests pass.
"""
import json
import pytest
from pathlib import Path
from jsonschema import Draft7Validator

SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "skills"
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


def test_schema_declares_version_1(schema):
    """Schema must pin version 1 for design-handoff contract."""
    assert schema["properties"]["version"]["const"] == 1


def test_valid_v1_payload_passes(validator):
    """Canonical payload with all v1 fields must validate (positive case)."""
    payload = {
        "design_complete_at": "2026-07-30T10:00:00+00:00",
        "proposals_reviewed": 3,
        "all_proposals_have_decision": True,
        "version": 1,
    }
    errors = list(validator.iter_errors(payload))
    assert errors == [], f"Expected no errors, got: {[e.message for e in errors]}"


def test_missing_required_field_fails(validator):
    """Each required field missing must produce a validation error."""
    full = {
        "design_complete_at": "2026-07-30T10:00:00+00:00",
        "proposals_reviewed": 3,
        "all_proposals_have_decision": True,
        "version": 1,
    }
    for required_field in ["design_complete_at", "proposals_reviewed",
                           "all_proposals_have_decision", "version"]:
        payload = {k: v for k, v in full.items() if k != required_field}
        errors = list(validator.iter_errors(payload))
        assert len(errors) >= 1, f"Expected error for missing field: {required_field}"


def test_extra_fields_rejected(validator):
    """additionalProperties: false must reject unknown fields."""
    payload = {
        "design_complete_at": "2026-07-30T10:00:00+00:00",
        "proposals_reviewed": 3,
        "all_proposals_have_decision": True,
        "version": 1,
        "extra_field": "should_not_be_allowed",
    }
    errors = list(validator.iter_errors(payload))
    assert len(errors) >= 1, "Expected error for extra field"


def test_proposals_reviewed_non_negative(validator):
    """proposals_reviewed must be >= 0."""
    payload = {
        "design_complete_at": "2026-07-30T10:00:00+00:00",
        "proposals_reviewed": -1,
        "all_proposals_have_decision": True,
        "version": 1,
    }
    errors = list(validator.iter_errors(payload))
    assert len(errors) >= 1, "Expected error for negative proposals_reviewed"


def test_proposals_reviewed_zero_is_valid(validator):
    """Edge case: 0 proposals reviewed should pass (e.g., skip all)."""
    payload = {
        "design_complete_at": "2026-07-30T10:00:00+00:00",
        "proposals_reviewed": 0,
        "all_proposals_have_decision": True,
        "version": 1,
    }
    errors = list(validator.iter_errors(payload))
    assert errors == [], f"Expected no errors for 0 proposals, got: {[e.message for e in errors]}"


def test_version_not_1_rejected(validator):
    """version must be exactly 1."""
    payload = {
        "design_complete_at": "2026-07-30T10:00:00+00:00",
        "proposals_reviewed": 3,
        "all_proposals_have_decision": True,
        "version": 2,
    }
    errors = list(validator.iter_errors(payload))
    assert len(errors) >= 1, "Expected error for version != 1"