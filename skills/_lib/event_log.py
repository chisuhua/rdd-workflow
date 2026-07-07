"""Append-only JSONL event log with query API and progress reports.

Stored at `.rddf/state/event-log.jsonl`. Each line is one event. Writes
are protected by a file lock for safety. The log is read on every query;
for 10K+ events the read is < 100ms (see test_query_10k_events_under_100ms).

Event ID format: `evt_YYYYMMDD_HHMMSS_NNN` where NNN is a per-process
sequence counter to guarantee uniqueness even within the same second.
"""
from __future__ import annotations
import datetime
import json
import os
import threading
from pathlib import Path
from typing import Iterable, Optional, Union

from skills._lib.event_types import Event, EventType, Severity
from skills._lib.lock import FileLock, LockTimeout


_LOCK_TIMEOUT = 10.0
_id_lock = threading.Lock()
_id_seq = 0


class EventLogError(Exception):
    """Raised on I/O or lock failure."""


def _next_id_seq() -> int:
    global _id_seq
    with _id_lock:
        _id_seq += 1
        return _id_seq


class EventLog:
    """JSONL event log at `path`."""

    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)

    # ----- ID generation -----------------------------------------------

    def generate_id(self) -> str:
        """Return a new unique event ID: `evt_YYYYMMDD_HHMMSS_NNN`."""
        now = datetime.datetime.now(datetime.timezone.utc)
        seq = _next_id_seq()
        return f"evt_{now.strftime('%Y%m%d_%H%M%S')}_{seq:03d}"

    # ----- Recording ----------------------------------------------------

    def record(
        self,
        event_type: Union[EventType, str],
        severity: Union[Severity, str],
        message: str,
        context: Optional[dict] = None,
        metadata: Optional[dict] = None,
        generate_id: bool = True,
    ) -> Event:
        """Append a new event. Returns the recorded Event."""
        if isinstance(event_type, str):
            event_type = EventType(event_type)
        if isinstance(severity, str):
            severity = Severity(severity)
        event = Event(
            event_type=event_type,
            severity=severity,
            message=message,
            id=self.generate_id() if generate_id else "",
            context=context or {},
            metadata=metadata or {},
        )
        try:
            with FileLock(self.path + ".lock", timeout=_LOCK_TIMEOUT):
                with open(self.path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(event.to_dict(), ensure_ascii=False))
                    f.write("\n")
        except LockTimeout as e:
            raise EventLogError(f"Could not acquire lock to write event: {e}") from e
        return event

    # ----- Query --------------------------------------------------------

    def query(
        self,
        event_type: Optional[Union[EventType, str]] = None,
        severity: Optional[Union[Severity, str]] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[Event]:
        """Read all events matching the filter. Returns chronologically-ordered Events."""
        if isinstance(event_type, str):
            event_type = EventType(event_type)
        if isinstance(severity, str):
            severity = Severity(severity)

        if not os.path.exists(self.path):
            return []

        results: list[Event] = []
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    event = Event.from_dict(d)
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue  # skip corrupt lines
                if event_type and event.event_type != event_type:
                    continue
                if severity and event.severity != severity:
                    continue
                if since and event.timestamp < since:
                    continue
                if until and event.timestamp > until:
                    continue
                results.append(event)
                if limit and len(results) >= limit:
                    break
        return results

    # ----- Aggregation -------------------------------------------------

    def get_progress_report(self) -> dict:
        """Aggregate event counts for the progress report."""
        events = self.query()
        return {
            "total_events": len(events),
            "iterations_completed": sum(
                1 for e in events if e.event_type == EventType.LOOP_ITERATION_COMPLETED
            ),
            "units_completed": sum(
                1 for e in events if e.event_type == EventType.EXECUTION_UNIT_COMPLETED
            ),
            "error_count": sum(
                1 for e in events if e.severity == Severity.ERROR
            ),
            "warnings": sum(
                1 for e in events if e.severity == Severity.WARN
            ),
        }
