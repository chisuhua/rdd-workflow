"""``rddf session show --events`` subcommand — events.jsonl history replay.

Per wave3-rddf-session-show-events (AC-P2-4-1~6): read-only query CLI for
the events bus. Filters compose with AND; default output is a table sorted
by ts ascending. Never mutates events.jsonl (MN-SE3).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable, Optional


def build_event_query(
    owner: Optional[str] = None,
    session_id: Optional[str] = None,
    kind: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
) -> Callable[[dict], bool]:
    """Build a filter function from CLI flags (AND composable).

    AC-P2-4-1: owner matches event["owner_opencode_session_id"].
    AC-P2-4-2: session matches context.session_id.
    AC-P2-4-3: kind matches event["kind"] (top-level or context).
    AC-P2-4-4: since/until do ISO-8601 lexicographic comparison on ts.
    """
    def query(event: dict) -> bool:
        ctx = event.get("context") or {}
        if owner and event.get("owner_opencode_session_id") != owner:
            return False
        if session_id and ctx.get("session_id") != session_id:
            return False
        if kind and event.get("kind") != kind and ctx.get("kind") != kind:
            return False
        ts = str(event.get("ts", ""))
        if since and ts < since:
            return False
        if until and ts > until:
            return False
        return True
    return query


def format_events_table(events: list[dict]) -> str:
    """Default table format, sorted by ts ascending (AC-P2-4-5)."""
    if not events:
        return "(no events)\n"
    sorted_events = sorted(events, key=lambda e: str(e.get("ts", "")))
    lines = [
        f"{'TIME':<26} {'KIND':<20} {'SESSION_ID':<20} {'EVENT_TYPE':<20} MESSAGE",
        f"{'----':<26} {'----':<20} {'----------':<20} {'----------':<20} -------",
    ]
    for e in sorted_events:
        ts = str(e.get("ts", "?"))[:19]
        kind = str(e.get("kind") or (e.get("context") or {}).get("kind") or "?")[:20]
        sid = str((e.get("context") or {}).get("session_id") or "?")[:20]
        etype = str(e.get("event_type") or "?")[:20]
        msg = str(e.get("message") or "")[:60]
        lines.append(f"{ts:<26} {kind:<20} {sid:<20} {etype:<20} {msg}")
    return "\n".join(lines) + "\n"


def format_events_json(events: list[dict]) -> str:
    """JSON array output (M-SE3), parseable by jq."""
    return json.dumps(events, ensure_ascii=False, indent=2)


def format_events_raw(events: list[dict]) -> str:
    """One JSONL per line (M-SE4), pipeable to jq."""
    return "\n".join(json.dumps(e, ensure_ascii=False) for e in events)


def handle_show_events_cmd(
    events_path: str = ".rddf/state/events.jsonl",
    owner: Optional[str] = None,
    session_id: Optional[str] = None,
    kind: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    format: str = "table",
    include_archive: bool = False,
) -> int:
    """Read events.jsonl, apply filters, emit the requested format.

    AC-P2-4-6: missing/empty events.jsonl -> "(no events)" (no crash).
    M-SE5: archive files excluded unless include_archive=True.
    """
    events_file = Path(events_path)
    if not events_file.exists():
        _emit([], format)
        return 0

    events: list[dict] = []
    with events_file.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                events.append(parsed)

    query = build_event_query(
        owner=owner, session_id=session_id, kind=kind, since=since, until=until
    )
    filtered = [e for e in events if query(e)]
    _emit(filtered, format)
    return 0


def _emit(events: list[dict], format: str) -> None:
    if format == "json":
        sys.stdout.write(format_events_json(events))
    elif format == "raw":
        sys.stdout.write(format_events_raw(events))
    else:
        sys.stdout.write(format_events_table(events))
