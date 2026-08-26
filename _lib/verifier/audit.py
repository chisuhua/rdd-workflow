"""Append-only audit log for verifier events.

Per fix-rdd-verifier-lifecycle-dashboard Task 4:
- JSONL at .rddf/state/verifier/<change>.audit.jsonl
- Events: running, failed, halted, bypassed, archive-ready
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

VALID_EVENTS = frozenset({
    "running", "failed", "halted", "bypassed", "archive-ready",
    "error", "skipped",
})


def _audit_path(project_root: Path, change_name: str) -> Path:
    return (Path(project_root) / ".rddf" / "state" / "verifier"
            / f"{change_name}.audit.jsonl")


def write_event(project_root: Path, change_name: str, event: str, *,
                commit: Optional[str] = None,
                route: Optional[str] = None,
                halt_reason: Optional[str] = None,
                bypass_reason: Optional[str] = None,
                bypass_source: Optional[str] = None,
                loop_count: Optional[int] = None) -> None:
    """Append an audit event line."""
    if event not in VALID_EVENTS:
        raise ValueError(f"invalid audit event: {event}; must be one of {sorted(VALID_EVENTS)}")

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "change": change_name,
        "event": event,
    }
    if commit is not None:
        entry["commit"] = commit
    if route is not None:
        entry["route"] = route
    if halt_reason is not None:
        entry["halt_reason"] = halt_reason
    if bypass_reason is not None:
        entry["bypass_reason"] = bypass_reason
    if bypass_source is not None:
        entry["bypass_source"] = bypass_source
    if loop_count is not None:
        entry["loop_count"] = loop_count

    path = _audit_path(Path(project_root), change_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_events(project_root: Path, change_name: str) -> list:
    """Read all audit events for a change."""
    path = _audit_path(Path(project_root), change_name)
    if not path.is_file():
        return []
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events
