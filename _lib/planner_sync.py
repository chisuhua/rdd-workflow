"""Planner sync — discover improvements, render state, delegate roadmap write.

This module is the **read-heavy** worker for `rdd-planner`. It scans
.rddf/improvements/*.md (read-only, never modifies), computes the
planner state, and (when --apply) writes:

  - .rddf/state/.planner-state.json  (atomic, via _lib.planner_state)
  - .rddf/roadmap.md  AUTO-SPRINT block (delegated to
    _lib.roadmap_sprint.update_roadmap with table='project')

Per Stage 2.5 P0-1 (ADR-0038): the AUTO-SPRINT block has exactly one
writer — `_lib.roadmap_sprint.update_roadmap`. This module does not
hold its own roadmap lock or render its own sprint block.

All improvement files are NEVER modified (Stage 1 ADR-0037 contract).
"""
from __future__ import annotations

import datetime as _dt
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

__all__ = [
    "SyncError",
    "discover_projects",
    "parse_feedback_status",
    "render_state",
    "apply_state",
]


class SyncError(Exception):
    """Base error for planner_sync."""


def _improvements_dir(project_root: Path) -> Path:
    return project_root / ".rddf" / "improvements"


def _parse_frontmatter(text: str) -> Optional[Dict[str, Any]]:
    """Return frontmatter dict or None if absent/malformed."""
    if not text.startswith("---"):
        return None
    try:
        end = text.index("\n---", 3)
        fm_inner = text[3:end].lstrip("\n")
    except ValueError:
        return None
    try:
        return yaml.safe_load(fm_inner) or {}
    except yaml.YAMLError:
        return None


def parse_feedback_status(proposal_path: Path) -> str:
    """Derive feedback_status from ## Feedback section.

    Returns one of: 'none' | 'needs-revision' | 'rejected' | 'resolved'.
    Defaults to 'none' when no ## Feedback section exists.
    """
    if not proposal_path.exists():
        return "none"
    text = proposal_path.read_text(encoding="utf-8")
    if "## Feedback" not in text:
        return "none"
    feedback_section = text[text.index("## Feedback"):]
    if re.search(r"\*\*kind\*\*: needs-revision", feedback_section):
        return "needs-revision"
    if re.search(r"\*\*kind\*\*: rejected", feedback_section):
        return "rejected"
    if re.search(r"\*\*kind\*\*: ac-fail", feedback_section):
        return "needs-revision"
    if re.search(r"\*\*resolution\*\*: resolved", feedback_section):
        return "resolved"
    return "needs-revision"


def discover_projects(project_root: Path) -> List[Dict[str, Any]]:
    """Scan .rddf/improvements/*.md and return list of project dicts."""
    imp_dir = _improvements_dir(project_root)
    if not imp_dir.exists():
        return []
    records = []
    for f in sorted(imp_dir.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        fm = _parse_frontmatter(text) or {}
        ref = fm.get("roadmap_ref") or {}
        has_ref = isinstance(ref, dict) and bool(ref.get("project_id"))
        record = {
            "proposal": f.stem,
            "project_id": ref.get("project_id") if isinstance(ref, dict) else None,
            "phase": ref.get("phase") if has_ref else "unmapped",
            "theme": ref.get("theme") if isinstance(ref, dict) else None,
            "priority": fm.get("priority", "P2"),
            "proposal_path": str(f),
            "feedback_status": parse_feedback_status(f),
            "mapped": has_ref,
        }
        records.append(record)
    return records


def render_state(
    project_root: Path,
    *,
    current_sprint: Optional[str] = None,
    sprint_started_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Compute planner state from project_root.

    Returns a dict conforming to planner_state_schema.json.
    """
    projects = discover_projects(project_root)
    active = []
    unmapped = []
    synced = []
    for p in projects:
        synced.append(p["proposal"])
        if p["mapped"]:
            active.append({
                "project_id": p["project_id"],
                "phase": p["phase"],
                "theme": p["theme"] or "",
                "priority": p["priority"],
                "status": "active",
                "proposal": p["proposal"],
                "feedback_status": p["feedback_status"],
            })
        else:
            unmapped.append(p["proposal"])

    now = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    return {
        "version": 1,
        "current_sprint": current_sprint or f"sprint-{_dt.datetime.now().strftime('%Y-%m')}",
        "sprint_started_at": sprint_started_at or now,
        "last_sync_at": now,
        "last_sync_status": "ok" if not unmapped else "warn",
        "active_projects": active,
        "unmapped_proposals": unmapped,
        "synced_proposals": synced,
    }


def apply_state(project_root: Path, state: Dict[str, Any]) -> Dict[str, int]:
    """Apply state: write .planner-state.json and delegate AUTO-SPRINT update.

    Returns a dict of {'state_written': bool, 'roadmap_written': bool}.
    Per Stage 2.5 P0-1, the AUTO-SPRINT block is owned exclusively by
    `_lib.roadmap_sprint.update_roadmap`; this function delegates.
    """
    from _lib.planner_state import write_state
    from _lib.roadmap_sprint import update_roadmap
    write_state(project_root, state)

    roadmap_path = project_root / ".rddf" / "roadmap.md"
    roadmap_written = 0
    if roadmap_path.exists():
        update_roadmap(str(roadmap_path), state, table="project")
        roadmap_written = 1

    return {"state_written": 1, "roadmap_written": roadmap_written}