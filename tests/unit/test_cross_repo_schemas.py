"""Unit tests for 6 cross-repo schemas (ADR-0030 + 7 related proposals).

Verifies ADR-0016 contract: each schema MUST have version (const:1) and $id.
"""
import json
import os
import subprocess
from pathlib import Path

import pytest
from jsonschema import Draft7Validator

SCHEMAS_DIR = Path(__file__).resolve().parent.parent.parent / "_lib" / "schemas"
DOCS_PATH = Path(__file__).resolve().parent.parent.parent / "docs" / "schemas" / "cross-repo-schemas.md"

SCHEMA_NAMES = [
    "cross_repo_pending_schema.json",
    "cross_repo_audit_schema.json",
    "mcp_trace_schema.json",
    "contract_cache_schema.json",
    "cross_repo_deps_cache_schema.json",
    "hub_metrics_schema.json",
]


@pytest.mark.parametrize("schema_name", SCHEMA_NAMES)
def test_schema_has_version_const_1(schema_name):
    """Each schema MUST pin version: 1 per ADR-0016 contract."""
    schema = json.loads((SCHEMAS_DIR / schema_name).read_text())
    assert "version" in schema["properties"], f"{schema_name} missing version property"
    assert schema["properties"]["version"]["const"] == 1
    assert "version" in schema["required"], f"{schema_name} missing version in required"


def test_all_schemas_have_unique_id():
    """Each schema MUST have unique $id (per ADR-0016 contract)."""
    ids = []
    for schema_name in SCHEMA_NAMES:
        schema = json.loads((SCHEMAS_DIR / schema_name).read_text())
        sid = schema.get("$id")
        assert sid is not None, f"{schema_name} missing $id"
        ids.append(sid)
    assert len(ids) == len(set(ids)), f"Duplicate $id: {ids}"


@pytest.mark.parametrize("schema_name", SCHEMA_NAMES)
def test_schema_uses_draft7(schema_name):
    """Each schema MUST use JSON Schema Draft-7 (project standard)."""
    schema = json.loads((SCHEMAS_DIR / schema_name).read_text())
    assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"


VALID_PAYLOADS = {
    "cross_repo_pending_schema.json": {
        "version": 1,
        "pending_issues": [],
        "last_updated": "2026-08-15T16:00:00Z",
    },
    "cross_repo_audit_schema.json": {
        "version": 1,
        "timestamp": "2026-08-15T16:00:00Z",
        "proposal_name": "my-proposal",
        "hub_issue": "org/rdd-hub#7",
        "decision": "initiate",
        "actor": {"type": "ai-agent", "id": "agent-x"},
    },
    "mcp_trace_schema.json": {
        "version": 1,
        "timestamp": "2026-08-15T16:00:00Z",
        "direction": "spoke-to-hub",
        "tool_name": "hub_create_issue",
        "actor_repo": "org/repo-frontend",
        "args_hash": "a" * 64,
        "result_status": "success",
    },
    "contract_cache_schema.json": {
        "version": 1,
        "last_sync": "2026-08-15T16:00:00Z",
        "contracts": [],
    },
    "cross_repo_deps_cache_schema.json": {
        "version": 1,
        "cache_generated_at": "2026-08-15T16:00:00Z",
        "spokes": [],
        "dependency_graph": {"nodes": [], "edges": []},
    },
    "hub_metrics_schema.json": {
        "version": 1,
        "last_updated": "2026-08-15T16:00:00Z",
        "spokes_connected": 5,
        "rfc_stats": {
            "total": 0,
            "by_status": {},
            "avg_decision_days": None,
        },
    },
}


@pytest.mark.parametrize("schema_name,payload", list(VALID_PAYLOADS.items()))
def test_valid_payload_passes(schema_name, payload):
    schema = json.loads((SCHEMAS_DIR / schema_name).read_text())
    validator = Draft7Validator(schema)
    errors = list(validator.iter_errors(payload))
    assert not errors, f"Valid payload failed for {schema_name}: {[e.message for e in errors]}"


@pytest.mark.parametrize("schema_name", SCHEMA_NAMES)
def test_invalid_field_value_fails(schema_name):
    """Wrong-type field value must fail validation."""
    schema = json.loads((SCHEMAS_DIR / schema_name).read_text())
    validator = Draft7Validator(schema)
    # Change version to string (should fail)
    payload = dict(VALID_PAYLOADS[schema_name])
    payload["version"] = "not-an-int"
    errors = list(validator.iter_errors(payload))
    assert errors, f"{schema_name} should fail with wrong version type"


@pytest.mark.parametrize("schema_name", SCHEMA_NAMES)
def test_missing_required_field_fails(schema_name):
    """Removing required version must fail validation."""
    schema = json.loads((SCHEMAS_DIR / schema_name).read_text())
    validator = Draft7Validator(schema)
    payload = dict(VALID_PAYLOADS[schema_name])
    del payload["version"]
    errors = list(validator.iter_errors(payload))
    assert errors, f"{schema_name} should fail without version"
    assert any("version" in e.message for e in errors)


def test_docs_file_exists():
    assert DOCS_PATH.exists(), f"Missing docs file: {DOCS_PATH}"


@pytest.mark.parametrize("schema_name", SCHEMA_NAMES)
def test_docs_mentions_each_schema(schema_name):
    content = DOCS_PATH.read_text()
    assert schema_name in content, f"docs missing reference to {schema_name}"


def test_openspec_validate_any_active_change():
    """openspec validate must accept at least one active change in openspec/changes/.

    Originally hardcoded to add-cross-repo-state-schemas, but that change was
    archived (W2-2). This generalized version validates that ANY currently
    active change in the repo passes openspec validate.
    """
    import os
    changes_dir = Path(__file__).resolve().parent.parent.parent / "openspec" / "changes"
    if not changes_dir.exists():
        pytest.skip("openspec/changes/ not present")

    active_changes = [
        d.name for d in changes_dir.iterdir()
        if d.is_dir() and not d.name.startswith("archive")
    ]
    if not active_changes:
        pytest.skip("No active changes in openspec/changes/")

    candidate = None
    for name in active_changes:
        if (changes_dir / name / "specs").is_dir():
            candidate = name
            break
    if candidate is None:
        pytest.skip(
            f"No active change has specs/ directory; "
            f"skipped validate (active={active_changes})"
        )

    result = subprocess.run(
        ["openspec", "validate", candidate],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parent.parent.parent,
    )
    assert result.returncode == 0, f"openspec validate {candidate} failed: {result.stderr}"
