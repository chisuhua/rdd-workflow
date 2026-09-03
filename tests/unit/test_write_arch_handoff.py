"""Unit tests for _lib/write_arch_handoff.py."""
import json
import os
import pytest
import threading
from skills.guide_arch.scripts import write_arch_handoff as wah


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
        assert result["version"] == 2
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

    def test_writes_adr_regex_from_project_yaml_when_present(self, tmp_repo):
        """write_arch_handoff reads .rddf/project.yaml adr.pattern and writes adr_regex.

        Per complete-project-yaml-config-gaps M4 Task 4.6: arch-handoff carries
        the Python regex from project.yaml so populate_lib can pass it through.
        """
        from pathlib import Path
        rd = Path(tmp_repo)
        # Create project.yaml with 3-digit adr.pattern
        project_dir = rd / ".rddf"
        project_dir.mkdir(exist_ok=True)
        (project_dir / "project.yaml").write_text(
            "adr:\n  pattern: \"^ADR-(\\\\d{3})-.*\\\\.md$\"\n"
        )
        # Create a 3-digit ADR file matching the pattern
        (rd / "docs" / "adr").mkdir(parents=True, exist_ok=True)
        (rd / "docs" / "adr" / "ADR-040-test.md").write_text("# ADR 040")
        result = wah.write_arch_handoff(
            project_root=str(rd),
            discovered_adr_dir="docs/adr",
        )
        assert "adr_regex" in result, "write_arch_handoff must write adr_regex from project.yaml"
        assert result["adr_regex"] == r"^ADR-(\d{3})-.*\.md$"

    def test_no_adr_regex_when_project_yaml_absent(self, tmp_repo):
        """write_arch_handoff omits adr_regex when no project.yaml (backward compat)."""
        result = wah.write_arch_handoff(
            project_root=str(tmp_repo),
            discovered_adr_dir="docs/adr",
        )
        assert "adr_regex" not in result, (
            "write_arch_handoff must not write adr_regex when project.yaml absent"
        )

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
        """Sets version: 2 (matches v2 schema with adr_regex passthrough)."""
        result = wah.write_arch_handoff(
            project_root=tmp_repo,
            discovered_adr_dir="docs/adr",
            discovered_roadmap_path="roadmap.md",
            discovered_architecture_dir="docs/architecture",
            discovered_adr_pattern="ADR-*.md",
        )
        assert result["version"] == 2

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


class TestWriteArchHandoffLocked:
    """Stage 3 Change 0: FileLock + atomic_write contract per Oracle C-1.

    Locks the migration from bare open(w)+json.dump to FileLock + atomic_write_json.
    Required to support future rdd-planner writing .planner-feedback.json under the
    same lock convention (no torn writes, no clobbering).
    """

    def test_lock_file_is_created_alongside_handoff(self, tmp_repo):
        """Acquires FileLock at .arch-handoff.json.lock (planner_state convention)."""
        from pathlib import Path
        wah.write_arch_handoff(
            project_root=tmp_repo,
            discovered_adr_dir="docs/adr",
            discovered_roadmap_path="roadmap.md",
            discovered_architecture_dir="docs/architecture",
            discovered_adr_pattern="ADR-*.md",
        )
        lock_path = Path(tmp_repo) / ".rddf" / "state" / ".arch-handoff.json.lock"
        assert lock_path.exists(), "FileLock file must be created in .rddf/state/"

    def test_lock_file_is_released_after_write(self, tmp_repo):
        """Lock file is closed (released) after write completes."""
        from pathlib import Path
        from _lib.core.lock import FileLock
        lock_path = Path(tmp_repo) / ".rddf" / "state" / ".arch-handoff.json.lock"
        wah.write_arch_handoff(
            project_root=tmp_repo,
            discovered_adr_dir="docs/adr",
            discovered_roadmap_path="roadmap.md",
            discovered_architecture_dir="docs/architecture",
            discovered_adr_pattern="ADR-*.md",
        )
        with FileLock(str(lock_path), timeout=1.0):
            pass

    def test_write_is_atomic_no_tmp_residue(self, tmp_repo):
        """Writes via tmp + rename (atomic_write_json); no .arch-handoff.json.tmp residue."""
        from pathlib import Path
        wah.write_arch_handoff(
            project_root=tmp_repo,
            discovered_adr_dir="docs/adr",
            discovered_roadmap_path="roadmap.md",
            discovered_architecture_dir="docs/architecture",
            discovered_adr_pattern="ADR-*.md",
        )
        tmp_residue = Path(tmp_repo) / ".rddf" / "state" / ".arch-handoff.json.tmp"
        assert not tmp_residue.exists(), "Atomic write must clean up .tmp file"

    def test_concurrent_writers_no_data_loss(self, tmp_repo):
        """Two concurrent write_arch_handoff calls produce valid JSON without torn writes."""
        results = {}
        errors = []

        def writer(label):
            try:
                r = wah.write_arch_handoff(
                    project_root=tmp_repo,
                    discovered_adr_dir="docs/adr",
                    discovered_roadmap_path="roadmap.md",
                    discovered_architecture_dir="docs/architecture",
                    discovered_adr_pattern="ADR-*.md",
                )
                results[label] = r["adr_count"]
            except Exception as exc:
                errors.append((label, exc))

        t1 = threading.Thread(target=writer, args=("a",))
        t2 = threading.Thread(target=writer, args=("b",))
        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        assert not errors, f"Concurrent writers must not raise: {errors}"
        assert results == {"a": 3, "b": 3}

        from pathlib import Path
        handoff_path = Path(tmp_repo) / ".rddf" / "state" / ".arch-handoff.json"
        with open(handoff_path) as f:
            data = json.load(f)
        assert data["adr_count"] == 3
        assert data["version"] == 2