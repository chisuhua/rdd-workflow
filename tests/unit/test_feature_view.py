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


from skills.feature.scripts.feature_view import group_changes_by_feature


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


from skills.feature.scripts.feature_view import rollup_status


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

    def test_completed_status_falls_through_to_in_progress(self):
        changes = [
            {"name": "a", "status": "completed"},
            {"name": "b", "status": "completed"},
        ]
        assert rollup_status(changes) == "in_progress"


from skills.feature.scripts.feature_view import compute_feature_edges, UNGROUPED


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


from skills.feature.scripts.feature_view import compute_parallel_groups, FeatureCycleError


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


from skills.feature.scripts.feature_view import render_mermaid


class TestRenderMermaid:
    def test_emits_flowchart_lr_header(self):
        out = render_mermaid({}, [], [], {})
        assert out.startswith("flowchart LR"), out

    def test_one_node_per_feature(self):
        features = {
            "A": {"status": "ready", "archived_count": 0, "change_count": 2, "parallel_group": 0},
            "B": {"status": "done", "archived_count": 1, "change_count": 1, "parallel_group": 1},
        }
        out = render_mermaid(features, [], [], {"A": 0, "B": 1})
        assert 'A["A' in out
        assert 'B["B' in out

    def test_hard_edge_renders_arrow(self):
        features = {"A": {"status": "ready", "archived_count": 0, "change_count": 1, "parallel_group": 0},
                    "B": {"status": "blocked", "archived_count": 0, "change_count": 1, "parallel_group": 1}}
        edges = [("A", "B", "hard")]
        out = render_mermaid(features, edges, [], {"A": 0, "B": 1})
        assert "A --> B" in out

    def test_conflict_renders_dotted_arrow(self):
        features = {"A": {"status": "ready", "archived_count": 0, "change_count": 1, "parallel_group": 0},
                    "B": {"status": "ready", "archived_count": 0, "change_count": 1, "parallel_group": 0}}
        out = render_mermaid(features, [], [("A", "B")], {"A": 0, "B": 0})
        assert "A -.->|冲突| B" in out

    def test_empty_features_emits_only_header(self):
        out = render_mermaid({}, [], [], {})
        assert out == "flowchart LR"

    def test_special_chars_in_feature_names(self):
        features = {"feature-stream_core": {"status": "ready", "archived_count": 0, "change_count": 1, "parallel_group": 0},
                    "feature-x_v2": {"status": "blocked", "archived_count": 0, "change_count": 1, "parallel_group": 1}}
        out = render_mermaid(features, [], [], {"feature-stream_core": 0, "feature-x_v2": 1})
        assert 'feature-stream_core["feature-stream_core' in out
        assert 'feature-x_v2["feature-x_v2' in out

    def test_deterministic_output(self):
        features = {"B": {"status": "ready", "archived_count": 0, "change_count": 1, "parallel_group": 0},
                    "A": {"status": "ready", "archived_count": 0, "change_count": 1, "parallel_group": 0}}
        out1 = render_mermaid(features, [], [], {"A": 0, "B": 0})
        out2 = render_mermaid(features, [], [], {"A": 0, "B": 0})
        assert out1 == out2
        assert out1.index("A[") < out1.index("B["), "features must be sorted by name"

    def test_label_includes_status_and_progress(self):
        features = {"A": {"status": "in_progress", "archived_count": 1, "change_count": 3, "parallel_group": 0}}
        out = render_mermaid(features, [], [], {"A": 0})
        assert "in_progress" in out
        assert "1/3" in out
        assert "wave 0" in out


from skills.feature.scripts import feature_view
from skills._lib import iteration


def _write_iteration(project_root, changes):
    state_dir = Path(project_root) / ".rddf" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "version": 3,
        "updated_at": "2026-07-09T00:00:00+00:00",
        "current_phase": "test",
        "changes": [{"name": c["name"], "status": c.get("status", "proposed"),
                     "added_at": "2026-07-09T00:00:00+00:00",
                     "parent_feature": c.get("parent_feature")}
                    for c in changes],
    }
    (state_dir / "iteration.json").write_text(json.dumps(data))


