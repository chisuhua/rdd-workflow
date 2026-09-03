"""Planner sync — discover improvements, render state, dual-zone roadmap write.

This module is the **read-heavy** worker for `rdd-planner`. It scans
.rddf/improvements/*.md (read-only, never modifies), computes the
planner state, and (when --apply) writes:

  - .rddf/state/.planner-state.json  (atomic)
  - .rddf/roadmap.md  (dual-zone: only the AUTO-SPRINT block)

All improvement files are NEVER modified (Stage 1 ADR-0037 contract).
"""
from __future__ import annotations

import datetime as _dt
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from _lib.core.atomic_write import atomic_write_text
from _lib.core.lock import FileLock

__all__ = [
    "SyncError",
    "discover_projects",
    "parse_feedback_status",
    "render_state",
    "apply_state",
]

AUTO_SPRINT_START = "<!-- AUTO-SPRINT-START -->"
AUTO_SPRINT_END = "<!-- AUTO-SPRINT-END -->"
SPRINT_HEADER_PREFIX = "## Current Sprint:"


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
    """Apply state: write .planner-state.json and update AUTO-SPRINT block.

    Returns a dict of {'state_written': bool, 'roadmap_written': bool}.
    """
    from _lib.planner_state import write_state
    write_state(project_root, state)

    roadmap_path = project_root / ".rddf" / "roadmap.md"
    if roadmap_path.exists():
        roadmap_text = roadmap_path.read_text(encoding="utf-8")
        new_block = _render_sprint_block(state)
        updated = _merge_sprint_block(roadmap_text, new_block)
        with FileLock(str(roadmap_path.with_suffix(".lock")), timeout=10.0):
            atomic_write_text(roadmap_path, updated)

    return {"state_written": 1, "roadmap_written": 1 if roadmap_path.exists() else 0}


def _render_sprint_block(state: Dict[str, Any]) -> str:
    """Render the inner content of the AUTO-SPRINT block (no sentinels)."""
    lines = [f"{SPRINT_HEADER_PREFIX} {state['current_sprint']}", ""]
    if state["active_projects"]:
        lines.append("| Project | Phase | Priority | Feedback | Proposal |")
        lines.append("|---------|-------|----------|----------|----------|")
        for p in state["active_projects"]:
            lines.append(
                f"| {p['project_id']} | {p['phase']} | {p['priority']} | "
                f"{p['feedback_status']} | {p['proposal']} |"
            )
    else:
        lines.append("_No active projects in current sprint._")
    lines.append("")
    if state["unmapped_proposals"]:
        lines.append(f"### Unmapped ({len(state['unmapped_proposals'])})")
        for name in state["unmapped_proposals"][:10]:
            lines.append(f"- {name}")
        if len(state["unmapped_proposals"]) > 10:
            lines.append(f"- ... and {len(state['unmapped_proposals']) - 10} more")
        lines.append("")
    return "\n".join(lines)


def _merge_sprint_block(roadmap_text: str, new_block: str) -> str:
    """Insert or replace the AUTO-SPRINT block in roadmap_text.

    - If both sentinels present: replace content between them.
    - If only start sentinel: insert end sentinel and replace.
    - If neither: append after '## Phase Skeleton' table (idempotent first-run).
    """
    start_idx = roadmap_text.find(AUTO_SPRINT_START)
    end_idx = roadmap_text.find(AUTO_SPRINT_END)

    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        before = roadmap_text[:start_idx + len(AUTO_SPRINT_START)]
        after = roadmap_text[end_idx:]
        return f"{before}\n{new_block}\n{after}"

    if start_idx != -1 and end_idx == -1:
        before = roadmap_text[:start_idx + len(AUTO_SPRINT_START)]
        return f"{before}\n{new_block}\n{AUTO_SPRINT_END}\n"

    if "## Phase Skeleton" in roadmap_text and "<!-- AUTO-INDEX -->" in roadmap_text:
        idx = roadmap_text.index("<!-- AUTO-INDEX -->")
        before = roadmap_text[:idx].rstrip() + "\n\n"
        after = "\n" + roadmap_text[idx:]
        return f"{before}{AUTO_SPRINT_START}\n{new_block}\n{AUTO_SPRINT_END}\n{after}"

    return f"{roadmap_text.rstrip()}\n\n{AUTO_SPRINT_START}\n{new_block}\n{AUTO_SPRINT_END}\n"