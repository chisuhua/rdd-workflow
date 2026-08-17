"""Tests for skills._lib.iteration.repair module."""
import json
from pathlib import Path

from skills._lib.iteration import repair


def test_force_mark_archived_writes_iteration(tmp_path: Path) -> None:
    """force_mark_archived writes status=archived + archived_at to iteration.json."""
    project_root = tmp_path
    rddf = project_root / ".rddf" / "state"
    rddf.mkdir(parents=True)
    iter_file = rddf / "iteration.json"
    iter_file.write_text(json.dumps({
        "version": 7,
        "changes": [
            {"name": "test-change", "status": "planned", "added_at": "2026-01-01T00:00:00Z"}
        ]
    }))
    archive_dir = project_root / "openspec" / "changes" / "archive" / "2026-08-16-test-change"
    archive_dir.mkdir(parents=True)
    (archive_dir / "proposal.md").write_text("# test")

    modified = repair.force_mark_archived(str(project_root), "test-change")

    assert modified is True
    data = json.loads(iter_file.read_text())
    entry = next(c for c in data["changes"] if c["name"] == "test-change")
    assert entry["status"] == "archived"
    assert "archived_at" in entry


def test_force_mark_archived_skips_when_no_archive_dir(tmp_path: Path) -> None:
    """force_mark_archived is a no-op when archive dir doesn't exist."""
    project_root = tmp_path
    rddf = project_root / ".rddf" / "state"
    rddf.mkdir(parents=True)
    iter_file = rddf / "iteration.json"
    iter_file.write_text(json.dumps({
        "version": 7,
        "changes": [{"name": "ghost", "status": "planned", "added_at": "2026-01-01T00:00:00Z"}]
    }))

    modified = repair.force_mark_archived(str(project_root), "ghost")

    assert modified is False
    data = json.loads(iter_file.read_text())
    entry = data["changes"][0]
    assert entry["status"] == "planned"


def test_force_mark_archived_idempotent(tmp_path: Path) -> None:
    """Second call after first is a no-op (no second modification)."""
    project_root = tmp_path
    rddf = project_root / ".rddf" / "state"
    rddf.mkdir(parents=True)
    iter_file = rddf / "iteration.json"
    iter_file.write_text(json.dumps({
        "version": 7,
        "changes": [{"name": "test-change", "status": "planned", "added_at": "2026-01-01T00:00:00Z"}]
    }))
    archive_dir = project_root / "openspec" / "changes" / "archive" / "2026-08-16-test-change"
    archive_dir.mkdir(parents=True)

    r1 = repair.force_mark_archived(str(project_root), "test-change")
    r2 = repair.force_mark_archived(str(project_root), "test-change")

    assert r1 is True
    assert r2 is False