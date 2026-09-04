"""Tests for atomic lifecycle ops in planner_feedback (Wave 4 Sub-task 1.1).

P0-2 fix: 4 ops (acknowledge/resolve/dismiss/prune) move from
read-outside-lck + write-inside-lck (TOCTOU) to read+modify+write
inside a single FileLock critical section.

R2 fix: FileLock is fcntl.flock per-fd, non-reentrant. The critical
section MUST only call `_write_planner_feedback_unlocked` and
`read_planner_feedback_unlocked` — NEVER `write_planner_feedback`
or `read_planner_feedback` (which themselves take the lock).
"""
from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest


def _setup_feedback_with_one_entry(tmp_path: Path, *, status: str = "open") -> str:
    """Create .planner-feedback.json with 1 open feedback entry."""
    project_root = str(tmp_path)
    state_dir = tmp_path / ".rddf" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)

    data = {
        "schema": "planner-feedback-v1",
        "version": 1,
        "owner": "rdd-planner",
        "branch": "master",
        "worktree_root": project_root,
        "codebase_commit": "",
        "arch_handoff_revision": 0,
        "state_revision": 0,
        "planner_state_last_sync_at": "2026-09-03T10:00:00+00:00",
        "feedbacks": [
            {
                "feedback_id": "pf-20260903-001",
                "kind": "unmapped_proposal",
                "severity": "critical",
                "status": status,
                "fingerprint": "abc123def4567890",
                "proposal": "feat-x",
                "theme": "",
                "related_adr_ids": [],
                "message": "...",
                "suggested_action": "...",
                "created_at": "2026-09-03T10:00:00+00:00",
                "last_seen_at": "2026-09-03T10:00:00+00:00",
                "acknowledged_at": None,
                "resolved_at": None,
                "resolved_by": None,
                "dismissed_at": None,
                "dismissed_by": None,
                "computed_from": {
                    "state_revision": 0,
                    "arch_handoff_revision": 0,
                    "codebase_commit": "",
                },
                "stale": False,
            }
        ],
        "summary": {"open_critical": 1, "open_warning": 0, "open_info": 0,
                    "acknowledged": 0, "resolved": 0, "dismissed": 0},
    }
    if status != "open":
        data["summary"] = {"open_critical": 0, "open_warning": 0, "open_info": 0,
                           "acknowledged": 0, "resolved": 0, "dismissed": 0}
        if status == "resolved":
            data["feedbacks"][0]["resolved_at"] = "2026-09-03T10:00:00+00:00"
            data["feedbacks"][0]["resolved_by"] = "architect"
            data["summary"]["resolved"] = 1
        elif status == "dismissed":
            data["feedbacks"][0]["dismissed_at"] = "2026-09-03T10:00:00+00:00"
            data["feedbacks"][0]["dismissed_by"] = "architect"
            data["summary"]["dismissed"] = 1

    (state_dir / ".planner-feedback.json").write_text(json.dumps(data))
    return project_root


def test_acknowledge_atomic_under_lock(tmp_path: Path):
    """50 threads concurrent acknowledge same ID → final status=acknowledged."""
    project_root = _setup_feedback_with_one_entry(tmp_path)

    from _lib.planner_feedback import acknowledge_feedback
    with ThreadPoolExecutor(max_workers=50) as pool:
        futures = [pool.submit(acknowledge_feedback, project_root, "pf-20260903-001")
                   for _ in range(50)]
        for f in futures:
            f.result()

    data = json.loads((tmp_path / ".rddf" / "state" / ".planner-feedback.json").read_text())
    assert data["feedbacks"][0]["status"] == "acknowledged"
    assert data["feedbacks"][0]["acknowledged_at"] is not None


def test_resolve_atomic_under_lock(tmp_path: Path):
    """50 threads concurrent resolve same ID → final status=resolved."""
    project_root = _setup_feedback_with_one_entry(tmp_path, status="acknowledged")

    from _lib.planner_feedback import resolve_feedback
    with ThreadPoolExecutor(max_workers=50) as pool:
        futures = [pool.submit(resolve_feedback, project_root, "pf-20260903-001")
                   for _ in range(50)]
        for f in futures:
            f.result()

    data = json.loads((tmp_path / ".rddf" / "state" / ".planner-feedback.json").read_text())
    assert data["feedbacks"][0]["status"] == "resolved"
    assert data["feedbacks"][0]["resolved_at"] is not None


