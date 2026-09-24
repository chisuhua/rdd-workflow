"""events_log.py — append/read/archive events.jsonl for guide-orchestrator event bus.

Per feat-guide-orchestrator-session-event-bus (ADR-0055 v3, Oracle + Metis revised).

File: <PROJECT_ROOT>/.rddf/state/events.jsonl (append-only JSONL).
Capacity: 50 MB cap (configurable via RDDF_EVENTS_LOG_MAX_SIZE_MB env var, default 50).
Archive: .rddf/state/events.archive.jsonl (rows beyond `keep` most recent).
Locking: fcntl.flock (POSIX), with a 10s lock timeout. Per fix-events-log-blocking-lock,
        uses retry-with-backoff (LOCK_EX blocking, no LOCK_NB) so concurrent writers
        serialize properly instead of raising BlockingIOError.

Design notes:
- events.jsonl is NEW (does NOT reuse existing event-log.jsonl — that file
  does not exist in real projects per Metis B4 fact check).
- seen_by is intentionally NOT in event rows (no per-owner state in file).
  Per-owner state lives in sessions.json goal.last_seen_offset.
- archive_events(sessions_file=...) resets all active stage_guide
  goal.last_seen_offset to 0 to avoid stale-line-number references
  (Metis B4). sessions_file is optional for backward compatibility.
"""
from __future__ import annotations

import datetime
import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


_LOCK_TIMEOUT = 10.0
_LOCK_RETRY_INTERVAL_S = 0.01  # 10ms between acquire attempts
_id_lock = threading.Lock()
_id_seq = 0

DEFAULT_MAX_SIZE_MB = 50
ARCHIVE_KEEP_DEFAULT = 1000

DEFAULT_HEARTBEAT_INTERVAL_SEC = 300


def get_heartbeat_interval_sec() -> int:
    """Return heartbeat interval in seconds (AC-P2-2-4 / M-HB5).

    Reads RDDF_HEARTBEAT_INTERVAL_SEC env var; falls back to 300s default
    when unset or non-integer.
    """
    raw = os.environ.get("RDDF_HEARTBEAT_INTERVAL_SEC", "")
    if raw.isdigit():
        return int(raw)
    return DEFAULT_HEARTBEAT_INTERVAL_SEC


