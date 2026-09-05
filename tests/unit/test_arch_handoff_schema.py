"""Tests for .arch-handoff.json JSON Schema (ADR-0016 Layer 2).

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
    / "_lib"
    / "schemas"
    / "arch_handoff_schema.json"
)


@pytest.fixture
def schema():
    assert SCHEMA_PATH.exists(), f"Schema file missing: {SCHEMA_PATH}"
    return json.loads(SCHEMA_PATH.read_text())


@pytest.fixture
def validator(schema):
    return Draft7Validator(schema)


def test_schema_contract_accepts_v1_and_v2(schema):
    """Schema must pin version 1 for ADR-0016 contract."""
    assert "enum" in schema["properties"]["version"] and schema["properties"]["version"]["enum"] == [1, 2, 3]


def test_valid_v1_payload_passes(validator):
    """Canonical payload with all v1 fields must validate (positive case)."""
    payload = {
        "arch_complete_at": "2026-07-08T10:00:00+00:00",
        "adr_count": 3,
        "completed_adr_ids": ["0001", "0002", "0003"],
        "roadmap_exists": True,
        "current_phase": "phase-1",
        "plan_started_at": None,
        # New v1 fields (ADR-0016 Layer 2):
        "adr_dir": "docs/adr",
        "roadmap_path": "roadmap.md",
        "architecture_dir": "docs/architecture",
        "adr_pattern": "ADR-*.md",
        "discovered": {
            "adr_dir": {"found": True, "created": False, "candidates_tried": 4},
            "roadmap_path": {"found": True, "created": False, "candidates_tried": 4},
            "architecture_dir": {"found": False, "created": False, "candidates_tried": 3},
        },
        "version": 1,
    }
    errors = list(validator.iter_errors(payload))
    assert errors == [], f"Expected no errors, got: {[e.message for e in errors]}"


def test_missing_new_field_fails(validator):
    """Pre-v1 payloads (missing adr_dir etc.) must be rejected at schema level."""
    payload_v0 = {
        "arch_complete_at": "2026-07-08T10:00:00+00:00",
        "adr_count": 1,
        "completed_adr_ids": ["0001"],
        "roadmap_exists": True,
        "current_phase": "default",
        "plan_started_at": None,
        "version": 0,  # legacy
        # Missing: adr_dir, roadmap_path, architecture_dir, adr_pattern, discovered
    }
    errors = list(validator.iter_errors(payload_v0))
    assert errors, "Expected rejection for missing v1 fields"
    paths = " ".join("/".join(str(x) for x in e.absolute_path) for e in errors)
    msgs = " ".join(e.message for e in errors)
    assert "adr_dir" in paths or "adr_dir" in msgs, (
        f"Expected adr_dir missing in errors: paths={paths[:200]}"
    )


def test_path_traversal_in_adr_dir_rejected(validator):
    """adr_dir with '..' must be rejected (security Momus HIGH#7)."""
    payload = {
        "arch_complete_at": "2026-07-08T10:00:00+00:00",
        "adr_count": 1,
        "completed_adr_ids": ["0001"],
        "roadmap_exists": True,
        "current_phase": "phase-1",
        "plan_started_at": None,
        "adr_dir": "../../etc/passwd",  # attack vector
        "roadmap_path": "roadmap.md",
        "architecture_dir": "docs/architecture",
        "adr_pattern": "ADR-*.md",
        "discovered": {
            "adr_dir": {"found": False, "created": False, "candidates_tried": 1},
            "roadmap_path": {"found": True, "created": False, "candidates_tried": 1},
            "architecture_dir": {"found": True, "created": False, "candidates_tried": 1},
        },
        "version": 1,
    }
    errors = list(validator.iter_errors(payload))
    assert errors, "Expected path-traversal rejection"


def test_absolute_path_in_adr_dir_rejected(validator):
    """adr_dir must be relative (worktree compatibility)."""
    payload = {
        "arch_complete_at": "2026-07-08T10:00:00+00:00",
        "adr_count": 1,
        "completed_adr_ids": ["0001"],
        "roadmap_exists": True,
        "current_phase": "phase-1",
        "plan_started_at": None,
        "adr_dir": "/etc/passwd",  # absolute
        "roadmap_path": "roadmap.md",
        "architecture_dir": "docs/architecture",
        "adr_pattern": "ADR-*.md",
        "discovered": {
            "adr_dir": {"found": True, "created": False, "candidates_tried": 1},
            "roadmap_path": {"found": True, "created": False, "candidates_tried": 1},
            "architecture_dir": {"found": True, "created": False, "candidates_tried": 1},
        },
        "version": 1,
    }
    errors = list(validator.iter_errors(payload))
    assert errors, "Expected absolute-path rejection"


def test_extra_fields_allowed_at_root(validator):
    """Schema must permit additionalProperties=true at root (forward compat)."""
    payload = {
        "arch_complete_at": "2026-07-08T10:00:00+00:00",
        "adr_count": 1,
        "completed_adr_ids": ["0001"],
        "roadmap_exists": True,
        "current_phase": "phase-1",
        "plan_started_at": None,
        "adr_dir": "docs/adr",
        "roadmap_path": "roadmap.md",
        "architecture_dir": "docs/architecture",
        "adr_pattern": "ADR-*.md",
        "discovered": {
            "adr_dir": {"found": True, "created": False, "candidates_tried": 1},
            "roadmap_path": {"found": True, "created": False, "candidates_tried": 1},
            "architecture_dir": {"found": True, "created": False, "candidates_tried": 1},
        },
        "version": 1,
        "future_field_xyz": "ignored",  # not in schema, must be allowed
    }
    errors = list(validator.iter_errors(payload))
    assert errors == [], f"Unexpected errors: {[e.message for e in errors]}"