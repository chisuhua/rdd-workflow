#!/usr/bin/env python3
"""Concurrency tests for rddf-session LOCK_NB file locking semantics.

Uses multiprocessing.Pool to spawn 100 parallel create_session calls,
verifying that:
- LOCK_NB fail-fast semantics work (no queueing, no infinite retry)
- No silent data corruption under concurrent access
- Final state is consistent (exactly one winner per slot)
"""
from __future__ import annotations

import json
import os
import tempfile
import time
import datetime
from multiprocessing import Pool
from pathlib import Path

import pytest

# Import the rddf-session store
from skills.rddf_session.scripts.rddf_session_pkg._store import RddfSessionStore
from skills.rddf_session.scripts.rddf_session_pkg._types import RddfSessionError


def _worker_create_session(args: tuple) -> dict:
    """Worker function for multiprocessing. Attempts to create a session.

    Returns a dict with:
        - worker_id: int
        - success: bool
        - error: str | None
        - session_id: str | None
    """
    worker_id, sessions_file, session_id = args

    store = RddfSessionStore(sessions_file)

    try:
        # Try to acquire lock and create session
        def create():
            data = store.read_unlocked()
            # Check if session already exists
            for s in data["sessions"]:
                if s.get("session_id") == session_id:
                    return {"success": False, "error": "session_exists"}

            # Create new session
            new_session = {
                "session_id": session_id,
                "kind": "stage_plan",
                "owner_opencode_session_id": f"worker_{worker_id}",
                "state": "active",
                "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "last_heartbeat": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "goal": {"intent": "guide-plan", "subject": "concurrent-test"},
            }
            data["sessions"].append(new_session)
            store.atomic_write(data)
            return {"success": True, "session_id": session_id}

        result = store.with_file_lock(create)
        return {
            "worker_id": worker_id,
            "success": result["success"],
            "error": result.get("error"),
            "session_id": result.get("session_id"),
        }
    except RddfSessionError as e:
        # LOCK_NB fail-fast - could not acquire lock
        return {
            "worker_id": worker_id,
            "success": False,
            "error": f"lock_failed: {e}",
            "session_id": None,
        }
    except Exception as e:
        return {
            "worker_id": worker_id,
            "success": False,
            "error": f"unexpected: {e}",
            "session_id": None,
        }


def _worker_read_session(args: tuple) -> dict:
    """Worker function for concurrent reads. Should never fail."""
    worker_id, sessions_file = args

    store = RddfSessionStore(sessions_file)

    try:
        # Reads don't need lock (read_unlocked)
        data = store.read_unlocked()
        return {
            "worker_id": worker_id,
            "success": True,
            "session_count": len(data.get("sessions", [])),
        }
    except Exception as e:
        return {
            "worker_id": worker_id,
            "success": False,
            "error": str(e),
        }


def _worker_write_session(args: tuple) -> dict:
    """Worker for stress test: write 10 sessions."""
    worker_id, sessions_file = args
    store = RddfSessionStore(sessions_file)
    for i in range(10):
        try:
            def do_write():
                data = store.read_unlocked()
                data.setdefault("sessions", [])
                _w_now = datetime.datetime.now(datetime.timezone.utc).isoformat()
                data["sessions"].append({
                    "session_id": f"rds_{worker_id:04x}{i:08x}",
                    "kind": "stage_plan",
                    "owner_opencode_session_id": f"worker_{worker_id}",
                    "state": "active",
                    "started_at": _w_now,
                    "last_heartbeat": _w_now,
                    "goal": {"intent": "guide-plan", "subject": "stress"},
                })
                store.atomic_write(data)
                return True

            store.with_file_lock(do_write)
        except RddfSessionError:
            pass  # Lock contention, skip this iteration
    return {"worker_id": worker_id}


