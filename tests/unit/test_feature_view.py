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


from skills._lib.feature_view import compute_feature_edges, UNGROUPED


def _deps(changes_pairs: list[tuple[str, str | None]]) -> dict:
    """Build a minimal deps-analysis-like dict from (change_name, blocker) pairs."""
    return {
        "changes": {
            name: {"name": name, "blocker": blocker, "conflicts": []}
            for name, blocker in changes_pairs
        }
    }


class TestComputeFeatureEdges:
    def test_all_pairs_hard_yields_one_edge(self):
        # 2 changes in A, 1 in B. m = 2*1 = 2. Each a blocks the single b.
        groups = {"A": ["a1", "a2"], "B": ["b1"]}
        deps = _deps([("a1", "b1"), ("a2", "b1")])
        edges = compute_feature_edges(deps, groups)
        assert ("A", "B", "hard") in edges

    def test_partial_overlap_yields_no_edge(self):
        # Fb has 2 changes but only 1 of the 2 a's blocks into it
        groups = {"A": ["a1", "a2"], "B": ["b1", "b2"]}
        deps = _deps([("a1", "b1"), ("a1", "b2")])  # a2 has no blocker
        edges = compute_feature_edges(deps, groups)
        assert edges == []

    def test_disjoint_yields_no_edge(self):
        groups = {"A": ["a1"], "B": ["b1"]}
        deps = _deps([])
        edges = compute_feature_edges(deps, groups)
        assert edges == []

    def test_ungrouped_excluded(self):
        groups = {"A": ["a1"], UNGROUPED: ["x"]}
        deps = _deps([("a1", "x")])
        edges = compute_feature_edges(deps, groups)
        assert edges == [], f"ungrouped should not produce edges, got {edges}"

    def test_self_loop_excluded(self):
        groups = {"A": ["a1", "a2"]}
        deps = _deps([("a1", "a2")])
        edges = compute_feature_edges(deps, groups)
        assert edges == []


from skills._lib.feature_view import compute_parallel_groups, FeatureCycleError


class TestComputeParallelGroups:
    def test_no_edges_all_wave_zero(self):
        features = {"A": 0, "B": 0, "C": 0}
        result = compute_parallel_groups([], features)
        assert result == {"A": 0, "B": 0, "C": 0}

    def test_chain_produces_three_waves(self):
        edges = [("A", "B", "hard"), ("B", "C", "hard")]
        features = {"A": 0, "B": 0, "C": 0}
        result = compute_parallel_groups(edges, features)
        assert result == {"A": 0, "B": 1, "C": 2}

    def test_diamond_shape(self):
        # A -> B, A -> C, B -> D, C -> D
        edges = [
            ("A", "B", "hard"), ("A", "C", "hard"),
            ("B", "D", "hard"), ("C", "D", "hard"),
        ]
        features = {"A": 0, "B": 0, "C": 0, "D": 0}
        result = compute_parallel_groups(edges, features)
        assert result == {"A": 0, "B": 1, "C": 1, "D": 2}

    def test_cycle_raises(self):
        edges = [("A", "B", "hard"), ("B", "A", "hard")]
        features = {"A": 0, "B": 0}
        with pytest.raises(FeatureCycleError) as exc_info:
            compute_parallel_groups(edges, features)
        assert set(exc_info.value.cycle) == {"A", "B"}

    def test_three_node_cycle_raises(self):
        edges = [("A", "B", "hard"), ("B", "C", "hard"), ("C", "A", "hard")]
        features = {"A": 0, "B": 0, "C": 0}
        with pytest.raises(FeatureCycleError) as exc_info:
            compute_parallel_groups(edges, features)
        assert set(exc_info.value.cycle) == {"A", "B", "C"}

    def test_edges_with_unknown_features_ignored(self):
        edges = [("A", "B", "hard"), ("A", "D", "hard"), ("E", "B", "hard")]
        features = {"A": 0, "B": 0}
        result = compute_parallel_groups(edges, features)
        assert result == {"A": 0, "B": 1}

    def test_empty_features_returns_empty_dict(self):
        assert compute_parallel_groups([], {}) == {}