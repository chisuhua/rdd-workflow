"""Test that mark_iteration_archived preserves verification field.

Per fix-rdd-verifier-lifecycle-dashboard Task 15:
- mark_iteration_archived must preserve verification object
- Only adds archived_at and (conditionally) archive_commit_sha
- Does NOT touch .rddf/state/verifier/, .ac-verdict-<change>.json, or audit log
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from skills._lib.iteration import post_archive  # noqa: E402

sync_iteration_after_archive = post_archive.sync_iteration_after_archive


def _setup_state(tmp_path: Path, change: dict) -> None:
    state_dir = tmp_path / ".rddf" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    doc = {"version": 7, "updated_at": "2026-08-26T00:00:00Z",
           "current_phase": "v2.1", "changes": [change]}
    (state_dir / "iteration.json").write_text(json.dumps(doc))


def test_archive_preserves_verification_field(tmp_path):
    _setup_state(tmp_path, {
        "name": "ch-x", "status": "in_worktree",
        "tasks_done": 1, "tasks_total": 1,
        "verification": {"state": "passed", "verdict_sha": "abc123",
                         "archive_ready": True, "checked_at": "2026-08-26T00:00:00Z"}
    })
    warning = sync_iteration_after_archive(str(tmp_path), "ch-x",
                                            archive_commit_sha="deadbeef")
    assert warning is None

    doc = json.loads((tmp_path / ".rddf/state/iteration.json").read_text())
    ch = doc["changes"][0]
    assert ch["status"] == "archived"
    assert ch["verification"]["state"] == "passed"
    assert ch["verification"]["verdict_sha"] == "abc123"
    assert ch["verification"]["archive_ready"] is True
    assert ch.get("archived_at") is not None


def test_archive_preserves_audit_log_and_cache(tmp_path):
    """Per design decision #9: archive MUST NOT touch verifier state files."""
    _setup_state(tmp_path, {
        "name": "ch-y", "status": "in_worktree",
        "tasks_done": 1, "tasks_total": 1,
        "verification": {"state": "passed", "archive_ready": True}
    })

    verifier_dir = tmp_path / ".rddf" / "state" / "verifier"
    verifier_dir.mkdir(parents=True, exist_ok=True)
    audit = verifier_dir / "ch-y.audit.jsonl"
    audit.write_text('{"ts": "2026-08-25T00:00:00Z", "event": "running"}\n')
    cache = tmp_path / ".rddf" / "state" / ".ac-verdict-ch-y.json"
    cache.write_text('{"schema_version": 2, "verification_state": "passed"}')

    sync_iteration_after_archive(str(tmp_path), "ch-y")

    assert audit.is_file(), "audit log must be preserved"
    assert cache.is_file(), "verdict cache must be preserved"


def test_archive_idempotent_on_second_run(tmp_path):
    _setup_state(tmp_path, {
        "name": "ch-z", "status": "completed",
        "tasks_done": 1, "tasks_total": 1,
        "verification": {"state": "passed", "archive_ready": True}
    })
    sync_iteration_after_archive(str(tmp_path), "ch-z",
                                   archive_commit_sha="sha1")
    first_doc = json.loads((tmp_path / ".rddf/state/iteration.json").read_text())
    first_archived_at = first_doc["changes"][0]["archived_at"]
    first_sha = first_doc["changes"][0].get("archive_commit_sha")

    sync_iteration_after_archive(str(tmp_path), "ch-z",
                                   archive_commit_sha="sha2")
    second_doc = json.loads((tmp_path / ".rddf/state/iteration.json").read_text())
    assert second_doc["changes"][0]["archived_at"] == first_archived_at
    assert second_doc["changes"][0].get("archive_commit_sha") == first_sha
    assert second_doc["changes"][0]["verification"]["state"] == "passed"