def test_dismiss_atomic_under_lock(tmp_path: Path):
    """50 threads concurrent dismiss same ID → final status=dismissed."""
    project_root = _setup_feedback_with_one_entry(tmp_path, status="acknowledged")

    from _lib.planner_feedback import dismiss_feedback
    with ThreadPoolExecutor(max_workers=50) as pool:
        futures = [pool.submit(dismiss_feedback, project_root, "pf-20260903-001")
                   for _ in range(50)]
        for f in futures:
            f.result()

    data = json.loads((tmp_path / ".rddf" / "state" / ".planner-feedback.json").read_text())
    assert data["feedbacks"][0]["status"] == "dismissed"
    assert data["feedbacks"][0]["dismissed_at"] is not None


def test_prune_resolved_atomic_under_lock(tmp_path: Path):
    """50 threads concurrent prune → all resolved/dismissed removed."""
    project_root = _setup_feedback_with_one_entry(tmp_path, status="resolved")

    from _lib.planner_feedback import prune_resolved_feedback
    with ThreadPoolExecutor(max_workers=50) as pool:
        futures = [pool.submit(prune_resolved_feedback, project_root) for _ in range(50)]
        for f in futures:
            f.result()

    data = json.loads((tmp_path / ".rddf" / "state" / ".planner-feedback.json").read_text())
    assert data["feedbacks"] == []


def test_concurrent_ack_and_resolve_no_lost_update(tmp_path: Path):
    """Mixed ack + resolve threads → final state consistent (no torn write)."""
    project_root = _setup_feedback_with_one_entry(tmp_path)

    from _lib.planner_feedback import acknowledge_feedback, resolve_feedback

    def _ack():
        acknowledge_feedback(project_root, "pf-20260903-001")

    def _resolve():
        resolve_feedback(project_root, "pf-20260903-001")

    ops = [_ack] * 25 + [_resolve] * 25
    with ThreadPoolExecutor(max_workers=50) as pool:
        futures = [pool.submit(op) for op in ops]
        for f in futures:
            f.result()

    data = json.loads((tmp_path / ".rddf" / "state" / ".planner-feedback.json").read_text())
    final_status = data["feedbacks"][0]["status"]
    # Final status must be one of the valid lifecycle states (no torn write)
    assert final_status in ("acknowledged", "resolved")


def test_no_nested_lock_deadlock(tmp_path: Path):
    """Lifecycle ops complete in < 1s each (no nested-lock LockTimeout deadlock)."""
    project_root = _setup_feedback_with_one_entry(tmp_path)

    from _lib.planner_feedback import (
        acknowledge_feedback, resolve_feedback,
        dismiss_feedback, prune_resolved_feedback,
    )

    start = time.time()
    acknowledge_feedback(project_root, "pf-20260903-001")
    elapsed = time.time() - start
    assert elapsed < 1.0, f"acknowledge took {elapsed:.2f}s (nested lock?)"

    start = time.time()
    resolve_feedback(project_root, "pf-20260903-001")
    elapsed = time.time() - start
    assert elapsed < 1.0, f"resolve took {elapsed:.2f}s (nested lock?)"

    start = time.time()
    dismiss_feedback(project_root, "pf-20260903-001")  # dismissed (from resolved is no-op)
    elapsed = time.time() - start
    assert elapsed < 1.0, f"dismiss took {elapsed:.2f}s (nested lock?)"

    start = time.time()
    prune_resolved_feedback(project_root)
    elapsed = time.time() - start
    assert elapsed < 1.0, f"prune took {elapsed:.2f}s (nested lock?)"


def test_unlocked_helpers_exist_and_work(tmp_path: Path):
    """_write_planner_feedback_unlocked + read_planner_feedback_unlocked exist (R2 critical)."""
    from _lib import planner_feedback
    assert hasattr(planner_feedback, "_write_planner_feedback_unlocked")
    assert hasattr(planner_feedback, "read_planner_feedback_unlocked")

    project_root = str(tmp_path)
    state_dir = tmp_path / ".rddf" / "state"
    state_dir.mkdir(parents=True)

    data = {"schema": "planner-feedback-v1", "feedbacks": [], "summary": {}}
    planner_feedback._write_planner_feedback_unlocked(project_root, data)
    loaded = planner_feedback.read_planner_feedback_unlocked(project_root)
    assert loaded["feedbacks"] == []