"""Discover verifier-eligible changes from iteration.json.

Per fix-rdd-verifier-lifecycle-dashboard Task 6:
- Eligible: status in {in_worktree, completed} AND tasks_done == tasks_total > 0 AND not archived
- Replaces the previous (broken) 'ship-done' status lookup
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Optional

_ARCHIVED = {"archived", "archived_partial"}
_IMPLEMENTED = {"in_worktree", "completed"}


def _is_eligible(change: dict) -> bool:
    status = change.get("status")
    if status in _ARCHIVED:
        return False
    if status not in _IMPLEMENTED:
        return False
    done = change.get("tasks_done") or 0
    total = change.get("tasks_total") or 0
    if total <= 0:
        return False
    return done == total


def discover_eligible(project_root: Path) -> list:
    """Return list of change names eligible for verification.

    Reads `.rddf/state/iteration.json` and applies the eligibility rules.
    Returns empty list if iteration.json missing or malformed.
    """
    state_file = Path(project_root) / ".rddf" / "state" / "iteration.json"
    if not state_file.is_file():
        return []
    try:
        doc = json.loads(state_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return []
    return [c["name"] for c in doc.get("changes", []) if _is_eligible(c)]


def discover_archived(project_root: Path, since: Optional[str] = None) -> list:
    """Return list of archived change names for post-archive audit.

    Per verifier-re-verify-archived-flag proposal:
    - Scans openspec/changes/archive/<date>-<name>/ directories
    - Optionally filters by archive date prefix (since=YYYY-MM-DD)
    - Returns [{name, archive_date}] dicts

    Args:
        project_root: absolute path to project root
        since: optional ISO date (YYYY-MM-DD); only include changes archived on/after this date

    Returns:
        List of dicts {name, archive_date, archive_path}
    """
    archive_root = Path(project_root) / "openspec" / "changes" / "archive"
    if not archive_root.is_dir():
        return []

    since_date = None
    if since:
        try:
            since_date = date.fromisoformat(since)
        except ValueError:
            since_date = None  # invalid → ignore filter

    results = []
    pattern = re.compile(r"^(\d{4}-\d{2}-\d{2})-(.+)$")
    for entry in sorted(archive_root.iterdir()):
        if not entry.is_dir():
            continue
        m = pattern.match(entry.name)
        if not m:
            continue
        archive_date_str, change_name = m.group(1), m.group(2)
        if since_date:
            try:
                entry_date = date.fromisoformat(archive_date_str)
                if entry_date < since_date:
                    continue
            except ValueError:
                continue
        results.append({
            "name": change_name,
            "archive_date": archive_date_str,
            "archive_path": str(entry),
        })
    return results
