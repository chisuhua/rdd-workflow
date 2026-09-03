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
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

__all__ = [
    "SyncError",
    "discover_projects",
    "parse_feedback_status",
    "render_state",
    "apply_state",
    "apply_state_with_warnings",
    "diff_state",
    "advance_sprint",
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
    """Derive feedback_status from the latest feedback entry.

    Per Stage 2.5 P0-2 (ADR-0037 latest-entry authority): isolates the
    `## Feedback` section (up to the next top-level `##`), selects the
    entry whose `### feedback-<id>` matches the frontmatter
    `last_feedback_id` (fallback: last `### feedback-*` block when the
    pointer is absent; fail-closed to `none` when the pointer names a
    missing block). Precedence is `resolution` (resolved → resolved)
    before `kind` mapping: needs-revision|ac-fail → needs-revision,
    rejected → rejected, blocked|noted → noted.

    Returns one of: 'none' | 'needs-revision' | 'rejected' | 'resolved' | 'noted'.
    """
    if not proposal_path.exists():
        return "none"
    text = proposal_path.read_text(encoding="utf-8")
    if "## Feedback" not in text:
        return "none"

    start = text.index("## Feedback")
    section = text[start:]
    rest = section[len("## Feedback"):]
    section_end = len(rest)
    pos_next_section = rest.find("\n## ", 1)
    if pos_next_section != -1 and pos_next_section < section_end:
        section_end = pos_next_section
    section = section[: len("## Feedback") + section_end]

    fm_id = None
    if text.startswith("---"):
        try:
            end_fm = text.index("\n---", 3)
            fm_inner = text[3:end_fm]
            fm = yaml.safe_load(fm_inner) or {}
            if isinstance(fm, dict):
                fm_id = fm.get("last_feedback_id")
        except (ValueError, yaml.YAMLError):
            fm_id = None

    blocks = []
    cursor = 0
    while True:
        j = section.find("\n### ", cursor + 1)
        if j == -1:
            break
        block_start = j + 1
        next_marker = section.find("\n### ", block_start)
        if next_marker == -1:
            next_marker = len(section)
        blocks.append(section[block_start:next_marker])
        cursor = j
        if cursor > 10_000:
            break

    if not blocks:
        return "none"

    if fm_id:
        selected = next((b for b in blocks if b.startswith(f"### {fm_id}")), None)
        if selected is None:
            logger.warning(
                "last_feedback_id %r points to missing entry; returning 'none'",
                fm_id,
            )
            return "none"
    else:
        selected = blocks[-1]

    if re.search(r"\*\*resolution\*\*: resolved", selected):
        return "resolved"
    m = re.search(r"\*\*kind\*\*:\s*(\S+)", selected)
    if not m:
        return "none"
    kind = m.group(1)
    if kind == "rejected":
        return "rejected"
    if kind in ("needs-revision", "ac-fail"):
        return "needs-revision"
    if kind in ("blocked", "noted"):
        return "noted"
    return "none"


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


def apply_state_with_warnings(project_root: Path, state: Dict[str, Any]) -> str:
    """Like apply_state, but emits a stdout warning listing newly added unmapped proposals.

    Returns the warning text (empty string when no new unmapped).
    Compares the `unmapped_proposals` list against the previous sync's
    stored `previous_unmapped`. On first sync (state file missing or
    no previous_unmapped), baseline equals current — no warning.
    """
    current_unmapped = list(state.get("unmapped_proposals") or [])
    try:
        from _lib.planner_state import read_state
        existing = read_state(project_root)
        previous = list(existing.get("previous_unmapped") or current_unmapped)
    except Exception:
        previous = current_unmapped

    state_with_baseline = dict(state)
    state_with_baseline["previous_unmapped"] = current_unmapped

    apply_state(project_root, state_with_baseline)

    newly = [name for name in current_unmapped if name not in previous]
    if newly:
        msg = f"\u26a0 newly unmapped proposals (vs prior sync): {', '.join(newly)}\n"
        import sys as _sys
        _sys.stdout.write(msg)
        return msg
    return ""


def diff_state(project_root: Path) -> Dict[str, Any]:
    """Compare stored planner state to freshly computed state.

    Returns a dict:
      - has_baseline: bool (False if state file missing or unreadable)
      - unmapped_diff: {"added": [...], "removed": [...]}
      - projects_diff: {project_id: {"phase": (stored, computed), "feedback_status": (stored, computed)}}
    Timestamps (last_sync_at, last_sync_status, sprint id) are NOT
    compared — they always differ and would create noise.
    """
    from _lib.planner_state import _state_path
    state_path = _state_path(project_root)
    if not state_path.exists():
        return {
            "has_baseline": False,
            "unmapped_diff": {"added": [], "removed": []},
            "projects_diff": {},
        }
    try:
        from _lib.planner_state import read_state
        stored = read_state(project_root)
    except Exception:
        return {
            "has_baseline": False,
            "unmapped_diff": {"added": [], "removed": []},
            "projects_diff": {},
        }
    computed = render_state(project_root)
    stored_unmapped = set(stored.get("unmapped_proposals") or [])
    computed_unmapped = set(computed.get("unmapped_proposals") or [])
    stored_active = {p["project_id"]: p for p in (stored.get("active_projects") or [])}
    computed_active = {p["project_id"]: p for p in (computed.get("active_projects") or [])}
    projects_diff: Dict[str, Dict[str, tuple]] = {}
    for pid in sorted(set(stored_active) | set(computed_active)):
        s = stored_active.get(pid, {})
        c = computed_active.get(pid, {})
        d: Dict[str, tuple] = {}
        for key in ("phase", "feedback_status"):
            if s.get(key) != c.get(key):
                d[key] = (s.get(key), c.get(key))
        if d:
            projects_diff[pid] = d
    return {
        "has_baseline": True,
        "unmapped_diff": {
            "added": sorted(computed_unmapped - stored_unmapped),
            "removed": sorted(stored_unmapped - computed_unmapped),
        },
        "projects_diff": projects_diff,
    }


_SPRINT_PATTERN = re.compile(r"^sprint-(\d{4})-(0[1-9]|1[0-2])$")


def _next_sprint_id(current: str) -> str:
    m = _SPRINT_PATTERN.match(current)
    if not m:
        return f"sprint-{_dt.datetime.now().strftime('%Y-%m')}"
    year, month = int(m.group(1)), int(m.group(2))
    if month == 12:
        return f"sprint-{year + 1:04d}-01"
    return f"sprint-{year:04d}-{month + 1:02d}"


def advance_sprint(
    project_root: Path,
    *,
    to_sprint: Optional[str] = None,
    force: bool = False,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Advance current sprint, record previous sprint snapshot to history, and refresh roadmap.

    Enforces forward-only advancement unless force=True.
    Raises SyncError if no baseline state exists or format is invalid.
    """
    from _lib.planner_state import _state_path, read_state, update_state
    from _lib.planner_history import HistoryEntry, append_history_entry

    state_file = _state_path(project_root)
    if not state_file.exists():
        raise SyncError("No baseline state exists. Run `rddf planner sync --apply` first.")

    stored = read_state(project_root)
    old_sprint = stored["current_sprint"]

    if to_sprint:
        if not _SPRINT_PATTERN.match(to_sprint):
            raise SyncError(f"Invalid sprint format: {to_sprint!r}, expected sprint-YYYY-MM")
        new_sprint = to_sprint
    else:
        new_sprint = _next_sprint_id(old_sprint)

    if not force and new_sprint <= old_sprint:
        raise SyncError(f"Target sprint {new_sprint!r} must move forward from {old_sprint!r}. Use --force to override.")

    if dry_run:
        return {"old_sprint": old_sprint, "new_sprint": new_sprint, "dry_run": True}

    now_iso = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")

    history_entry = HistoryEntry(
        version=1,
        sprint=old_sprint,
        closed_at=now_iso,
        started_at=stored.get("sprint_started_at", now_iso),
        snapshot=dict(stored),
    )
    append_history_entry(project_root, history_entry)

    def _advance_mutator(state: Dict[str, Any]) -> Dict[str, Any]:
        state["current_sprint"] = new_sprint
        state["sprint_started_at"] = now_iso
        state["last_sync_at"] = now_iso
        return state

    updated_state = update_state(project_root, _advance_mutator)

    roadmap_path = project_root / ".rddf" / "roadmap.md"
    if roadmap_path.exists():
        from _lib.roadmap_sprint import update_roadmap
        update_roadmap(str(roadmap_path), updated_state, table="project")

    return {"old_sprint": old_sprint, "new_sprint": new_sprint, "dry_run": False}