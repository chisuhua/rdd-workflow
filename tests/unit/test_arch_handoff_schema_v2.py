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


# ============================================================================
# M4 Task 4.5 (complete-project-yaml-config-gaps): adr_regex field for Python regex passthrough
# ============================================================================


def test_v2_includes_adr_regex_field(schema):
    """arch_handoff_schema v2 includes optional 'adr_regex' field for Python regex.

    Per complete-project-yaml-config-gaps M4 Task 4.5: write_arch_handoff reads
    .rddf/project.yaml adr.pattern (Python regex) and writes to arch-handoff
    adr_regex field. populate_lib then reads this for scan_adr_catalog passthrough.
    """
    assert "adr_regex" in schema["properties"], (
        "arch_handoff_schema v2 must include 'adr_regex' field for Python regex passthrough"
    )
    field = schema["properties"]["adr_regex"]
    assert field["type"] == "string"
    # adr_regex is optional (backward compat with v1 payloads that don't have it)
    assert "default" not in field or field.get("default") is None


def test_v1_payload_without_adr_regex_still_valid(schema):
    """v1 payload (no adr_regex field) still validates under v2 schema (backward compat)."""
    v1 = _full_v1_payload()
    assert "adr_regex" not in v1, "v1 fixture should not include adr_regex"
    errors = list(Draft7Validator(schema).iter_errors(v1))
    assert errors == [], f"v1 (no adr_regex) must validate, got: {[e.message for e in errors]}"


def test_v2_payload_with_adr_regex_validates(schema):
    """v2 payload including adr_regex field validates."""
    v2 = _full_v1_payload()
    v2["version"] = 2
    v2["adr_regex"] = r"^ADR-(\d{3})-.*\.md$"
    errors = list(Draft7Validator(schema).iter_errors(v2))
    assert errors == [], f"v2 (with adr_regex) must validate, got: {[e.message for e in errors]}"


# ============================================================================
# M4 Task 4.2 (complete-project-yaml-config-gaps M4):
# roadmap_incremental_update passes adr_regex from arch-handoff to scan_adr_catalog
# ============================================================================


def test_resolve_adr_pattern_priority_chain(tmp_path):
    """Priority: explicit > arch-handoff > project.yaml > default.

    Per complete-project-yaml-config-gaps M4 Task 4.2: roadmap_incremental_update
    must read arch-handoff adr_regex and pass it through to scan_adr_catalog
    so 3-digit projects (ChipForge) work end-to-end.

    This test verifies the resolver logic that the caller
    (roadmap_incremental_update) will use.
    """
    import json
    import yaml
    from pathlib import Path
    from _lib.adr_catalog import _resolve_adr_pattern_for_caller
    # Setup arch-handoff with adr_regex (3-digit)
    state_dir = tmp_path / ".rddf" / "state"
    state_dir.mkdir(parents=True)
    arch_handoff = {
        "version": 2,
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
            "roadmap_path": {"found": False, "created": False, "candidates_tried": 0},
            "architecture_dir": {"found": False, "created": False, "candidates_tried": 0},
        },
        "adr_regex": r"^ADR-(\d{3})-.*\.md$",
    }
    (state_dir / ".arch-handoff.json").write_text(json.dumps(arch_handoff))

    # arch-handoff adr_regex wins over project.yaml
    project_dir = tmp_path / ".rddf"
    (project_dir / "project.yaml").write_text(
        yaml.dump({"adr": {"pattern": r"^ADR-(\d{4})-.*\.md$"}})
    )
    result = _resolve_adr_pattern_for_caller(tmp_path, explicit=None)
    assert result == r"^ADR-(\d{3})-.*\.md$", (
        f"arch-handoff adr_regex should win over project.yaml, got {result!r}"
    )

    # No arch-handoff → falls back to project.yaml
    (state_dir / ".arch-handoff.json").unlink()
    result = _resolve_adr_pattern_for_caller(tmp_path, explicit=None)
    assert result == r"^ADR-(\d{4})-.*\.md$", (
        f"No arch-handoff should fall back to project.yaml, got {result!r}"
    )

    # Explicit arg wins over all
    result = _resolve_adr_pattern_for_caller(
        tmp_path, explicit=r"^ADR-(\d{2})-.*\.md$"
    )
    assert result == r"^ADR-(\d{2})-.*\.md$", (
        f"Explicit arg should win, got {result!r}"
    )

    # No arch-handoff, no project.yaml, no explicit → None (caller falls back to default)
    (project_dir / "project.yaml").unlink()
    result = _resolve_adr_pattern_for_caller(tmp_path, explicit=None)
    assert result is None


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
