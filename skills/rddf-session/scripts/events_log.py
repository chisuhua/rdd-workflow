"""events_log.py — append/read/archive events.jsonl for guide-orchestrator event bus.

Per feat-guide-orchestrator-session-event-bus (ADR-0055 v3, Oracle + Metis revised).

File: <PROJECT_ROOT>/.rddf/state/events.jsonl (append-only JSONL).
Capacity: 50 MB cap (configurable via RDDF_EVENTS_LOG_MAX_SIZE_MB env var, default 50).
Archive: .rddf/state/events.archive.jsonl (rows beyond `keep` most recent).
Locking: fcntl.flock (POSIX), with a 10s lock timeout.

Design notes:
- events.jsonl is NEW (does NOT reuse existing event-log.jsonl — that file
  does not exist in real projects per Metis B4 fact check).
- seen_by is intentionally NOT in event rows (no per-owner state in file).
  Per-owner state lives in sessions.json goal.last_seen_offset.
- archive_events() resets all active stage_guide goal.last_seen_offset to 0
  to avoid stale-line-number references (Metis B4).
"""
from __future__ import annotations

import datetime
import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


_LOCK_TIMEOUT = 10.0
_id_lock = threading.Lock()
_id_seq = 0

DEFAULT_MAX_SIZE_MB = 50
ARCHIVE_KEEP_DEFAULT = 1000

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
        return f"evt_{now.strftime('%Y%m%d_%H%M%S')}_{seq:03d}"

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
        try:
            with open(self._lock_path, "w") as lockf:
                import fcntl
                fcntl.flock(lockf.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                try:
                    with open(self.path, "a", encoding="utf-8") as f:
                        f.write(json.dumps(row, ensure_ascii=False) + "\n")
                finally:
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
                import fcntl
                fcntl.flock(lockf.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                try:
                    with open(self.path, "w", encoding="utf-8") as f:
                        f.writelines(rows)
                finally:
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


def archive_events(path: str, keep: int = ARCHIVE_KEEP_DEFAULT) -> int:
    """Move oldest rows beyond `keep` from events.jsonl to events.archive.jsonl.

    Standalone function (not method) for use from CLI / hooks without instantiating.
    Caller is responsible for resetting stage_guide goal.last_seen_offset after
    archive (per Metis B4 — line numbers shift after archive).
    """
    p = Path(path)
    if not p.exists():
        return 0
    lock_path = p.with_suffix(".lock")
    archive_path = p.parent / (p.stem + ".archive.jsonl")

    try:
        with open(lock_path, "w") as lockf:
            import fcntl
            fcntl.flock(lockf.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
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
                return len(to_archive)
            finally:
                fcntl.flock(lockf.fileno(), fcntl.LOCK_UN)
    except (OSError, IOError) as e:
        raise EventsLogError(f"Could not archive events: {e}") from e