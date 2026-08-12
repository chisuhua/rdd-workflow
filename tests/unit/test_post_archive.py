"""Unit tests for post_archive helper.

TDD Step 1: Write failing tests (red).
After implementation, all these should pass (green).
"""
import json
import sys
from pathlib import Path

# Allow imports from project root
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from skills._lib.iteration import post_archive  # noqa: E402
from skills._lib.iteration import store  # noqa: E402


def _seed_iteration(project_root: Path, changes: list[dict]) -> Path:
    """Write a minimal valid iteration.json to .rddf/state/."""
    state_dir = project_root / ".rddf" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    iter_path = state_dir / "iteration.json"
    data = {
        "version": 4,
        "updated_at": "2026-08-05T10:00:00+00:00",
        "current_phase": "default",
        "changes": changes,
    }
    iter_path.write_text(json.dumps(data, indent=2))
    return iter_path


def _read_iteration(project_root: Path) -> dict:
    return json.loads((project_root / ".rddf" / "state" / "iteration.json").read_text())


class TestSyncAfterArchive:
    """TDD tests for sync_iteration_after_archive."""

    def test_writes_archived_at_on_pending_change(self, tmp_path):
        """GIVEN a change with status='proposed' AND no archived_at
        WHEN sync_iteration_after_archive is called
        THEN status → 'archived' AND archived_at is set."""
        _seed_iteration(tmp_path, [
            {"name": "test-change", "status": "proposed",
             "added_at": "2026-08-01T00:00:00+00:00",
             "plan_path": ".rddf/plans/test-change.md"}
        ])

        result = post_archive.sync_iteration_after_archive(
            project_root=str(tmp_path),
            change_name="test-change",
            archive_commit_sha="abc123",
        )

        assert result is None  # No warning
        data = _read_iteration(tmp_path)
        c = data["changes"][0]
        assert c["status"] == "archived"
        assert "archived_at" in c
        assert c["archived_at"]  # ISO timestamp populated

    def test_idempotent_preserves_existing_archived_at(self, tmp_path):
        """GIVEN a change already archived_at='2026-07-01T00:00:00'
        WHEN sync_iteration_after_archive is called again
        THEN archived_at is NOT overwritten (stays 2026-07-01)."""
        original_ts = "2026-07-01T00:00:00+00:00"
        _seed_iteration(tmp_path, [
            {"name": "test-change", "status": "archived",
             "added_at": "2026-06-01T00:00:00+00:00",
             "archived_at": original_ts,
             "plan_path": ".rddf/plans/test-change.md"}
        ])

        result = post_archive.sync_iteration_after_archive(
            project_root=str(tmp_path),
            change_name="test-change",
            archive_commit_sha="abc123",
        )

        assert result is None
        data = _read_iteration(tmp_path)
        c = data["changes"][0]
        assert c["archived_at"] == original_ts  # NOT overwritten

    def test_writes_archive_commit_sha(self, tmp_path):
        """GIVEN a change with no archive_commit_sha
        WHEN sync_iteration_after_archive is called with sha=abc123
        THEN archive_commit_sha='abc123' is set."""
        _seed_iteration(tmp_path, [
            {"name": "test-change", "status": "proposed",
             "added_at": "2026-08-01T00:00:00+00:00"}
        ])

        post_archive.sync_iteration_after_archive(
            project_root=str(tmp_path),
            change_name="test-change",
            archive_commit_sha="abc123",
        )

        data = _read_iteration(tmp_path)
        assert data["changes"][0]["archive_commit_sha"] == "abc123"

    def test_idempotent_preserves_existing_archive_commit_sha(self, tmp_path):
        """GIVEN a change already archive_commit_sha='old_sha'
        WHEN sync_iteration_after_archive is called with new sha
        THEN archive_commit_sha is NOT overwritten (stays old_sha)."""
        _seed_iteration(tmp_path, [
            {"name": "test-change", "status": "archived",
             "added_at": "2026-08-01T00:00:00+00:00",
             "archive_commit_sha": "old_sha"}
        ])

        post_archive.sync_iteration_after_archive(
            project_root=str(tmp_path),
            change_name="test-change",
            archive_commit_sha="new_sha",
        )

        data = _read_iteration(tmp_path)
        assert data["changes"][0]["archive_commit_sha"] == "old_sha"

    def test_writes_tasks_done_from_archive_tasks_md(self, tmp_path):
        """GIVEN a change with tasks.md in archive/ with [x] count
        WHEN sync_iteration_after_archive is called
        THEN tasks_done is set to the count of [x] in archive tasks.md."""
        # Create archive directory with tasks.md
        archive_dir = tmp_path / "openspec" / "changes" / "archive" / "2026-08-05-test-change"
        archive_dir.mkdir(parents=True)
        (archive_dir / "tasks.md").write_text(
            "# Tasks\n"
            "- [ ] 1.1 task one\n"
            "- [x] 1.2 task two\n"
            "- [x] 1.3 task three\n"
            "- [x] 1.4 task four\n"
        )
        _seed_iteration(tmp_path, [
            {"name": "test-change", "status": "proposed",
             "added_at": "2026-08-01T00:00:00+00:00"}
        ])

        post_archive.sync_iteration_after_archive(
            project_root=str(tmp_path),
            change_name="test-change",
            archive_commit_sha="abc123",
        )

        data = _read_iteration(tmp_path)
        assert data["changes"][0]["tasks_done"] == 3

    def test_writes_plan_path(self, tmp_path):
        """GIVEN a change with no plan_path
        WHEN sync_iteration_after_archive is called
        THEN plan_path is set to .rddf/plans/<name>.md."""
        _seed_iteration(tmp_path, [
            {"name": "test-change", "status": "proposed",
             "added_at": "2026-08-01T00:00:00+00:00"}
        ])

        post_archive.sync_iteration_after_archive(
            project_root=str(tmp_path),
            change_name="test-change",
            archive_commit_sha="abc123",
        )

        data = _read_iteration(tmp_path)
        assert data["changes"][0]["plan_path"] == ".rddf/plans/test-change.md"

    def test_returns_warning_when_change_not_found(self, tmp_path):
        """GIVEN iteration.json without a matching change
        WHEN sync_iteration_after_archive is called
        THEN returns a warning string AND does NOT raise."""
        _seed_iteration(tmp_path, [
            {"name": "other-change", "status": "proposed",
             "added_at": "2026-08-01T00:00:00+00:00"}
        ])

        result = post_archive.sync_iteration_after_archive(
            project_root=str(tmp_path),
            change_name="missing-change",
            archive_commit_sha="abc123",
        )

        assert result is not None  # Warning returned
        assert isinstance(result, str)
        assert "missing-change" in result

    def test_no_op_when_iteration_missing(self, tmp_path):
        """GIVEN no .rddf/state/iteration.json
        WHEN sync_iteration_after_archive is called
        THEN returns a warning AND does NOT raise."""
        # No iteration.json created
        result = post_archive.sync_iteration_after_archive(
            project_root=str(tmp_path),
            change_name="any-change",
            archive_commit_sha="abc123",
        )

        assert result is not None
        assert "iteration.json" in result.lower() or "not found" in result.lower()

    def test_does_not_block_on_corrupt_iteration(self, tmp_path):
        """GIVEN a schema-invalid iteration.json
        WHEN sync_iteration_after_archive is called
        THEN returns a warning AND does NOT raise (fail open)."""
        state_dir = tmp_path / ".rddf" / "state"
        state_dir.mkdir(parents=True)
        (state_dir / "iteration.json").write_text(
            '{"version": 4, "changes": [{"name": "x", "status": "not_in_enum", "added_at": "2026-08-01T00:00:00+00:00"}], "current_phase": "default", "updated_at": "2026-08-01T00:00:00+00:00"}'
        )

        result = post_archive.sync_iteration_after_archive(
            project_root=str(tmp_path),
            change_name="x",
            archive_commit_sha="abc123",
        )

        # Should return warning, not raise
        assert result is not None
        assert isinstance(result, str)


class TestCountDoneTasks:
    """Tests for the count_done_tasks helper for archive tasks.md."""

    def test_counts_done_checkboxes(self, tmp_path):
        """Counts '- [x]' markers, ignoring '- [ ]'."""
        tasks = tmp_path / "tasks.md"
        tasks.write_text(
            "# Tasks\n"
            "- [x] 1.1 done\n"
            "- [x] 1.2 done\n"
            "- [ ] 1.3 todo\n"
            "- [x] 1.4 done\n"
        )
        assert post_archive.count_done_tasks(str(tasks)) == 3

    def test_returns_zero_for_missing_file(self, tmp_path):
        tasks = tmp_path / "missing.md"
        assert post_archive.count_done_tasks(str(tasks)) == 0

    def test_handles_uppercase_x(self, tmp_path):
        """BOTH [x] and [X] should be counted (case-insensitive)."""
        tasks = tmp_path / "tasks.md"
        tasks.write_text(
            "- [x] 1.1\n"
            "- [X] 1.2\n"
            "- [x] 1.3\n"
        )
        assert post_archive.count_done_tasks(str(tasks)) == 3
