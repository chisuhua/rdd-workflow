"""Schema v1.1: proposals_authored renamed to proposals_ready.

Per fix-v4-rdd-planner-scope-over-assignment Task 4 / A3 + B3.
"""
import json
from pathlib import Path

SCHEMA_PATH = Path("_lib/schemas/planner_handoff_schema.json")


def test_schema_excludes_proposals_authored():
    text = SCHEMA_PATH.read_text()
    assert '"proposals_authored"' not in text, "schema must drop proposals_authored (fiction)"


def test_schema_includes_proposals_ready():
    schema = json.loads(SCHEMA_PATH.read_text())
    assert "proposals_ready" in schema.get("properties", {}), \
        "schema must have proposals_ready"


def test_planner_stage_exit_emits_proposals_ready():
    """End-to-end: running planner_stage_exit.sh produces JSON with proposals_ready."""
    import subprocess
    result = subprocess.run(
        ["bash", "skills/rdd-planner/scripts/planner_stage_exit.sh", "fix-v4-rdd-planner-scope-over-assignment"],
        capture_output=True, text=True, cwd="/workspace/project/rdd-workflow"
    )
    handoff_path = Path(".rddf/state/.planner-handoff.json")
    if handoff_path.exists():
        text = handoff_path.read_text()
        assert '"proposals_ready"' in text
        assert '"proposals_authored"' not in text


def test_planner_stage_entry_uses_proposals_ready_env():
    """scripts use PROPOSALS_READY env var (not PROPOSALS_AUTHORED)."""
    for script in ["skills/rdd-planner/scripts/planner_stage_entry.sh",
                   "skills/rdd-planner/scripts/planner_stage_exit.sh"]:
        text = Path(script).read_text()
        assert "PROPOSALS_AUTHORED" not in text, \
            f"{script} still references PROPOSALS_AUTHORED (should be PROPOSALS_READY)"


def test_ac13_planner_state_has_recommended_route():
    """AC-13: planner-state schema v1.1 has recommended_route advisory field."""
    schema = json.loads(Path("_lib/schemas/planner_state_schema.json").read_text())
    properties = schema.get("properties", {})
    assert "recommended_route" in properties, "planner-state missing recommended_route"
    rec = properties["recommended_route"]
    assert "enum" in rec or "type" in rec, "recommended_route must declare enum or type"
