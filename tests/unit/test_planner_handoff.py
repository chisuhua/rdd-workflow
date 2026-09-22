"""Tests for _lib/planner_handoff.py"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, '/workspace/project/rdd-workflow')
from _lib.planner_handoff import read_planner_handoff, write_planner_handoff


class TestWriteReadRoundtrip:
    def test_basic_write_read_roundtrip(self, tmp_path):
        proposals = ["proposal-a", "proposal-b"]
        features = ["feat-x", "feat-y"]
        result = write_planner_handoff(
            str(tmp_path),
            proposals,
            3,
            features,
            "sprint-2026-09",
        )
        read_back = read_planner_handoff(str(tmp_path))
        assert read_back["schema"] == "planner-handoff-v1"
        assert read_back["version"] == 1
        assert read_back["owner"] == "rdd-planner"
        assert read_back["current_sprint"] == "sprint-2026-09"
        assert read_back["proposals_ready"] == proposals
        assert read_back["proposals_approved_count"] == 3
        assert read_back["features_active"] == features
        assert "planner_complete_at" in read_back


class TestSchemaValidation:
    def test_schema_version_owner(self, tmp_path):
        result = write_planner_handoff(
            str(tmp_path),
            [],
            0,
            [],
            "sprint-2026-09",
        )
        assert result["schema"] == "planner-handoff-v1"
        assert result["version"] == 1
        assert result["owner"] == "rdd-planner"


class TestEmptyEdgeCases:
    def test_empty_lists(self, tmp_path):
        result = write_planner_handoff(
            str(tmp_path),
            [],
            0,
            [],
            "sprint-empty",
        )
        assert result["proposals_ready"] == []
        assert result["features_active"] == []
        assert result["proposals_approved_count"] == 0
        read_back = read_planner_handoff(str(tmp_path))
        assert read_back["proposals_ready"] == []
        assert read_back["features_active"] == []
        assert read_back["proposals_approved_count"] == 0

    def test_proposals_approved_count_zero(self, tmp_path):
        result = write_planner_handoff(
            str(tmp_path),
            [],
            0,
            [],
            "sprint-zero-count",
        )
        assert result["proposals_approved_count"] == 0
        read_back = read_planner_handoff(str(tmp_path))
        assert read_back["proposals_approved_count"] == 0

    def test_special_characters_in_sprint(self, tmp_path):
        result = write_planner_handoff(
            str(tmp_path),
            [],
            0,
            [],
            "sprint-2026-09",
        )
        read_back = read_planner_handoff(str(tmp_path))
        assert read_back["current_sprint"] == "sprint-2026-09"


class TestOverwrite:
    def test_overwrite(self, tmp_path):
        write_planner_handoff(
            str(tmp_path),
            ["p1"],
            1,
            ["f1"],
            "sprint-1",
        )
        write_planner_handoff(
            str(tmp_path),
            ["p1", "p2", "p3"],
            5,
            ["f1", "f2"],
            "sprint-2",
        )
        read_back = read_planner_handoff(str(tmp_path))
        assert read_back["proposals_ready"] == ["p1", "p2", "p3"]
        assert read_back["proposals_approved_count"] == 5
        assert read_back["features_active"] == ["f1", "f2"]
        assert read_back["current_sprint"] == "sprint-2"


class TestMissingFile:
    def test_missing_file(self, tmp_path):
        result = read_planner_handoff(str(tmp_path))
        assert result == {}


class TestEnvVarPattern:
    def test_env_var_pattern(self, tmp_path):
        env = {
            "PROJECT_ROOT": str(tmp_path),
            "PROPOSALS_READY": "prop-a,prop-b,prop-c",
            "PROPOSALS_APPROVED_COUNT": "7",
            "FEATURES_ACTIVE": "feat-m,feat-n",
            "CURRENT_SPRINT": "sprint-env-test",
        }
        result = subprocess.run(
            [sys.executable, "-c", """
