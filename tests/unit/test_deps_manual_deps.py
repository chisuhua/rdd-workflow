"""Unit tests for skills/deps/scripts/deps_output.py — merge_manual_deps."""
import logging
from pathlib import Path
import pytest
import yaml

from skills.deps.scripts import deps_output as do


class TestMergeManualDeps:
    """Tests for merge_manual_deps(changes, project_root).

    merge_manual_deps reads openspec/changes/<name>/roadmap-meta.yaml
    for each change and merges manual_deps / manual_blocks into the
    change records.
    """

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _write_roadmap_meta(project_root: str, name: str, data: dict) -> str:
        """Write a roadmap-meta.yaml for a given change and return its path."""
        path = Path(project_root) / "openspec" / "changes" / name / "roadmap-meta.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f)
        return str(path)

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_no_roadmap_meta_noop(self, tmp_path):
        """When no roadmap-meta.yaml exists for any change, changes are
        returned unmodified."""
        changes = [
            {"name": "change-a", "blocker": None, "blocks": []},
            {"name": "change-b", "blocker": None, "blocks": []},
        ]
        result = do.merge_manual_deps(changes, str(tmp_path))

        # Same list object, mutated in place
        assert result is changes
        assert result[0]["blocker"] is None
        assert result[0]["blocks"] == []
        assert result[1]["blocker"] is None
        assert result[1]["blocks"] == []

    def test_manual_deps_sets_blocker(self, tmp_path):
        """When a change has manual_deps: ['change-b'], its blocker is set
        to 'change-b' and 'change-b' is added to its blocks list."""
        self._write_roadmap_meta(str(tmp_path), "change-a", {
            "roadmap": {"manual_deps": ["change-b"]},
        })
        changes = [
            {"name": "change-a", "blocker": None, "blocks": []},
            {"name": "change-b", "blocker": None, "blocks": []},
        ]
        result = do.merge_manual_deps(changes, str(tmp_path))

        # change-a's blocker set to "change-b"
        assert result[0]["blocker"] == "change-b"
        # change-b added to change-a's blocks
        assert "change-b" in result[0]["blocks"]
        # recommendation annotated
        assert "manual override" in result[0].get("recommendation", "")

    def test_manual_blocks_sets_reverse(self, tmp_path):
        """When change-a has manual_blocks: ['change-c'], change-c's blocker
        is set to 'change-a'."""
        self._write_roadmap_meta(str(tmp_path), "change-a", {
            "roadmap": {"manual_blocks": ["change-c"]},
        })
        changes = [
            {"name": "change-a", "blocker": None, "blocks": []},
            {"name": "change-c", "blocker": None, "blocks": []},
        ]
        result = do.merge_manual_deps(changes, str(tmp_path))

        # change-c (index 1) should have blocker set to "change-a"
        assert result[1]["blocker"] == "change-a"
        # change-a should be in change-c's blocks
        assert "change-a" in result[1]["blocks"]
        # change-c's recommendation annotated
        assert "manual override" in result[1].get("recommendation", "")

    def test_respects_existing_blocker(self, tmp_path):
        """When a change already has a blocker from static analysis AND
        manual_deps, the existing static blocker is PRESERVED. Only blocks
        is extended, and recommendation is annotated."""
        self._write_roadmap_meta(str(tmp_path), "change-a", {
            "roadmap": {"manual_deps": ["change-c"]},
        })
        changes = [
            # change-a already has blocker "change-b" from static analysis
            {"name": "change-a", "blocker": "change-b", "blocks": []},
            {"name": "change-b", "blocker": None, "blocks": []},
            {"name": "change-c", "blocker": None, "blocks": []},
        ]
        result = do.merge_manual_deps(changes, str(tmp_path))

        # Existing blocker NOT overwritten
        assert result[0]["blocker"] == "change-b"
        # Blocks extended with the manual dep
        assert "change-c" in result[0]["blocks"]
        # recommendation annotated
        assert "manual override" in result[0].get("recommendation", "")

    def test_malformed_yaml_skipped(self, tmp_path, caplog):
        """When roadmap-meta.yaml has malformed YAML, the function logs a
        warning and skips that change without crashing."""
        caplog.set_level(logging.WARNING)

        # Write deliberately malformed YAML
        meta_path = (
            Path(tmp_path) / "openspec" / "changes" / "change-a" / "roadmap-meta.yaml"
        )
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.write_text("{ invalid: yaml: [[broken", encoding="utf-8")

        changes = [
            {"name": "change-a", "blocker": None, "blocks": []},
        ]
        # Should not raise
        result = do.merge_manual_deps(changes, str(tmp_path))

        assert result[0]["blocker"] is None
        assert result[0]["blocks"] == []
        # Should have logged a warning about malformed YAML
        assert any("malformed" in msg.lower() for msg in caplog.messages)

    def test_recommendation_annotated(self, tmp_path):
        """When human deps differ from static analysis, recommendation is
        annotated with 'manual override' and original text preserved."""
        self._write_roadmap_meta(str(tmp_path), "change-a", {
            "roadmap": {"manual_deps": ["change-c"]},
        })
        changes = [
            # Static analysis says blocked by change-b, human says depends on
            # change-c — blocker is preserved, but blocks extended
            {
                "name": "change-a",
                "blocker": "change-b",
                "blocks": [],
                "recommendation": "static: wait for change-b",
            },
            {"name": "change-b", "blocker": None, "blocks": []},
            {"name": "change-c", "blocker": None, "blocks": []},
        ]
        result = do.merge_manual_deps(changes, str(tmp_path))

        # Existing blocker preserved
        assert result[0]["blocker"] == "change-b"
        # Blocks includes the manual dep
        assert "change-c" in result[0]["blocks"]
        # Recommendation annotated with "manual override"
        rec = result[0].get("recommendation", "")
        assert "manual override" in rec
        # Original recommendation text preserved
        assert "static: wait for change-b" in rec