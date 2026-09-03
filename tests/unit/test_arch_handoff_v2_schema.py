"""Consumer-side compat tests for v2 arch-handoff contract (Stage 3 / ADR-0042).

Locks: existing v1 consumers (state_reader, jq parsing in plan_intake.sh)
accept v2 handoff with extra additive fields.
"""
import json
import shutil
from pathlib import Path

import pytest


V2_FIXTURE = {
    "arch_complete_at": "2026-09-03T10:00:00Z",
    "adr_count": 3,
    "completed_adr_ids": ["0001", "0002", "0003"],
    "roadmap_exists": True,
    "current_phase": "phase-1",
    "plan_started_at": None,
    "adr_dir": "docs/adr",
    "roadmap_path": "roadmap.md",
    "architecture_dir": "docs/architecture",
    "adr_pattern": "ADR-*.md",
    "adr_regex": r"^ADR-(\d{3})-.*\.md$",
    "roadmap_fragments_dir": ".rddf/roadmap",
    "discovered": {
        "adr_dir": {"found": True, "created": False, "candidates_tried": 1},
        "roadmap_path": {"found": True, "created": False, "candidates_tried": 1},
        "architecture_dir": {"found": False, "created": False, "candidates_tried": 2},
    },
    "version": 2,
}


class TestArchHandoffV2ConsumerCompat:
    def test_v2_handoff_validates_against_schema(self, tmp_path):
        """v2 handoff with all additive fields validates against arch_handoff_schema.json."""
        import jsonschema
        schema_path = Path("_lib/schemas/arch_handoff_schema.json")
        with open(schema_path) as f:
            schema = json.load(f)
        jsonschema.validate(V2_FIXTURE, schema)

    def test_v1_minimal_payload_still_validates(self, tmp_path):
        """v1 payload (only required fields) still validates against v2 schema (backward compat)."""
        import jsonschema
        schema_path = Path("_lib/schemas/arch_handoff_schema.json")
        with open(schema_path) as f:
            schema = json.load(f)
        v1_minimal = {
            "arch_complete_at": "2026-08-01T10:00:00Z",
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
                "architecture_dir": {"found": False, "created": False, "candidates_tried": 2},
            },
            "version": 1,
        }
        jsonschema.validate(v1_minimal, schema)

    def test_v2_handoff_with_unknown_field_validates_due_to_additional_properties(self, tmp_path):
        """Per ADR-0016 v2 additive: unknown fields are tolerated."""
        import jsonschema
        schema_path = Path("_lib/schemas/arch_handoff_schema.json")
        with open(schema_path) as f:
            schema = json.load(f)
        v2_with_extra = dict(V2_FIXTURE)
        v2_with_extra["future_field_v3"] = {"anything": "goes"}
        jsonschema.validate(v2_with_extra, schema)

    def test_state_reader_accepts_v2_payload(self, tmp_path):
        """Per ADR-0042: state_reader is a v1 consumer — must tolerate v2 handoff."""
        from _lib.state_reader import read_arch_handoff
        handoff_path = tmp_path / ".rddf" / "state" / ".arch-handoff.json"
        handoff_path.parent.mkdir(parents=True, exist_ok=True)
        handoff_path.write_text(json.dumps(V2_FIXTURE))
        state = read_arch_handoff(str(tmp_path))
        assert state is not None
        assert state["version"] == 2
        assert state["adr_count"] == 3

    def test_v2_handoff_preserves_adr_regex_through_consumer(self, tmp_path):
        """Per complete-project-yaml-config-gaps M4: adr_regex passthrough survives consumer."""
        from _lib.state_reader import read_arch_handoff
        handoff_path = tmp_path / ".rddf" / "state" / ".arch-handoff.json"
        handoff_path.parent.mkdir(parents=True, exist_ok=True)
        handoff_path.write_text(json.dumps(V2_FIXTURE))
        state = read_arch_handoff(str(tmp_path))
        assert state["adr_regex"] == r"^ADR-(\d{3})-.*\.md$"
        assert state["roadmap_fragments_dir"] == ".rddf/roadmap"

    def test_plan_intake_jq_parse_accepts_v2(self, tmp_path):
        """plan_intake.sh uses jq to extract ADR_DIR/ROADMAP_PATH from handoff — v2 must parse."""
        handoff_path = tmp_path / ".rddf" / "state" / ".arch-handoff.json"
        handoff_path.parent.mkdir(parents=True, exist_ok=True)
        handoff_path.write_text(json.dumps(V2_FIXTURE))
        import shutil
        if not shutil.which("jq"):
            pytest.skip("jq not installed")
        import subprocess
        result = subprocess.run(
            ["jq", "-e", ".adr_dir, .roadmap_path, .adr_pattern, .adr_regex, .version",
             str(handoff_path)],
            capture_output=True, text=True, timeout=5,
        )
        assert result.returncode == 0, f"jq failed: {result.stderr}"
        lines = result.stdout.strip().splitlines()
        assert '"docs/adr"' in lines[0]
        assert '"roadmap.md"' in lines[1]
        assert '"ADR-*.md"' in lines[2]
        assert "ADR-" in lines[3] and "md" in lines[3]
        assert lines[4] == "2"