"""Session stats tracking for developer experience observability.

Per improvements/developer-experience-observability.md:
- Track tool calls (bash, read, edit, write, task) by name
- Track failures (quota exhausted, timeouts) with type/tool/count
- Track phase durations (plan, execute, archive) in seconds
- Output to .rddf/state/session_stats.json (env-overridable via RDDF_STATE_DIR)

Output file is read by post-session reports to identify workflow bottlenecks.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


def _get_session_stats_path() -> Path:
    """Resolve .rddf/state/session_stats.json path."""
    rddf_state = os.environ.get("RDDF_STATE_DIR")
    if rddf_state:
        return Path(rddf_state) / "session_stats.json"
    project_root = Path(os.environ.get("PROJECT_ROOT", "."))
    return project_root / ".rddf" / "state" / "session_stats.json"


def _empty_stats() -> Dict:
    """Return a fresh empty stats structure."""
    return {
        "session_id": "",
        "tool_calls": {},
        "failures": [],
        "phase_durations": {},
        "updated_at": "",
    }


def load_session_stats() -> Dict:
    """Load session stats from JSON file. Returns empty if missing."""
    path = _get_session_stats_path()
    if not path.exists():
        return _empty_stats()
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return _empty_stats()


def save_session_stats(stats: Dict) -> None:
    """Atomic write of session stats to JSON file."""
    path = _get_session_stats_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    # Auto-generate session_id if missing
    if not stats.get("session_id"):
        stats["session_id"] = f"ses_{uuid.uuid4().hex[:12]}"

    stats["updated_at"] = datetime.now(timezone.utc).isoformat()

    tmp_path = path.with_suffix(".json.tmp")
    with open(tmp_path, "w") as f:
        json.dump(stats, f, indent=2)
    tmp_path.replace(path)


def record_tool_call(tool: str) -> None:
    """Record a tool call. Increments count by tool name."""
    stats = load_session_stats()
    stats["tool_calls"][tool] = stats["tool_calls"].get(tool, 0) + 1
    save_session_stats(stats)


def record_failure(failure_type: str, tool: str = "unknown", count: int = 1, **metadata) -> None:
    """Record a failure event. Aggregates by type+tool."""
    stats = load_session_stats()
    now = datetime.now(timezone.utc).isoformat()

    existing = None
    for f in stats["failures"]:
        if f.get("type") == failure_type and f.get("tool") == tool:
            existing = f
            break

    if existing is not None:
        existing["count"] = existing.get("count", 0) + count
        existing["last_occurred_at"] = now
    else:
        stats["failures"].append({
            "type": failure_type,
            "tool": tool,
            "count": count,
            "first_occurred_at": now,
            "last_occurred_at": now,
            **metadata,
        })

    save_session_stats(stats)


def record_phase_duration(phase: str, seconds: float) -> None:
    """Record duration of a workflow phase (in seconds)."""
    stats = load_session_stats()
    stats["phase_durations"][phase] = stats["phase_durations"].get(phase, 0) + seconds
    save_session_stats(stats)


def reset_session_stats() -> None:
    """Reset all stats to empty."""
    path = _get_session_stats_path()
    if path.exists():
        path.unlink()
