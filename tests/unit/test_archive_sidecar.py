"""Unit tests for tasks_md sidecar generation (fix-tasks-md-archive-residue).

Verifies the sidecar write + tasks_done derivation helpers that
archive.sh calls at the end of archive_change.
"""
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class TestSidecarHelpers:
    def test_write_sidecar_creates_snapshot(self, tmp_path):
        """write_tasks_md_sidecar copies original tasks.md to .archived-snapshot."""
        from skills._lib.iteration import archive_sidecar as mod

        tasks_md = tmp_path / "tasks.md"
        original = "- [x] 1.1 done\n- [ ] 1.2 todo\n"
        tasks_md.write_text(original)

        mod.write_tasks_md_sidecar(str(tmp_path))

        sidecar = tmp_path / "tasks.md.archived-snapshot"
        assert sidecar.exists()
        assert sidecar.read_text() == original

    def test_write_sidecar_replaces_tasks_md_with_skeleton(self, tmp_path):
        """write_tasks_md_sidecar replaces tasks.md with an archived-skeleton."""
        from skills._lib.iteration import archive_sidecar as mod

        tasks_md = tmp_path / "tasks.md"
        original = "- [x] 1.1 done\n- [ ] 1.2 todo\n"
        tasks_md.write_text(original)

        mod.write_tasks_md_sidecar(str(tmp_path))

        replaced = (tmp_path / "tasks.md").read_text()
        assert "archived" in replaced.lower()
        assert replaced != original

    def test_write_sidecar_idempotent(self, tmp_path):
        """Re-running does not overwrite the sidecar."""
        from skills._lib.iteration import archive_sidecar as mod

        (tmp_path / "tasks.md").write_text("- [x] 1.1\n")
        mod.write_tasks_md_sidecar(str(tmp_path))
        first_content = (tmp_path / "tasks.md.archived-snapshot").read_text()

        # Second call should not overwrite the sidecar
        mod.write_tasks_md_sidecar(str(tmp_path))
        assert (tmp_path / "tasks.md.archived-snapshot").read_text() == first_content

    def test_write_sidecar_no_tasks_md(self, tmp_path):
        """If tasks.md doesn't exist, no sidecar is created (graceful skip)."""
        from skills._lib.iteration import archive_sidecar as mod

        # No tasks.md in tmp_path
        mod.write_tasks_md_sidecar(str(tmp_path))
        assert not (tmp_path / "tasks.md.archived-snapshot").exists()


class TestTasksDoneDerivation:
    def test_count_done_from_markdown(self):
        """Count [x] and [X] in a tasks.md string."""
        from skills._lib.iteration import archive_sidecar as mod

        text = "- [x] 1.1\n- [X] 1.2\n- [ ] 1.3\n- [x] 1.4\n"
        assert mod.count_done_tasks(text) == 3

    def test_count_done_empty(self):
        from skills._lib.iteration import archive_sidecar as mod
        assert mod.count_done_tasks("") == 0
        assert mod.count_done_tasks("no checkboxes here") == 0
