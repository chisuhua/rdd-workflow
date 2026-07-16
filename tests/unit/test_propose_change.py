"""Unit tests for skills/_lib/propose_change.py."""
import json
import pytest
from skills._lib import propose_change as pc


@pytest.fixture
def project_root(tmp_path):
    (tmp_path / "proposal-suggestions.md").write_text("[]")
    return str(tmp_path)


@pytest.fixture
def project_with_suggestions(tmp_path):
    entries = [
        {"name": "c1", "status": "待创建"},
        {"name": "c2", "status": "created"},
    ]
    (tmp_path / "proposal-suggestions.md").write_text(
        json.dumps(entries, ensure_ascii=False, indent=2)
    )
    return str(tmp_path)


class TestSetSuggestionStatus:
    def test_updates_status_for_matching_name(self, project_with_suggestions):
        result = pc.set_suggestion_status(project_with_suggestions, "c1", "skeleton")
        assert result is True
        with open(f"{project_with_suggestions}/proposal-suggestions.md") as f:
            entries = json.load(f)
        assert entries[0]["status"] == "skeleton"
        assert entries[1]["status"] == "created"  # unchanged

    def test_no_op_when_name_not_found(self, project_with_suggestions):
        result = pc.set_suggestion_status(project_with_suggestions, "c999", "skeleton")
        assert result is False

    def test_no_op_when_file_missing(self, project_root):
        import os
        os.remove(f"{project_root}/proposal-suggestions.md")
        result = pc.set_suggestion_status(project_root, "c1", "skeleton")
        assert result is False

    def test_preserves_other_fields(self, project_with_suggestions):
        # Add extra fields to first entry
        with open(f"{project_with_suggestions}/proposal-suggestions.md") as f:
            entries = json.load(f)
        entries[0]["phase"] = "phase-1"
        entries[0]["priority"] = "P2"
        with open(f"{project_with_suggestions}/proposal-suggestions.md", "w") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
            f.write("\n")
        pc.set_suggestion_status(project_with_suggestions, "c1", "skeleton")
        with open(f"{project_with_suggestions}/proposal-suggestions.md") as f:
            entries = json.load(f)
        assert entries[0]["status"] == "skeleton"
        assert entries[0]["phase"] == "phase-1"  # preserved
        assert entries[0]["priority"] == "P2"   # preserved
        assert entries[0]["name"] == "c1"       # preserved

    def test_returns_false_on_malformed_json(self, tmp_path):
        bad_file = tmp_path / "proposal-suggestions.md"
        bad_file.write_text("not valid json {{{")
        result = pc.set_suggestion_status(str(tmp_path), "c1", "skeleton")
        assert result is False

class TestCreateSkeletonChange:
    """create_skeleton_change writes minimal proposal.md + roadmap-meta.yaml
    and updates iteration.json (status=planned). Encapsulates the skeleton
    branch of propose.md Phase 4 (lines 486-551).
    """

    def test_writes_proposal_md_with_why_and_what_changes(self, tmp_path):
        result = pc.create_skeleton_change(
            project_root=str(tmp_path),
            name="my-change",
            current_phase="phase-1",
            category="general",
            priority="P2",
        )
        assert result is True
        proposal = (tmp_path / "openspec" / "changes" / "my-change" / "proposal.md").read_text()
        assert "## Why" in proposal
        assert "## What Changes" in proposal

    def test_writes_roadmap_meta_yaml(self, tmp_path):
        pc.create_skeleton_change(str(tmp_path), "c1", "phase-1", "general", "P2")
        yaml_path = tmp_path / "openspec" / "changes" / "c1" / "roadmap-meta.yaml"
        assert yaml_path.exists()
        content = yaml_path.read_text()
        assert 'phase: "phase-1"' in content
        assert 'category: "general"' in content
        assert 'priority: "P2"' in content

    def test_updates_iteration_json_status_to_planned(self, tmp_path):
        from skills._lib import iteration as it
        it.save(str(tmp_path), it.create_empty())
        pc.create_skeleton_change(str(tmp_path), "c1", "phase-1", "general", "P2")
        loaded = it.load(str(tmp_path))
        names = [c["name"] for c in loaded["changes"]]
        assert "c1" in names
        match = next(c for c in loaded["changes"] if c["name"] == "c1")
        assert match["status"] == "planned"

    def test_returns_true_even_when_iteration_module_unavailable(self, tmp_path, monkeypatch):
        # Simulate ImportError by patching sys.modules
        import sys
        monkeypatch.setitem(sys.modules, "skills._lib.iteration", None)
        # Should not crash; proposal + yaml should still be written
        result = pc.create_skeleton_change(str(tmp_path), "c1", "phase-1", "general", "P2")
        assert result is True
        # proposal.md + yaml should exist
        assert (tmp_path / "openspec" / "changes" / "c1" / "proposal.md").exists()
        assert (tmp_path / "openspec" / "changes" / "c1" / "roadmap-meta.yaml").exists()


