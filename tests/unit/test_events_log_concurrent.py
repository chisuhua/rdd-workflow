"""Tests for events_log.py concurrent lock behavior (fix-events-log-blocking-lock).

Per fix-events-log-blocking-lock AC-5 / AC-6:
- Two real subprocess Python processes concurrently write to events.jsonl
- All events must be persisted (no BlockingIOError)
- Lock timeout (10s) raises EventsLogError if acquisition fails

Replaces the old `LOCK_EX | LOCK_NB` (non-blocking) with a 10s timeout
retry loop so concurrent writers serialize properly.
"""
from __future__ import annotations

import json
import multiprocessing
import os
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
from pathlib import Path

import pytest

from skills.rddf_session.scripts.events_log import (
    DEFAULT_MAX_SIZE_MB,
    EventsLog,
    EventsLogError,
)


def _child_writer(entries_count: int, events_path: str, ready_event, start_event):
    """Child process target: wait for start signal, then write N events."""
    import fcntl
    import time as _time
    from skills.rddf_session.scripts.events_log import EventsLog

    log = EventsLog(events_path)
    ready_event.set()
    start_event.wait(timeout=30)
    for i in range(entries_count):
        log.append_event(
            event_type="test", severity="info", message=f"c{os.getpid()}-{i}",
            session_id=f"rds_{i}", kind="stage_arch",
            parent_session_id=None, owner_opencode_session_id=f"OWNER_{os.getpid()}",
        )
    return entries_count


def test_concurrent_writers_no_loss(tmp_path: Path):
    """AC-5: 2 subprocess writers × 50 events → 100 total events (no BlockingIOError).

    Before fix: LOCK_NB raised BlockingIOError → second writer lost all events.
    After fix: 10s timeout retry serializes writes → all 100 events preserved.

    Note: We check total line count, not unique event_id count, because
    generate_id() uses a process-local _id_seq counter (cross-process collision
    is a separate issue tracked as fix-events-log-id-collision, out of scope
    for this fix).
    """
    events_path = str(tmp_path / "events.jsonl")

    # Use multiprocessing primitives for cross-process coordination
    ready_a = multiprocessing.Event()
    ready_b = multiprocessing.Event()
    start = multiprocessing.Event()

    proc_a = multiprocessing.Process(
        target=_child_writer,
        args=(50, events_path, ready_a, start),
    )
    proc_b = multiprocessing.Process(
        target=_child_writer,
        args=(50, events_path, ready_b, start),
    )
    proc_a.start()
    proc_b.start()

    # Wait for both children to be ready, then release them simultaneously
    assert ready_a.wait(timeout=10), "child A never signaled ready"
    assert ready_b.wait(timeout=10), "child B never signaled ready"
    start.set()

    proc_a.join(timeout=30)
    proc_b.join(timeout=30)

    # Both processes must have exited cleanly (no exception)
    assert proc_a.exitcode == 0, f"child A exited with {proc_a.exitcode}"
    assert proc_b.exitcode == 0, f"child B exited with {proc_b.exitcode}"

    # Count total events — should be exactly 100 (50 + 50, no BlockingIOError loss)
    lines = [l for l in Path(events_path).read_text().split("\n") if l.strip()]
    assert len(lines) == 100, f"expected 100 events, got {len(lines)}"

    # Verify messages from BOTH child processes are present (proves both wrote)
    from_pid_a = sum(1 for l in lines if f"c{proc_a.pid}-" in l)
    from_pid_b = sum(1 for l in lines if f"c{proc_b.pid}-" in l)
    assert from_pid_a >= 1, f"no events from child A (pid={proc_a.pid})"
    assert from_pid_b >= 1, f"no events from child B (pid={proc_b.pid})"
    assert from_pid_a + from_pid_b == 100, (
        f"expected 100 events total, got {from_pid_a} from A + {from_pid_b} from B"
    )


def test_lock_timeout_raises_events_log_error(tmp_path: Path):
    """AC-4: lock acquisition beyond 10s raises EventsLogError.

    Hold lock in a child process; main process attempts append_event;
    after 10s timeout, EventsLogError is raised (not bare BlockingIOError).
    """
    events_path = str(tmp_path / "events.jsonl")
    # Pre-create the file so lock_path exists
    Path(events_path).touch()

    # Spawn child that holds lock indefinitely
    holder = multiprocessing.Process(
        target=_hold_lock_forever,
        args=(events_path,),
    )
    holder.start()
    time.sleep(1)  # let child acquire lock

    # Main process tries to write — should timeout after ~10s and raise
    log = EventsLog(events_path)
    t0 = time.monotonic()
    with pytest.raises(EventsLogError, match="Could not acquire lock within"):
        log.append_event(
            event_type="test", severity="info", message="will-fail",
            session_id="rds_x", kind="stage_arch",
            parent_session_id=None, owner_opencode_session_id="OWNER_X",
        )
    elapsed = time.monotonic() - t0

    # Should have waited approximately the timeout (10s), not less
    assert 9.0 <= elapsed <= 12.0, f"timeout took {elapsed:.2f}s, expected ~10s"

    # Cleanup
    holder.terminate()
    holder.join(timeout=5)


def _hold_lock_forever(events_path: str):
    """Child target: acquire fcntl lock and never release."""
    import fcntl
    # Match EventsLog._lock_path: self.path.with_suffix(".lock")
    from pathlib import Path
    lock_path = str(Path(events_path).with_suffix(".lock"))
    with open(lock_path, "w") as lockf:
        fcntl.flock(lockf.fileno(), fcntl.LOCK_EX)
        time.sleep(60)  # hold for 60s


def test_single_process_still_works(tmp_path: Path):
    """Regression: single-process append_event still works after lock fix."""
    log = EventsLog(str(tmp_path / "events.jsonl"))
    for i in range(5):
        log.append_event(
            event_type="test", severity="info", message=f"e-{i}",
            session_id=f"rds_{i}", kind="stage_arch",
            parent_session_id=None, owner_opencode_session_id="OWNER",
        )
    rows = log.read_since(offset=0)
    assert len(rows) == 5


def test_event_id_unique_across_processes(tmp_path: Path):
    """Regression: generate_id must include PID/microseconds for cross-process uniqueness.

    Before fix: two processes with _id_seq=0 generated identical event_ids.
    After fix: PID + microseconds differentiate.
    """
    def _gen_in_child(ready_event, results_list):
        from skills.rddf_session.scripts.events_log import EventsLog
        log = EventsLog(str(tmp_path / "events.jsonl"))
        ids = [log.generate_id() for _ in range(20)]
        results_list.extend(ids)
        ready_event.set()

    from multiprocessing import Manager
    with Manager() as manager:
        ready_a = manager.Event()
        ready_b = manager.Event()
        results_a = manager.list()
        results_b = manager.list()
        proc_a = multiprocessing.Process(
            target=_gen_in_child, args=(ready_a, results_a)
        )
        proc_b = multiprocessing.Process(
            target=_gen_in_child, args=(ready_b, results_b)
        )
        proc_a.start()
        proc_b.start()
        proc_a.join(timeout=10)
        proc_b.join(timeout=10)

        all_ids = list(results_a) + list(results_b)
        assert len(all_ids) == 40
        assert len(set(all_ids)) == 40, (
            f"event_ids collide across processes; "
            f"got {len(set(all_ids))} unique out of 40"
        )