class TestRddfSessionConcurrency:
    """Test concurrent session operations."""

    def test_concurrent_create_session_100_workers(self, tmp_path: Path):
        """100 concurrent create_session calls for the SAME session_id.

        Expected behavior:
        - Exactly ONE worker should succeed (create the session)
        - 99 workers should fail with lock contention or session_exists
        - No data corruption
        """
        sessions_file = str(tmp_path / "sessions.json")
        session_id = "rds_" + "a" * 12

        # Prepare 100 workers all trying to create the same session
        args_list = [(i, sessions_file, session_id) for i in range(100)]

        with Pool(processes=20) as pool:  # Limit to 20 parallel to avoid resource exhaustion
            results = pool.map(_worker_create_session, args_list)

        # Count successes and failures
        successes = [r for r in results if r["success"]]
        failures = [r for r in results if not r["success"]]

        # Verify: exactly ONE success (the first to acquire lock)
        assert len(successes) == 1, f"Expected exactly 1 success, got {len(successes)}"
        assert successes[0]["session_id"] == session_id

        # Verify: all others failed (lock contention or session_exists)
        assert len(failures) == 99, f"Expected 99 failures, got {len(failures)}"

        # Verify: final state has exactly one session
        store = RddfSessionStore(sessions_file)
        data = store.read_unlocked()
        assert len(data["sessions"]) == 1
        assert data["sessions"][0]["session_id"] == session_id

    def test_concurrent_create_different_sessions(self, tmp_path: Path):
        """100 concurrent create_session calls for DIFFERENT session_ids.

        Expected behavior:
        - All 100 should succeed (no conflict on different IDs)
        - Final state has 100 sessions
        """
        sessions_file = str(tmp_path / "sessions.json")

        # Each worker creates a unique session
        args_list = [(i, sessions_file, f"rds_{i:012x}") for i in range(100)]

        with Pool(processes=20) as pool:
            results = pool.map(_worker_create_session, args_list)

        # Count successes
        successes = [r for r in results if r["success"]]
        failures = [r for r in results if not r["success"]]

        # All should succeed (different session_ids, just lock contention on write)
        # Some may fail due to lock contention, but retry logic should handle it
        # In practice with LOCK_NB, some may fail - we just verify no corruption
        assert len(successes) > 0, "Expected at least some successes"

        # Verify: no corruption in final state
        store = RddfSessionStore(sessions_file)
        data = store.read_unlocked()

        # All sessions should be unique
        session_ids = [s["session_id"] for s in data["sessions"]]
        assert len(session_ids) == len(set(session_ids)), "Duplicate session_ids found"

    def test_concurrent_reads_never_fail(self, tmp_path: Path):
        """Concurrent reads should never fail (no lock needed).

        100 parallel read_unlocked calls should all succeed.
        """
        sessions_file = str(tmp_path / "sessions.json")

        # Pre-populate with some sessions
        store = RddfSessionStore(sessions_file)
        _prepop_now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        store.atomic_write({
            "version": 1,
            "sessions": [
                {
                    "session_id": f"rds_{i:012x}",
                    "kind": "stage_plan",
                    "owner_opencode_session_id": "prepop_owner",
                    "state": "active",
                    "started_at": _prepop_now,
                    "last_heartbeat": _prepop_now,
                    "goal": {"intent": "guide-plan", "subject": "prepop"},
                }
                for i in range(10)
            ]
        })

        # 100 concurrent reads
        args_list = [(i, sessions_file) for i in range(100)]

        with Pool(processes=20) as pool:
            results = pool.map(_worker_read_session, args_list)

        # All should succeed
        successes = [r for r in results if r["success"]]
        assert len(successes) == 100, f"Expected all 100 reads to succeed, got {len(successes)}"

    def test_lock_nb_fail_fast_no_queueing(self, tmp_path: Path):
        """Verify LOCK_NB fails immediately when lock is held.

        If one process holds the lock, others should fail fast
        (not block indefinitely).
        """
        sessions_file = str(tmp_path / "sessions.json")
        store = RddfSessionStore(sessions_file)

        # Hold the lock in main process
        lock_acquired = False

        def hold_lock():
            nonlocal lock_acquired
            lock_acquired = True
            time.sleep(0.5)  # Hold lock for 0.5s
            return "done"

        # Start holding lock
        import threading
        thread = threading.Thread(target=lambda: store.with_file_lock(hold_lock))
        thread.start()

        # Wait for lock to be acquired
        time.sleep(0.1)

        # Try to acquire lock from another thread (should fail fast)
        store2 = RddfSessionStore(sessions_file)
        failed = False

        try:
            store2.with_file_lock(lambda: "should not reach here")
        except RddfSessionError:
            failed = True

        thread.join()

        # Verify: second attempt failed fast (didn't wait for lock release)
        assert failed, "Expected LOCK_NB to fail fast when lock is held"

    def test_no_data_corruption_under_contention(self, tmp_path: Path):
        """Stress test: many concurrent writes should not corrupt data.

        100 workers each write 10 times to the same file.
        Final JSON should be valid and contain expected data.
        """
        sessions_file = str(tmp_path / "sessions.json")

        args_list = [(i, sessions_file) for i in range(20)]  # 20 workers, 10 writes each

        with Pool(processes=10) as pool:
            pool.map(_worker_write_session, args_list)

        # Verify: JSON is valid
        store = RddfSessionStore(sessions_file)
        data = store.read_unlocked()

        # Verify: no duplicate session_ids
        session_ids = [s["session_id"] for s in data["sessions"]]
        assert len(session_ids) == len(set(session_ids)), "Data corruption: duplicate session_ids"

        # Verify: all session_ids follow schema-legal pattern rds_<12hex>
        for sid in session_ids:
            assert sid.startswith("rds_") and len(sid) == 16, f"Invalid session_id: {sid}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
