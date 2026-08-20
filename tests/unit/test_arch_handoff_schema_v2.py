"""Tests for ADR-0016 arch_handoff schema v2 (additive roadmap_fragments_dir)."""
import json
import pytest
from jsonschema import Draft7Validator


SCHEMA_PATH = "skills/_lib/schemas/arch_handoff_schema.json"


def _full_v1_payload() -> dict:
    """Return a complete v1 payload (all required fields present)."""
    return {
        "version": 1,
        "arch_complete_at": "2026-01-01T00:00:00",
        "adr_count": 0,
        "completed_adr_ids": [],
        "roadmap_exists": False,
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
    }


@pytest.fixture
def schema():
    with open(SCHEMA_PATH) as f:
        return json.load(f)


def test_schema_metadata_stays_v1_invariant(schema):
    """Project invariant: all rdd-workflow schemas keep version.const='v1' (schema system version).
    Contract version is a separate field (properties.version.enum) and may evolve.
    """
    assert schema.get("version", {}).get("const") == "v1", (
        f"Project invariant: schema version.const must stay 'v1', got {schema.get('version')!r}. "
        "If you intend to bump the contract version, modify properties.version.enum instead."
    )


def test_contract_version_accepts_v1_and_v2(schema):
    """Contract payload version enum must accept both 1 (v1 payload) and 2 (v2 payload) for backward compat."""
    enum = schema["properties"]["version"].get("enum")
    assert enum == [1, 2], f"Expected contract enum=[1, 2], got {enum!r}"


def test_v1_payload_still_accepted(schema):
    """v1 payload (version=1, no roadmap_fragments_dir) validates (backward compat via additionalProperties: true)."""
    v1 = _full_v1_payload()
    assert "roadmap_fragments_dir" not in v1, "v1 payload fixture leaked fragments_dir"
    errors = list(Draft7Validator(schema).iter_errors(v1))
    assert errors == [], f"v1 must validate, got errors: {[e.message for e in errors]}"


def test_v2_payload_with_fragments_dir_accepted(schema):
    """v2 payload (version=2 + new roadmap_fragments_dir field) validates."""
    v2 = _full_v1_payload()
    v2["version"] = 2
    v2["roadmap_path"] = ".rddf/roadmap.md"
    v2["roadmap_fragments_dir"] = ".rddf/roadmap"
    errors = list(Draft7Validator(schema).iter_errors(v2))
    assert errors == [], f"v2 must validate, got errors: {[e.message for e in errors]}"


def test_roadmap_fragments_dir_field_defined(schema):
    """New roadmap_fragments_dir field must be in properties with type=string and default."""
    prop = schema["properties"].get("roadmap_fragments_dir")
    assert prop is not None, "roadmap_fragments_dir missing from properties"
    assert prop.get("type") == "string"
    assert prop.get("default") == ".rddf/roadmap"


def test_roadmap_fragments_dir_not_required(schema):
    """Additive field MUST NOT be required (backward compat for v1 payloads)."""
    assert "roadmap_fragments_dir" not in schema.get("required", []), (
        "roadmap_fragments_dir must be additive (not required) for v1 backward compat"
    )
