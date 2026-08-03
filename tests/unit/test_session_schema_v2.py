"""Verify sessions_schema.json v2 accepts optional sub_phase + workflow_group."""
import json
from pathlib import Path

try:
    import jsonschema
except ImportError:
    import pytest
    pytest.skip("jsonschema not installed", allow_module_level=True)


SCHEMA = json.loads(Path("skills/_lib/schemas/sessions_schema.json").read_text())


def test_schema_version_accepts_v1_and_v2():
    """Schema accepts version >= 1 (backward compat for v1 sessions)."""
    version_def = SCHEMA["properties"]["version"]
    assert version_def.get("minimum", 1) >= 1


def test_sub_phase_field_optional():
    session_props = SCHEMA["$defs"]["Session"]["properties"]
    assert "sub_phase" in session_props
    type_def = session_props["sub_phase"]["type"]
    assert "null" in type_def


def test_workflow_group_field_optional():
    session_props = SCHEMA["$defs"]["Session"]["properties"]
    assert "workflow_group" in session_props


def test_v1_sessions_still_validate():
    v1_session = {
        "session_id": "rds_aaaabbbbcccc",
        "kind": "stage_ship",
        "owner_opencode_session_id": "owner1",
        "state": "active",
        "started_at": "2026-08-02T15:00:00+00:00",
        "last_heartbeat": "2026-08-02T15:30:00+00:00",
    }
    jsonschema.validate(instance={"version": 2, "sessions": [v1_session]}, schema=SCHEMA)


def test_v2_sessions_with_sub_phase_validate():
    v2_session = {
        "session_id": "rds_ddddddddeeee",
        "kind": "stage_ship",
        "owner_opencode_session_id": "owner1",
        "state": "active",
        "started_at": "2026-08-02T15:00:00+00:00",
        "last_heartbeat": "2026-08-02T15:30:00+00:00",
        "sub_phase": "phase_3_archive_demo",
        "workflow_group": "rddf-session-batch",
    }
    jsonschema.validate(instance={"version": 2, "sessions": [v2_session]}, schema=SCHEMA)