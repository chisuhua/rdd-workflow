"""Discover verifier-eligible changes from iteration.json.

Per fix-rdd-verifier-lifecycle-dashboard Task 6:
- Eligible: status in {in_worktree, completed} AND tasks_done == tasks_total > 0 AND not archived
- Replaces the previous (broken) 'ship-done' status lookup
"""
from __future__ import annotations

import json
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