def _acquire_lock_with_timeout(lockf, timeout: float = _LOCK_TIMEOUT) -> None:
    """Acquire fcntl.flock LOCK_EX with bounded retry (per fix-events-log-blocking-lock).

    Previously used LOCK_EX | LOCK_NB which raised BlockingIOError immediately on
    contention, causing second concurrent writers to lose all events. This helper
    retries LOCK_EX | LOCK_NB (non-blocking) with sleep between attempts until the
    timeout expires, achieving effective serialization across processes.

    Raises EventsLogError if the lock cannot be acquired within `timeout` seconds.
    """
    import fcntl
    deadline = time.monotonic() + timeout
    while True:
        try:
            fcntl.flock(lockf.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except BlockingIOError:
            if time.monotonic() >= deadline:
                raise EventsLogError(
                    f"Could not acquire lock within {timeout:.1f}s"
                )
            time.sleep(_LOCK_RETRY_INTERVAL_S)

# Event types for the workflow event bus
EVENT_TYPES = frozenset({
    "phase_started",
    "phase_completed",
    "phase_failed",
    "phase_heartbeat",
    "guide_intent_detected",
    "guide_routed",
    "user_message",
    "test",  # used by unit tests; not emitted by hooks
})


def _next_id_seq() -> int:
    global _id_seq
    with _id_lock:
        _id_seq += 1
        return _id_seq


class EventsLogError(Exception):
    """Raised on I/O or lock failure."""


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


class EventsLog:
    """JSONL append-only event log for guide-orchestrator event bus."""

    def __init__(self, path: str, max_size_mb: int = DEFAULT_MAX_SIZE_MB):
        self.path = Path(path)
        self.max_size_mb = max_size_mb
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock_path = self.path.with_suffix(".lock")

    # ----- ID generation -----

    def generate_id(self) -> str:
        now = datetime.datetime.now(datetime.timezone.utc)
        seq = _next_id_seq()
        # Include PID + microseconds to avoid cross-process collision when two
        # writers start within the same second and both initialize _id_seq=0.
        pid = os.getpid()
        us = now.strftime("%f")  # microseconds
        return f"evt_{now.strftime('%Y%m%d_%H%M%S')}_{pid}_{us}_{seq:03d}"

    # ----- Recording -----

    def append_event(
        self,
        event_type: str,
        severity: str,
        message: str,
        session_id: str,
        kind: str,
        parent_session_id: Optional[str] = None,
        owner_opencode_session_id: Optional[str] = None,
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Append a new event row. Returns the row as a dict.

        Args:
            event_type: one of EVENT_TYPES
            severity: info | warn | error
            message: human-readable summary
            session_id: rds_xxx (or null)
            kind: stage_arch | stage_design | stage_plan | stage_ship | stage_guide
            parent_session_id: rds_yyy or None
            owner_opencode_session_id: ses_xxx or None
        """
        if event_type not in EVENT_TYPES:
            raise EventsLogError(
                f"Unknown event_type: {event_type}. Must be one of {sorted(EVENT_TYPES)}"
            )
        row = {
            "event_id": self.generate_id(),
            "ts": _now(),
            "event_type": event_type,
            "severity": severity,
            "message": message,
            "context": {
                "session_id": session_id,
                "kind": kind,
                "parent_session_id": parent_session_id,
                "owner_opencode_session_id": owner_opencode_session_id,
            },
        }
        if extra_context:
            row["context"].update(extra_context)
        try:
            with open(self._lock_path, "w") as lockf:
                _acquire_lock_with_timeout(lockf)
                try:
                    with open(self.path, "a", encoding="utf-8") as f:
                        f.write(json.dumps(row, ensure_ascii=False) + "\n")
                finally:
                    import fcntl
                    fcntl.flock(lockf.fileno(), fcntl.LOCK_UN)
        except (OSError, IOError) as e:
            raise EventsLogError(f"Could not append event: {e}") from e
        return row

    # ----- Reading -----

    def read_since(self, offset: int = 0) -> List[Dict[str, Any]]:
        """Return events starting at offset (skip first N lines).

        offset=0 returns all events. offset=2 skips lines 0,1 and returns line 2+.
        Tolerant of malformed lines (skip + continue).
        """
        if not self.path.exists():
            return []
        rows: List[Dict[str, Any]] = []
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                for line_no, raw in enumerate(f, 0):
                    if line_no < offset:
                        continue
                    line = raw.strip()
                    if not line:
                        continue
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue  # best-effort: skip malformed
        except FileNotFoundError:
            return []
        return rows

    def mark_seen(self, event_id: str, owner_opencode_session_id: str) -> bool:
        """Append owner to seen_by array on the matching event row.

        Note: events.jsonl is append-only; this rewrites the file with the
        updated seen_by for the matched event. In current v3 design,
        seen_by is per-row but the polling contract uses goal.last_seen_offset
        in sessions.json instead, so this method is rarely needed.
        """
        if not self.path.exists():
            return False
        rows: List[str] = []
        found = False
        with open(self.path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line:
                    rows.append(raw)
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    rows.append(raw)
                    continue
                if row.get("event_id") == event_id:
                    seen = row.setdefault("seen_by", [])
                    if owner_opencode_session_id not in seen:
                        seen.append(owner_opencode_session_id)
                    found = True
                rows.append(json.dumps(row, ensure_ascii=False) + "\n")
        if not found:
            return False
        try:
            with open(self._lock_path, "w") as lockf:
                _acquire_lock_with_timeout(lockf)
                try:
                    with open(self.path, "w", encoding="utf-8") as f:
                        f.writelines(rows)
                finally:
                    import fcntl
                    fcntl.flock(lockf.fileno(), fcntl.LOCK_UN)
        except (OSError, IOError) as e:
            raise EventsLogError(f"Could not mark seen: {e}") from e
        return True

    # ----- Archive -----

    def current_size_mb(self) -> float:
        if not self.path.exists():
            return 0.0
        return self.path.stat().st_size / (1024 * 1024)

    def check_and_archive(self, keep: int = ARCHIVE_KEEP_DEFAULT) -> int:
        """If size > max_size_mb, archive oldest rows beyond `keep` to .archive.jsonl.

        Returns number of archived rows.
        """
        if self.current_size_mb() < self.max_size_mb:
            return 0
        return archive_events(str(self.path), keep=keep)


def archive_events(
    path: str,
    keep: int = ARCHIVE_KEEP_DEFAULT,
    sessions_file: Optional[str] = None,
) -> int:
    """Move oldest rows beyond `keep` from events.jsonl to events.archive.jsonl.

    Standalone function (not method) for use from CLI / hooks without instantiating.
    If ``sessions_file`` is provided, also reset all active stage_guide sessions'
    ``goal.last_seen_offset`` to 0 after archive (per Metis B4 — line numbers
    shift after archive, so per-owner offsets become stale references).
    """
    p = Path(path)
    if not p.exists():
        return 0
    lock_path = p.with_suffix(".lock")
    archive_path = p.parent / (p.stem + ".archive.jsonl")

    try:
        with open(lock_path, "w") as lockf:
            _acquire_lock_with_timeout(lockf)
            try:
                with open(p, "r", encoding="utf-8") as f:
                    all_lines = [ln for ln in f.readlines() if ln.strip()]
                if len(all_lines) <= keep:
                    return 0
                to_archive = all_lines[:-keep]
                to_keep = all_lines[-keep:]
                # Append to archive
                with open(archive_path, "a", encoding="utf-8") as f:
                    f.writelines(to_archive)
                # Rewrite main file with kept rows
                with open(p, "w", encoding="utf-8") as f:
                    f.writelines(to_keep)
                archived_count = len(to_archive)
            finally:
                import fcntl
                fcntl.flock(lockf.fileno(), fcntl.LOCK_UN)
    except (OSError, IOError) as e:
        raise EventsLogError(f"Could not archive events: {e}") from e

    if sessions_file and archived_count > 0:
        _reset_stage_guide_offsets(sessions_file)
    return archived_count


def _reset_stage_guide_offsets(sessions_file: str) -> int:
    """Reset all active stage_guide sessions' goal.last_seen_offset to 0.

    Called from archive_events() after archive to prevent stale line-number
    references. Returns the number of sessions reset. Tolerates missing or
    malformed sessions_file (best-effort).
    """
    import json as _json
    p = Path(sessions_file)
    if not p.exists():
        return 0
    try:
        data = _json.loads(p.read_text(encoding="utf-8"))
    except (_json.JSONDecodeError, OSError):
        return 0
    sessions = data.get("sessions", [])
    if not isinstance(sessions, list):
        return 0
    reset_count = 0
    for s in sessions:
        if not isinstance(s, dict):
            continue
        if s.get("kind") != "stage_guide":
            continue
        if s.get("state") != "active":
            continue
        goal = s.get("goal")
        if not isinstance(goal, dict):
            continue
        if "last_seen_offset" not in goal:
            continue
        if goal["last_seen_offset"] == 0:
            continue
        goal["last_seen_offset"] = 0
        reset_count += 1
    if reset_count == 0:
        return 0
    try:
        p.write_text(_json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError:
        return 0
    return reset_count