"""Unit tests for skills/_lib/write_arch_handoff.py."""
import json
import os
import pytest
from skills._lib import write_arch_handoff as wah


@pytest.fixture
def tmp_repo(tmp_path):
    """Create a temporary repo structure with ADRs + roadmap."""
    root = tmp_path
    # Create ADR directory
    adr_dir = root / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    # Create 3 ADRs (skip 0000 template)
    for num, name in [("0001", "first-adr"), ("0002", "second-adr"), ("0003", "third-adr")]:
        (adr_dir / f"ADR-{num}-{name}.md").write_text(f"# ADR-{num}: {name}\n")
    # Create template (should be excluded)
    (adr_dir / "ADR-0000-template.md").write_text("# Template\n")
    # Create roadmap
    (root / "roadmap.md").write_text("# Roadmap\n\n**当前阶段**: phase-1\n")
    # Create state dir
    (root / ".rddf" / "state").mkdir(parents=True, exist_ok=True)
    return str(root)


class TestWriteArchHandoff:
    def test_writes_valid_json_with_correct_schema(self, tmp_repo):
        """Writes valid JSON with correct schema."""
        result = wah.write_arch_handoff(
            project_root=tmp_repo,
            discovered_adr_dir="docs/adr",
            discovered_roadmap_path="roadmap.md",
            discovered_architecture_dir="docs/architecture",
            discovered_adr_pattern="ADR-*.md",
        )
        assert isinstance(result, dict)
        assert "arch_complete_at" in result
        assert result["adr_count"] == 3  # excludes template
        assert result["version"] == 1
        # File should exist on disk
        path = os.path.join(tmp_repo, ".rddf", "state", ".arch-handoff.json")
        assert os.path.exists(path)

    def test_discovers_adr_files_by_pattern(self, tmp_repo):
        """Discovers ADR files matching the configured pattern."""
        result = wah.write_arch_handoff(
            project_root=tmp_repo,
            discovered_adr_dir="docs/adr",
            discovered_roadmap_path="roadmap.md",
            discovered_architecture_dir="docs/architecture",
            discovered_adr_pattern="ADR-*.md",
        )
        assert len(result["completed_adr_ids"]) == 3
        assert "0001" in result["completed_adr_ids"]
        assert "0002" in result["completed_adr_ids"]
        assert "0003" in result["completed_adr_ids"]

    def test_extracts_numeric_ids_from_filenames(self, tmp_repo):
        """Extracts numeric IDs like '0001' from 'ADR-0001-foo.md'."""
        result = wah.write_arch_handoff(
            project_root=tmp_repo,
            discovered_adr_dir="docs/adr",
            discovered_roadmap_path="roadmap.md",
            discovered_architecture_dir="docs/architecture",
            discovered_adr_pattern="ADR-*.md",
        )
        # IDs should be sorted numerically
        assert result["completed_adr_ids"] == ["0001", "0002", "0003"]

    def test_custom_adr_pattern(self, tmp_repo):
        """Works with custom patterns like DEC-*.md or RFD-*.md."""
        # Remove existing ADR files, create DEC-* pattern
        adr_dir = os.path.join(tmp_repo, "docs", "adr")
        for f in os.listdir(adr_dir):
            os.remove(os.path.join(adr_dir, f))
        for num in ["0001", "0002"]:
            with open(os.path.join(adr_dir, f"DEC-{num}-decision.md"), "w") as f:
                f.write(f"# DEC-{num}\n")

        result = wah.write_arch_handoff(
            project_root=tmp_repo,
            discovered_adr_dir="docs/adr",
            discovered_roadmap_path="roadmap.md",
            discovered_architecture_dir="docs/architecture",
            discovered_adr_pattern="DEC-*.md",
        )
        assert result["adr_count"] == 2
        assert "0001" in result["completed_adr_ids"]
        assert "0002" in result["completed_adr_ids"]

    def test_empty_adr_dir_graceful(self, tmp_repo):
        """Handles missing ADR directory gracefully (sets adr_count=0)."""
        import shutil
        shutil.rmtree(os.path.join(tmp_repo, "docs", "adr"))

        result = wah.write_arch_handoff(
            project_root=tmp_repo,
            discovered_adr_dir="docs/adr",  # doesn't exist now
            discovered_roadmap_path="roadmap.md",
            discovered_architecture_dir="docs/architecture",
            discovered_adr_pattern="ADR-*.md",
        )
        assert result["adr_count"] == 0
        assert result["completed_adr_ids"] == []

    def test_roadmap_phase_extraction(self, tmp_repo):
        """Extracts **当前阶段** from roadmap markdown."""
        with open(os.path.join(tmp_repo, "roadmap.md"), "w") as f:
            f.write("# Roadmap\n\n**当前阶段**: phase-3\n")

        result = wah.write_arch_handoff(
            project_root=tmp_repo,
            discovered_adr_dir="docs/adr",
            discovered_roadmap_path="roadmap.md",
            discovered_architecture_dir="docs/architecture",
            discovered_adr_pattern="ADR-*.md",
        )
        assert result["current_phase"] == "phase-3"

    def test_populates_discovery_fields(self, tmp_repo):
        """Populates discovered.adr_dir.found etc."""
        result = wah.write_arch_handoff(
            project_root=tmp_repo,
            discovered_adr_dir="docs/adr",
            discovered_roadmap_path="roadmap.md",
            discovered_architecture_dir="docs/architecture",
            discovered_adr_pattern="ADR-*.md",
            discovered_adr_dir_found="true",
            discovered_roadmap_found="true",
            discovered_arch_found="false",
            discovered_adr_dir_tried="3",
            discovered_roadmap_tried="2",
            discovered_arch_tried="1",
        )
        assert result["discovered"]["adr_dir"]["found"] is True
        assert result["discovered"]["roadmap_path"]["found"] is True
        assert result["discovered"]["architecture_dir"]["found"] is False
        assert result["discovered"]["adr_dir"]["candidates_tried"] == 3
        assert result["discovered"]["roadmap_path"]["candidates_tried"] == 2
        assert result["discovered"]["architecture_dir"]["candidates_tried"] == 1

    def test_version_field(self, tmp_repo):
        """Sets version: 1 (matches v1 schema)."""
        result = wah.write_arch_handoff(
            project_root=tmp_repo,
            discovered_adr_dir="docs/adr",
            discovered_roadmap_path="roadmap.md",
            discovered_architecture_dir="docs/architecture",
            discovered_adr_pattern="ADR-*.md",
        )
        assert result["version"] == 1

    def test_arch_complete_at_iso_timestamp(self, tmp_repo):
        """Sets arch_complete_at to ISO timestamp."""
        result = wah.write_arch_handoff(
            project_root=tmp_repo,
            discovered_adr_dir="docs/adr",
            discovered_roadmap_path="roadmap.md",
            discovered_architecture_dir="docs/architecture",
            discovered_adr_pattern="ADR-*.md",
        )
        assert "arch_complete_at" in result
        # Should be ISO 8601 with T separator and sufficient length
        assert "T" in result["arch_complete_at"]
        assert len(result["arch_complete_at"]) >= 19  # "YYYY-MM-DDTHH:MM:SS"

    def test_roadmap_exists_bool(self, tmp_repo):
        """Sets roadmap_exists boolean based on parameter."""
        # Path exists
        result = wah.write_arch_handoff(
            project_root=tmp_repo,
            discovered_adr_dir="docs/adr",
            discovered_roadmap_path="roadmap.md",
            discovered_architecture_dir="docs/architecture",
            discovered_adr_pattern="ADR-*.md",
            roadmap_exists_bool="true",
        )
        assert result["roadmap_exists"] is True

        # Path doesn't exist
        result = wah.write_arch_handoff(
            project_root=tmp_repo,
            discovered_adr_dir="docs/adr",
            discovered_roadmap_path="nonexistent.md",
            discovered_architecture_dir="docs/architecture",
            discovered_adr_pattern="ADR-*.md",
            roadmap_exists_bool="false",
        )
        assert result["roadmap_exists"] is False