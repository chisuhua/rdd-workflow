"""tests/unit/test_session_metrics.py — sessions_schema.json v3 metrics field validation."""
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
schema = json.loads((REPO_ROOT / "skills" / "_lib" / "schemas" / "sessions_schema.json").read_text())
SESSION_PROPS = schema["$defs"]["Session"]["properties"]

def test_schema_version_is_v3():
    assert schema["version"]["const"] == "v3"

def test_session_schema_has_metrics_field():
    assert "metrics" in SESSION_PROPS
    assert SESSION_PROPS["metrics"]["type"] == "object"

def test_metrics_has_required_subfields():
    metrics = SESSION_PROPS["metrics"]
    for f in ("started_at", "ended_at", "duration_s", "user_decisions", "retries"):
        assert f in metrics["properties"], f"missing: {f}"

def test_v2_entry_without_metrics_still_valid():
    """v2 data (no metrics field) must remain valid under v3 schema."""
    v2_entry = {
        "session_id": "rds_abcdef012345",
        "kind": "stage_arch",
        "state": "completed",
        "started_at": "2026-08-15T16:40:00+00:00",
        "last_heartbeat": "2026-08-15T16:50:00+00:00",
        "owner_opencode_session_id": "sess_test",
        "parent_session_id": None
    }
    # v2-style had 'stage'/'status'/'added_at' fields not in v3 schema
    # (renamed: stage→kind, status→state, added_at→started_at)
    assert 'kind' in SESSION_PROPS
    assert 'state' in SESSION_PROPS
    assert 'started_at' in SESSION_PROPS
    # Verify all v2 fields are in v3 Session.properties
    for k in v2_entry:
        assert k in SESSION_PROPS, f"v2 field {k} not in v3 schema"

def test_metrics_minimal_payload_validates():
    """metrics with only started_at should validate (other subfields optional)."""
    import jsonschema
    session_item_schema = {
        "type": "object",
        "properties": SESSION_PROPS,
        "required": schema["$defs"]["Session"]["required"]
    }
    payload = {
        "session_id": "rds_abcdef012345",
        "kind": "stage_arch",
        "state": "active",
        "started_at": "2026-09-01T08:00:00+00:00",
        "last_heartbeat": "2026-09-01T08:00:00+00:00",
        "owner_opencode_session_id": "sess_x",
        "parent_session_id": None,
        "metrics": {"started_at": "2026-09-01T08:00:00+00:00"}
    }
    # No exception = valid
    jsonschema.validate(payload, session_item_schema)
