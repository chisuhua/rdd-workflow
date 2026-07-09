import json
from pathlib import Path

import jsonschema
import pytest

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "skills" / "_lib" / "schemas" / "feature_view_schema.json"


@pytest.fixture
def schema() -> dict:
    with open(SCHEMA_PATH) as f:
        return json.load(f)


@pytest.fixture
def valid_payload() -> dict:
    return {
        "schema_version": 1,
        "updated_at": "2026-07-09T12:00:00+00:00",
        "features": {
            "feature-stream": {
                "name": "feature-stream",
                "status": "in_progress",
                "change_names": ["refactor-stream-base", "add-m2sPipe"],
                "change_count": 2,
                "archived_count": 0,
                "rollup_basis": "explicit",
                "depends_on": [],
                "blocks": ["feature-pipes"],
                "parallel_group": 0,
                "conflicts_with": [],
            }
        },
        "execution_order": [["feature-stream"], ["feature-pipes"]],
    }


class TestFeatureViewSchema:
    def test_valid_payload_accepted(self, schema, valid_payload):
        jsonschema.validate(valid_payload, schema)  # should not raise

    def test_missing_schema_version_rejected(self, schema, valid_payload):
        del valid_payload["schema_version"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(valid_payload, schema)

    def test_wrong_status_rejected(self, schema, valid_payload):
        valid_payload["features"]["feature-stream"]["status"] = "bogus"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(valid_payload, schema)

    def test_wrong_schema_version_rejected(self, schema, valid_payload):
        valid_payload["schema_version"] = 99
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(valid_payload, schema)

    def test_execution_order_must_be_list_of_lists(self, schema, valid_payload):
        valid_payload["execution_order"] = ["feature-stream", "feature-pipes"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(valid_payload, schema)

    def test_features_must_be_object(self, schema, valid_payload):
        valid_payload["features"] = ["feature-stream", "feature-pipes"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(valid_payload, schema)


from skills._lib.feature_view import group_changes_by_feature


class TestGroupChangesByFeature:
    def test_explicit_parent_feature(self):
        changes = [
            {"name": "a-core", "parent_feature": "feature-a"},
            {"name": "a-adapters", "parent_feature": "feature-a"},
            {"name": "b-core", "parent_feature": "feature-b"},
        ]
        result = group_changes_by_feature(changes)
        assert set(result.keys()) == {"feature-a", "feature-b"}, result
        assert sorted(result["feature-a"]) == ["a-adapters", "a-core"]
        assert result["feature-b"] == ["b-core"]

    def test_name_prefix_fallback(self):
        changes = [
            {"name": "feature-stream-core"},
            {"name": "feature-stream-adapters"},
            {"name": "feature-utils-helper"},
        ]
        result = group_changes_by_feature(changes)
        assert set(result.keys()) == {"feature-stream", "feature-utils"}, result

    def test_mixed_basis_uses_max_signal(self):
        changes = [
            {"name": "feature-stream-core"},
            {"name": "feature-stream-tests", "parent_feature": "feature-stream"},
        ]
        result = group_changes_by_feature(changes)
        assert list(result.keys()) == ["feature-stream"], result
        assert sorted(result["feature-stream"]) == ["feature-stream-core", "feature-stream-tests"]

    def test_ungrouped_synthetic(self):
        changes = [
            {"name": "fix-typo"},
            {"name": "debt-cleanup"},
            {"name": "feature-stream-core", "parent_feature": "feature-stream"},
        ]
        result = group_changes_by_feature(changes)
        assert "__ungrouped__" in result
        assert sorted(result["__ungrouped__"]) == ["debt-cleanup", "fix-typo"]
        assert result["feature-stream"] == ["feature-stream-core"]


from skills._lib.feature_view import rollup_status


class TestRollupStatus:
    def test_blocked_wins_over_in_progress(self):
        changes = [
            {"name": "a", "status": "blocked_by"},
            {"name": "b", "status": "in_worktree"},
        ]
        assert rollup_status(changes) == "blocked"

    def test_in_progress_when_no_blocker_and_one_in_worktree(self):
        changes = [
            {"name": "a", "status": "in_worktree"},
            {"name": "b", "status": "proposed"},
        ]
        assert rollup_status(changes) == "in_progress"

    def test_ready_when_all_proposed_or_planned(self):
        changes = [
            {"name": "a", "status": "proposed"},
            {"name": "b", "status": "planned"},
        ]
        assert rollup_status(changes) == "ready"

    def test_done_when_all_archived(self):
        changes = [
            {"name": "a", "status": "archived"},
            {"name": "b", "status": "archived"},
        ]
        assert rollup_status(changes) == "done"

    def test_in_progress_with_review_counts(self):
        changes = [
            {"name": "a", "status": "review"},
            {"name": "b", "status": "proposed"},
        ]
        assert rollup_status(changes) == "in_progress"

    def test_empty_returns_ungrouped(self):
        assert rollup_status([]) == "ungrouped"