import os
import sys
sys.path.insert(0, '/workspace/project/rdd-workflow')
from _lib.planner_handoff import write_planner_handoff, read_planner_handoff
project_root = os.environ.get('PROJECT_ROOT')
proposals_ready = [p for p in os.environ.get('PROPOSALS_READY', '').split(',') if p.strip()]
proposals_approved_count = int(os.environ.get('PROPOSALS_APPROVED_COUNT', '0'))
features_active = [p for p in os.environ.get('FEATURES_ACTIVE', '').split(',') if p.strip()]
current_sprint = os.environ.get('CURRENT_SPRINT')
write_planner_handoff(project_root, proposals_ready, proposals_approved_count, features_active, current_sprint)
read_back = read_planner_handoff(project_root)
assert read_back['proposals_ready'] == ['prop-a', 'prop-b', 'prop-c'], f'proposals mismatch: {read_back}'
assert read_back['proposals_approved_count'] == 7, f'count mismatch: {read_back}'
assert read_back['features_active'] == ['feat-m', 'feat-n'], f'features mismatch: {read_back}'
assert read_back['current_sprint'] == 'sprint-env-test', f'sprint mismatch: {read_back}'
print('OK')
"""],
            env={**os.environ, **env},
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"
        assert "OK" in result.stdout


class TestFieldPreservation:
    def test_field_preservation_across_reads(self, tmp_path):
        original = write_planner_handoff(
            str(tmp_path),
            ["proposal-x"],
            10,
            ["feature-a", "feature-b"],
            "sprint-preserve",
        )
        for _ in range(3):
            read_back = read_planner_handoff(str(tmp_path))
            assert read_back["schema"] == original["schema"]
            assert read_back["version"] == original["version"]
            assert read_back["owner"] == original["owner"]
            assert read_back["current_sprint"] == original["current_sprint"]
            assert read_back["proposals_ready"] == original["proposals_ready"]
            assert read_back["proposals_approved_count"] == original["proposals_approved_count"]
            assert read_back["features_active"] == original["features_active"]


class TestActiveObjectives:
    """active_objectives field (per add-objective-aware-planner): rdd-planner
    objective awareness — list of active objectives with id/priority/status/
    review_by/theme/next_sprint_candidates. Consumed by rdd-planner LLM at
    stage entry to recommend next tasks based on each objective's §10."""

    def test_basic_roundtrip_with_objectives(self, tmp_path):
        objectives = [
            {
                "id": "objective-onboard-new-skill",
                "priority": "P1",
                "status": "active",
                "review_by": "2026-12-21",
                "theme": "新增 skill 的标准化 onboarding 流程",
                "next_sprint_candidates": [
                    "起草 add-skill-onboarding 入口 SKILL.md + 5 段 improvement 草稿",
                    "复用 add-improve/SKILL.md 的 pre_create_brainstorm_check.sh HARD-GATE",
                ],
            }
        ]
        result = write_planner_handoff(
            str(tmp_path),
            ["proposal-a"],
            1,
            ["feat-x"],
            "sprint-2026-09",
            active_objectives=objectives,
        )
        assert result["active_objectives"] == objectives
        read_back = read_planner_handoff(str(tmp_path))
        assert read_back["active_objectives"] == objectives

    def test_default_empty_list(self, tmp_path):
        """Backwards compat: callers not yet passing active_objectives get []."""
        result = write_planner_handoff(
            str(tmp_path), [], 0, [], "sprint-2026-09"
        )
        assert result["active_objectives"] == []
        read_back = read_planner_handoff(str(tmp_path))
        assert read_back["active_objectives"] == []

    def test_multiple_objectives_preserved(self, tmp_path):
        objectives = [
            {
                "id": "objective-onboard-new-skill",
                "priority": "P1",
                "status": "active",
                "review_by": "2026-12-21",
                "theme": "新增 skill 的标准化 onboarding 流程",
                "next_sprint_candidates": ["cand-A", "cand-B"],
            },
            {
                "id": "objective-bypass-audit-hub-governance",
                "priority": "P2",
                "status": "deferred",
                "review_by": "2026-12-21",
                "theme": "统一 bypass audit + hub federation governance",
                "next_sprint_candidates": [],
            },
        ]
        result = write_planner_handoff(
            str(tmp_path), [], 0, [], "sprint-2026-09",
            active_objectives=objectives,
        )
        assert len(result["active_objectives"]) == 2
        assert result["active_objectives"][0]["id"] == "objective-onboard-new-skill"
        assert result["active_objectives"][1]["status"] == "deferred"
        # §10 N/A → 空 candidates list preserved (per objective D9 N/A format)
        assert result["active_objectives"][1]["next_sprint_candidates"] == []

    def test_env_var_active_objectives_json(self, tmp_path):
        """__main__ parses ACTIVE_OBJECTIVES_JSON env var into the field."""
        import json as _json
        env_payload = [
            {
                "id": "objective-x",
                "priority": "P1",
                "status": "active",
                "review_by": "2026-12-21",
                "theme": "test theme",
                "next_sprint_candidates": ["do thing 1", "do thing 2"],
            }
        ]
        env = {
            "PROJECT_ROOT": str(tmp_path),
            "PROPOSALS_READY": "",
            "PROPOSALS_APPROVED_COUNT": "0",
            "FEATURES_ACTIVE": "",
            "CURRENT_SPRINT": "sprint-env-obj",
            "RECOMMENDED_ROUTE": "unknown",
            "ACTIVE_OBJECTIVES_JSON": _json.dumps(env_payload),
        }
        result = subprocess.run(
            [sys.executable, "-c", """
import os, sys
sys.path.insert(0, '/workspace/project/rdd-workflow')
import json as _json
from _lib.planner_handoff import write_planner_handoff, read_planner_handoff
payload = _json.loads(os.environ['ACTIVE_OBJECTIVES_JSON'])
result = write_planner_handoff(
    os.environ['PROJECT_ROOT'], [], 0, [], os.environ['CURRENT_SPRINT'],
    recommended_route=os.environ['RECOMMENDED_ROUTE'],
    active_objectives=payload,
)
read_back = read_planner_handoff(os.environ['PROJECT_ROOT'])
assert read_back['active_objectives'] == payload
print('OK')
"""],
            env={**os.environ, **env},
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"
        assert "OK" in result.stdout