class TestUpdateRoadmapMeta:
    """update_roadmap_meta encapsulates lines 617-686 of propose.md:
    - Lookup phase/category from proposal-suggestions.md (or fallback)
    - Validate category against valid_categories list
    - Write roadmap-meta.yaml

    Per baseline correction: uses real init_state('phase-1') categories
    (arch-design, infra-setup, core-impl, core-test), NOT 'general'.
    """

    def test_writes_yaml_with_phase_and_category(self, tmp_path):
        (tmp_path / "openspec" / "changes" / "c1").mkdir(parents=True)
        # Set up proposal-suggestions.md with explicit phase/category
        entries = [{"name": "c1", "phase": "phase-2", "category": "core-impl"}]
        (tmp_path / "proposal-suggestions.md").write_text(json.dumps(entries))
        result = pc.update_roadmap_meta(
            str(tmp_path), "c1",
            current_phase="phase-1",
            change_category="arch-design",
            priority="P2",
            valid_categories=(
                "arch-design:Architecture Design\n"
                "infra-setup:Infrastructure Setup\n"
                "core-impl:Core Implementation\n"
                "core-test:Core Test"
            ),
        )
        assert result is True
        yaml_path = tmp_path / "openspec" / "changes" / "c1" / "roadmap-meta.yaml"
        assert yaml_path.exists()
        content = yaml_path.read_text()
        # Should use entry's phase (phase-2) not current_phase
        assert 'phase: "phase-2"' in content
        assert 'category: "core-impl"' in content

    def test_falls_back_to_arguments_when_suggestions_missing(self, tmp_path):
        (tmp_path / "openspec" / "changes" / "c1").mkdir(parents=True)
        # No proposal-suggestions.md
        result = pc.update_roadmap_meta(
            str(tmp_path), "c1",
            current_phase="phase-3",
            change_category="arch-design",
            priority="P1",
            valid_categories="arch-design:Arch",
        )
        assert result is True
        yaml_path = tmp_path / "openspec" / "changes" / "c1" / "roadmap-meta.yaml"
        content = yaml_path.read_text()
        assert 'phase: "phase-3"' in content

    def test_always_falls_back_to_general_when_category_invalid(self, tmp_path):
        (tmp_path / "openspec" / "changes" / "c1").mkdir(parents=True)
        entries = [{"name": "c1", "category": "nonexistent"}]
        (tmp_path / "proposal-suggestions.md").write_text(json.dumps(entries))
        result = pc.update_roadmap_meta(
            str(tmp_path), "c1",
            current_phase="phase-1",
            change_category="general",
            priority="P2",
            valid_categories=(
                "arch-design:Architecture Design\n"
                "infra-setup:Infrastructure Setup\n"
                "core-impl:Core Implementation\n"
                "core-test:Core Test"
            ),
        )
        assert result is True
        yaml_path = tmp_path / "openspec" / "changes" / "c1" / "roadmap-meta.yaml"
        content = yaml_path.read_text()
        # Should ALWAYS fallback to 'general' regardless of valid_categories
        assert 'category: "general"' in content

    def test_returns_false_when_change_directory_missing(self, tmp_path):
        result = pc.update_roadmap_meta(
            str(tmp_path), "missing-change",
            current_phase="phase-1",
            change_category="arch-design",
            priority="P2",
            valid_categories="arch-design:Architecture",
        )
        assert result is False

    def test_uses_priority_argument(self, tmp_path):
        (tmp_path / "openspec" / "changes" / "c1").mkdir(parents=True)
        result = pc.update_roadmap_meta(
            str(tmp_path), "c1",
            current_phase="phase-1",
            change_category="core-impl",
            priority="P0",
            valid_categories="arch-design:Arch\ncore-impl:Core",
        )
        yaml_path = tmp_path / "openspec" / "changes" / "c1" / "roadmap-meta.yaml"
        assert 'priority: "P0"' in yaml_path.read_text()


