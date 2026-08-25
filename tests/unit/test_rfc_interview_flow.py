"""Unit tests for rfc_draft_schema.json (RFC draft template schema).

NOTE (cleanup-pre-existing-debt): design_done_gate.check_rfc_draft() was an
orphan gate (never wired into check_design_done_gate) and was deleted along
with its helpers. The schema itself is still used by rfc_interview.sh and
detect_cross_repo_impact.py, so its validation tests remain here.
"""
import json
from pathlib import Path

import pytest
import jsonschema


SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent / "skills" / "_lib" / "schemas" / "rfc_draft_schema.json"


def _valid_draft() -> dict:
    return {
        "version": "v1",
        "proposal_name": "auth-v2-redesign",
        "title": "[RFC] Redesign auth-v2 endpoints",
        "stakeholders": ["org/repo-a", "org/repo-b"],
        "gate": "Design-Gate",
        "contract_impact": "Breaking-Change",
        "created_at": "2026-08-19T10:00:00+00:00",
        "created_by": "test-user",
    }


# ---------------------------------------------------------------------------
# Schema validation tests
# ---------------------------------------------------------------------------

def test_schema_is_valid_json():
    schema = json.loads(SCHEMA_PATH.read_text())
    jsonschema.Draft7Validator.check_schema(schema)


def test_valid_draft_passes_schema():
    schema = json.loads(SCHEMA_PATH.read_text())
    jsonschema.validate(_valid_draft(), schema)


def test_missing_field_fails_schema():
    draft = _valid_draft()
    del draft["title"]
    schema = json.loads(SCHEMA_PATH.read_text())
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(draft, schema)


def test_wrong_version_fails_schema():
    draft = _valid_draft()
    draft["version"] = "v2"  # wrong schema version
    schema = json.loads(SCHEMA_PATH.read_text())
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(draft, schema)


def test_invalid_stakeholder_format_fails_schema():
    draft = _valid_draft()
    draft["stakeholders"] = ["not-org-repo", "valid-org/repo"]
    schema = json.loads(SCHEMA_PATH.read_text())
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(draft, schema)


def test_empty_stakeholders_fails_schema():
    draft = _valid_draft()
    draft["stakeholders"] = []
    schema = json.loads(SCHEMA_PATH.read_text())
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(draft, schema)


def test_invalid_gate_fails_schema():
    draft = _valid_draft()
    draft["gate"] = "Custom-Gate"
    schema = json.loads(SCHEMA_PATH.read_text())
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(draft, schema)


def test_invalid_impact_fails_schema():
    draft = _valid_draft()
    draft["contract_impact"] = "Maybe"
    schema = json.loads(SCHEMA_PATH.read_text())
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(draft, schema)


def test_optional_fields_omitted_passes():
    draft = _valid_draft()
    # contract_draft_path and hub_issue_url are optional
    schema = json.loads(SCHEMA_PATH.read_text())
    jsonschema.validate(draft, schema)  # should not raise