def _write_deps(project_root, changes_pairs, conflicts_pairs=None):
    state_dir = Path(project_root) / ".rddf" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    changes_map = {}
    for name, blocker in changes_pairs:
        if name not in changes_map:
            changes_map[name] = {"name": name, "blocker": blocker, "conflicts": []}
        else:
            changes_map[name]["blocker"] = blocker
    for a, b in (conflicts_pairs or []):
        if a in changes_map:
            changes_map[a]["conflicts"].append(b)
        else:
            changes_map[a] = {"name": a, "blocker": None, "conflicts": [b]}
    data = {"version": 1, "updated_at": "2026-07-09T00:00:00+00:00", "changes": changes_map}
    (state_dir / "deps-analysis.json").write_text(json.dumps(data))


class TestUpdateIterationFeatureView:
    def test_writes_feature_view_node(self, tmp_path):
        _write_iteration(tmp_path, [
            {"name": "feature-stream-core", "parent_feature": "feature-stream"},
            {"name": "feature-stream-tests", "parent_feature": "feature-stream"},
            {"name": "fix-typo"},
        ])
        count = feature_view.update_iteration_feature_view(str(tmp_path))
        assert count == 2  # feature-stream + __ungrouped__
        data = json.loads((tmp_path / ".rddf" / "state" / "iteration.json").read_text())
        assert "feature_view" in data
        fv = data["feature_view"]
        assert fv["schema_version"] == 1
        assert "feature-stream" in fv["features"]
        assert "__ungrouped__" in fv["features"]
        assert fv["features"]["feature-stream"]["status"] == "ready"
        assert fv["features"]["feature-stream"]["change_count"] == 2

    def test_missing_iteration_raises(self, tmp_path):
        import pytest
        with pytest.raises(feature_view.NoIterationError):
            feature_view.update_iteration_feature_view(str(tmp_path))

    def test_missing_deps_analysis_still_writes_status(self, tmp_path):
        _write_iteration(tmp_path, [
            {"name": "a-core", "parent_feature": "feature-a"},
        ])
        count = feature_view.update_iteration_feature_view(str(tmp_path))
        assert count == 1
        data = json.loads((tmp_path / ".rddf" / "state" / "iteration.json").read_text())
        fv = data["feature_view"]
        assert fv["features"]["feature-a"]["depends_on"] == []
        assert fv["features"]["feature-a"]["blocks"] == []
        assert fv["execution_order"] == [["feature-a"]]

    def test_conflicts_are_deduplicated(self, tmp_path):
        _write_iteration(tmp_path, [
            {"name": "a1", "parent_feature": "feature-a"},
            {"name": "a2", "parent_feature": "feature-a"},
            {"name": "b1", "parent_feature": "feature-b"},
        ])
        _write_deps(tmp_path, [], conflicts_pairs=[("a1", "b1"), ("a2", "b1")])
        feature_view.update_iteration_feature_view(str(tmp_path))
        data = json.loads((tmp_path / ".rddf" / "state" / "iteration.json").read_text())
        fv = data["feature_view"]
        assert fv["features"]["feature-a"]["conflicts_with"] == ["feature-b"]
        assert fv["features"]["feature-b"]["conflicts_with"] == ["feature-a"]
    def test_rollup_includes_blocked_by_from_deps(self, tmp_path):
        _write_iteration(tmp_path, [
            {"name": "a1", "parent_feature": "feature-a"},
        ])
        deps_data = {
            "version": 1,
            "updated_at": "2026-07-09T00:00:00+00:00",
            "changes": {
                "a1": {"name": "a1", "status": "blocked_by", "blocker": None, "conflicts": []}
            }
        }
        (tmp_path / ".rddf" / "state" / "deps-analysis.json").write_text(json.dumps(deps_data))
        feature_view.update_iteration_feature_view(str(tmp_path))
        data = json.loads((tmp_path / ".rddf" / "state" / "iteration.json").read_text())
        fv = data["feature_view"]
        assert fv["features"]["feature-a"]["status"] == "blocked"
        iteration_changes = {c["name"]: c for c in data.get("changes", [])}
        assert iteration_changes["a1"]["status"] == "proposed"

    def test_file_locked_error_when_save_times_out(self, tmp_path, monkeypatch):
        from skills._lib.core.lock import LockTimeout
        _write_iteration(tmp_path, [
            {"name": "a1", "parent_feature": "feature-a"},
        ])
        def _raise_timeout(*args, **kwargs):
            raise LockTimeout("simulated lock contention")
        monkeypatch.setattr(feature_view.it_mod, "save", _raise_timeout)
        with pytest.raises(feature_view.FileLockedError):
            feature_view.update_iteration_feature_view(str(tmp_path))