class TestUpdateRoadmapState:
    """update_roadmap_state encapsulates lines 688-711 of propose.md:
    Add change to .rddf/state/roadmap-state.json under the right
    phase/category. Uses existing roadmap_state.update_change_count helper.

    Per baseline correction: defensive against missing phase/category.
    """

    def test_adds_change_to_correct_phase_and_category(self, tmp_path):
        from skills._lib import roadmap_state as rs
        # Initialize roadmap-state.json with real init_state defaults
        state_file = str(tmp_path / ".rddf" / "state" / "roadmap-state.json")
        rs.init_state(state_file, "phase-1")
        result = pc.update_roadmap_state(str(tmp_path), "c1", "phase-1", "arch-design")
        assert result is True
        state = rs.read_state(state_file)
        changes = state["phases"]["phase-1"]["categories"]["arch-design"]["changes"]
        assert "c1" in changes

    def test_does_not_duplicate_existing_change(self, tmp_path):
        from skills._lib import roadmap_state as rs
        state_file = str(tmp_path / ".rddf" / "state" / "roadmap-state.json")
        rs.init_state(state_file, "phase-1")
        pc.update_roadmap_state(str(tmp_path), "c1", "phase-1", "arch-design")
        pc.update_roadmap_state(str(tmp_path), "c1", "phase-1", "arch-design")
        state = rs.read_state(state_file)
        changes = state["phases"]["phase-1"]["categories"]["arch-design"]["changes"]
        # No duplicates (update_change_count is idempotent)
        assert changes.count("c1") == 1

    def test_handles_missing_category_gracefully(self, tmp_path):
        """Per baseline: update_change_count raises KeyError when category
        doesn't exist in state. update_roadmap_state MUST catch this
        gracefully (matches original inline behavior lines 707-709).
        """
        from skills._lib import roadmap_state as rs
        state_file = str(tmp_path / ".rddf" / "state" / "roadmap-state.json")
        rs.init_state(state_file, "phase-1")
        # 'nonexistent' is NOT in phase-1's default categories
        result = pc.update_roadmap_state(
            str(tmp_path), "c1", "phase-1", "nonexistent"
        )
        # Must NOT crash; returns False (graceful skip)
        assert result is False or result is None
        # State file unchanged
        state = rs.read_state(state_file)
        assert "nonexistent" not in state["phases"]["phase-1"]["categories"]

    def test_handles_missing_phase_gracefully(self, tmp_path):
        """Same defensive behavior for missing phase."""
        from skills._lib import roadmap_state as rs
        state_file = str(tmp_path / ".rddf" / "state" / "roadmap-state.json")
        rs.init_state(state_file, "phase-1")
        result = pc.update_roadmap_state(
            str(tmp_path), "c1", "nonexistent-phase", "arch-design"
        )
        assert result is False or result is None

    def test_returns_none_when_state_file_missing(self, tmp_path):
        # No roadmap-state.json at all
        result = pc.update_roadmap_state(str(tmp_path), "c1", "phase-1", "arch-design")
        # Returns None for graceful skip
        assert result is None or result is False


class TestUpdateIterationProposed:
    """update_iteration_proposed encapsulates lines 713-760 of propose.md:
    Updates iteration.json with status=proposed + phase/category/priority.

    Per baseline: phase/category values are real init_state defaults
    (phase-1, arch-design/infra-setup/core-impl/core-test), NOT 'general'.
    """

    def test_updates_status_to_proposed(self, tmp_path):
        from skills._lib import iteration as it
        it.save(str(tmp_path), it.create_empty())
        pc.update_iteration_proposed(
            str(tmp_path), "c1",
            phase="phase-1", category="core-impl", priority="P2",
        )
        loaded = it.load(str(tmp_path))
        match = next(c for c in loaded["changes"] if c["name"] == "c1")
        assert match["status"] == "proposed"
        assert match["phase"] == "phase-1"
        assert match["category"] == "core-impl"
        assert match["priority"] == "P2"

    def test_handles_special_chars_in_change_name_safely(self, tmp_path):
        from skills._lib import iteration as it
        it.save(str(tmp_path), it.create_empty())
        # Should not raise even with special characters in name
        pc.update_iteration_proposed(
            str(tmp_path), "test-with-dash_and_underscore",
            phase="phase-1", category="core-impl", priority="P2",
        )
        loaded = it.load(str(tmp_path))
        names = [c["name"] for c in loaded["changes"]]
        assert "test-with-dash_and_underscore" in names
