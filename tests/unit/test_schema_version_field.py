"""Schema version field test (fix-schema-version-field, 17 schemas × 1).

Per ADR-0016 + fix-schema-version-field proposal AC:
- Every schema under skills/_lib/schemas/ must declare a top-level
  `"version"` field with `"const": "v1"`.
- Schema-level `version` is distinct from any `properties.version`
  business field (e.g. sessions_schema.json's properties.version).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

SCHEMA_DIR = Path(__file__).parent.parent.parent / "skills" / "_lib" / "schemas"
SCHEMAS = sorted(p.name for p in SCHEMA_DIR.glob("*.json"))
assert len(SCHEMAS) == 18, f"expected 18 schemas, found {len(SCHEMAS)}"


@pytest.mark.parametrize("schema_name", SCHEMAS)
def test_version_field_present(schema_name: str):
    schema_path = SCHEMA_DIR / schema_name
    data = json.loads(schema_path.read_text())
    assert "version" in data, f"{schema_name}: missing top-level 'version' field"
    assert isinstance(data["version"], dict), (
        f"{schema_name}: 'version' must be a JSON Schema object with const"
    )
    assert data["version"].get("const") == "v1", (
        f"{schema_name}: version.const must equal 'v1', got "
        f"{data['version'].get('const')!r}"
    )


def test_version_field_distinct_from_properties_version():
    """schemas with `properties.version` business field keep it; the
    top-level const version is a separate metadata field."""
    sessions = json.loads((SCHEMA_DIR / "sessions_schema.json").read_text())
    assert "version" in sessions
    assert sessions["version"].get("const") == "v1"
    assert "version" in sessions.get("properties", {}), (
        "sessions_schema.json should preserve its business properties.version"
    )


def test_version_field_positioned_after_schema():
    """version field should be inserted right after $schema per
    JSON Schema standard field ordering."""
    for name in SCHEMAS:
        path = SCHEMA_DIR / name
        data = json.loads(path.read_text())
        if "$schema" in data:
            keys = list(data.keys())
            assert keys.index("$schema") < keys.index("version"), (
                f"{name}: 'version' should appear after '$schema'"
            )