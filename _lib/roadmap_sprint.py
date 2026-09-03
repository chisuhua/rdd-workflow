"""Roadmap AUTO-SPRINT section renderer.

The user-editable parts of `roadmap.md` (long-term phase definitions)
are separated from the auto-generated "current sprint" table by HTML
comment sentinels:

    <!-- AUTO-SPRINT-START -->
    ... auto-generated table ...
    <!-- AUTO-SPRINT-END -->

`render_sprint_table(data)` returns the inner content (the markdown
table) for the AUTO-SPRINT block. `update_roadmap(roadmap_path, data)`
rewrites the file in place: preserves everything outside the sentinels,
replaces everything between them.

Stage 2.5 P0-1 (per ADR-0038): `update_roadmap` is the sole writer of
the AUTO-SPRINT block. Both change-shape (`render_sprint_table`) and
project-shape (`render_project_table`) rendering share the same sentinel
split helper and locked atomic write. The lock path is
`<roadmap_path>.lock`.

Design choices:
- Atomic write (write to .tmp then rename) so a partial render never
  leaves the file with a half-updated block.
- Per-file FileLock around read/write so concurrent writers (planner
  sync and loop hooks) cannot interleave.
- If the file is missing, the caller should not call this — they
  should run `skill_use("roadmap", "init")` first.
- If the sentinels are missing, the block is appended to the end of
  the file with a header. (First-run behavior.)
- Stale-deps warning: if any active change's `last_deps_at` is > 24h
  old, a warning line is rendered into the table header.
"""
from __future__ import annotations

import datetime
import logging
import os
from pathlib import Path
from typing import Optional

from skills._lib.core.lock import FileLock

logger = logging.getLogger(__name__)

START_SENTINEL = "<!-- AUTO-SPRINT-START -->"
END_SENTINEL = "<!-- AUTO-SPRINT-END -->"
STALE_DEPS_HOURS = 24

_STATUS_ICON = {
    "proposed": "📋",
    "in_worktree": "🔄",
    "completed": "✅",
}


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _format_staleness(latest_deps_at: Optional[str]) -> str:
    """Return a human-friendly staleness string for the header line."""
    if not latest_deps_at:
        return "never"
    try:
        last = datetime.datetime.fromisoformat(latest_deps_at.replace("Z", "+00:00"))
    except ValueError:
        return "unknown"
    delta = _now() - last
    hours = delta.total_seconds() / 3600
    if hours < 1:
        return f"{int(delta.total_seconds() / 60)}m ago"
    if hours < 24:
        return f"{int(hours)}h ago"
    return f"{int(hours / 24)}d ago"


def _latest_deps_at(changes: list[dict]) -> Optional[str]:
    """Return the most recent last_deps_at across all active changes."""
    candidates: list[Optional[str]] = [
        c.get("last_deps_at") for c in changes if c.get("last_deps_at")
    ]
    if not candidates:
        return None
    valid = [x for x in candidates if x is not None]
    if not valid:
        return None
    return max(valid)


def _has_stale_deps(changes: list[dict]) -> bool:
    """True if any active change's last_deps_at is > STALE_DEPS_HOURS ago."""
    now = _now()
    for c in changes:
        last_deps = c.get("last_deps_at")
        if not last_deps:
            continue
        try:
            last = datetime.datetime.fromisoformat(last_deps.replace("Z", "+00:00"))
        except ValueError:
            continue
        if (now - last).total_seconds() / 3600 > STALE_DEPS_HOURS:
            return True
    return False


def render_sprint_table(data: dict) -> str:
    """Render the inner content of the AUTO-SPRINT block (no sentinels).

    Returns a multi-line string suitable for direct insertion between
    the START_SENTINEL and END_SENTINEL lines.
    """
    changes = data.get("changes", [])
    active = [c for c in changes if c.get("status") in ("proposed", "in_worktree", "completed")]
    archived = [c for c in changes if c.get("status") == "archived"]
    phase = data.get("current_phase", "default")
    latest_deps = _latest_deps_at(active)
    staleness = _format_staleness(latest_deps)
    staleness_warn = " ⚠️" if _has_stale_deps(active) else ""

    lines = []
    lines.append(f"_Phase: `{phase}` · Active: {len(active)} · Archived: {len(archived)} · Last deps: {staleness}{staleness_warn}_")
    lines.append("")

    if not active:
        lines.append("_（无 active change — 运行 `skill_use(\"propose\", \"<name>\")` 添加）_")
    else:
        lines.append("| Change | Phase | Cat | Status | Blocker | Group | Conflicts | Tasks | Plan |")
        lines.append("|--------|-------|-----|--------|---------|-------|-----------|-------|------|")
        for c in active:
            icon = _STATUS_ICON.get(c.get("status", ""), "?")
            blocker = c.get("blocker") or "—"
            group = str(c.get("parallel_group", "")) if c.get("parallel_group") is not None else "—"
            conflicts = ", ".join(c.get("conflicts", []) or []) or "—"
            done = c.get("tasks_done", 0) or 0
            total = c.get("tasks_total", 0) or 0
            tasks = f"{done}/{total}" if total else "—"
            plan = "✅" if c.get("plan_path") else "—"
            short_phase = (c.get("phase") or "—")[:8]
            short_cat = (c.get("category") or "—")[:10]
            lines.append(
                f"| {c.get('name', '?')} | {short_phase} | {short_cat} | {icon} {c.get('status', '?')} | "
                f"{blocker} | {group} | {conflicts} | {tasks} | {plan} |"
            )

    if archived:
        lines.append("")
        lines.append("_🗄️ Archived (top 5): " + ", ".join(f"`{c.get('name', '?')}`" for c in archived[:5]) + "_")

    return "\n".join(lines) + "\n"


def _split_around_sentinels(content: str) -> tuple[str, str]:
    """Return (before, after) the AUTO-SPRINT sentinels in `content`.

    Three cases:

    - Both sentinels present, END after START (happy path):
      `before` is content before START, `after` is content after END.
      update_roadmap() uses these to replace the inner block in place.

    - Both sentinels missing: `before` is the whole content (with
      trailing newline), `after` is "". update_roadmap() appends a
      fresh block to the end.

    - Dangling/malformed (one sentinel missing, or END before START):
      discard everything from the first sentinel position to end of
      file. User content before the first sentinel is preserved;
      update_roadmap() then appends a fresh well-formed block. This
      self-heals files where a previous update was interrupted
      mid-write (START present, END missing), or where a user
      manually inserted an orphaned marker, or where the two
      sentinels appear in reversed order.

    Without this self-healing, dangling-sentinel files would
    accumulate duplicate START markers on each subsequent update,
    producing visibly malformed output until manual cleanup.
    """
    start_idx = content.find(START_SENTINEL)
    end_idx = content.find(END_SENTINEL)
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        before = content[:start_idx]
        after = content[end_idx + len(END_SENTINEL):]
        return before, after

    malformed_present = [idx for idx in (start_idx, end_idx) if idx != -1]
    if not malformed_present:
        before = content if content.endswith("\n") else content + "\n"
        return before, ""

    first_marker = min(malformed_present)
    before = content[:first_marker]
    if not before.endswith("\n"):
        before += "\n"
    return before, ""


def render_full_block(data: dict) -> str:
    """Render the complete AUTO-SPRINT block including sentinel comments.

    Useful for first-run append (when sentinels are missing).
    """
    inner = render_sprint_table(data)
    return f"{START_SENTINEL}\n{inner}{END_SENTINEL}\n"


def render_project_table(data: dict) -> str:
    """Render the planner project table for AUTO-SPRINT block.

    `data` is a planner state dict with keys:
      - current_sprint: str (e.g. "sprint-2026-09")
      - active_projects: list of dicts with keys
        project_id, phase, priority, feedback_status, proposal
      - unmapped_proposals: list[str] (optional)

    Returns the inner content (no sentinels) suitable for insertion
    between `<!-- AUTO-SPRINT-START -->` and `<!-- AUTO-SPRINT-END -->`.
    """
    sprint = data.get("current_sprint", "")
    active = data.get("active_projects") or []
    unmapped = data.get("unmapped_proposals") or []
    lines = [f"## Current Sprint: {sprint}", ""]
    if active:
        lines.append("| Project | Phase | Priority | Feedback | Proposal |")
        lines.append("|---------|-------|----------|----------|----------|")
        for p in active:
            pid = p.get("project_id") or "—"
            phase = p.get("phase") or "—"
            prio = p.get("priority") or "—"
            fb = p.get("feedback_status") or "none"
            prop = p.get("proposal") or "—"
            lines.append(f"| {pid} | {phase} | {prio} | {fb} | {prop} |")
    else:
        lines.append("_No active projects in current sprint._")
    lines.append("")
    if unmapped:
        lines.append(f"### Unmapped ({len(unmapped)})")
        for name in unmapped[:10]:
            lines.append(f"- {name}")
        if len(unmapped) > 10:
            lines.append(f"- ... and {len(unmapped) - 10} more")
        lines.append("")
    return "\n".join(lines) + "\n"


def update_roadmap(roadmap_path: str, data: dict, *, table: str = "changes") -> None:
    """Rewrite roadmap.md to refresh the AUTO-SPRINT block in place.

    - `table='changes'` (default): legacy change-table renderer
      (`render_sprint_table`). Used by `test_iteration_lifecycle` and
      loop hooks.
    - `table='project'`: planner project-table renderer
      (`render_project_table`). Used by `rddf planner sync --apply`.

    This function is the **only writer** of the AUTO-SPRINT block. It
    serializes concurrent writers via a per-file FileLock
    (`<roadmap_path>.lock`) and writes atomically (.tmp + rename).
    Returns silently if `roadmap_path` does not exist (caller should
    have ensured the file exists; this avoids clobbering).
    """
    if not os.path.isfile(roadmap_path):
        logger.debug("roadmap.md not found at %s; skipping AUTO-SPRINT update", roadmap_path)
        return

    if table == "project":
        inner = render_project_table(data)
    else:
        inner = render_sprint_table(data)

    lock_path = str(Path(roadmap_path).with_suffix(".lock"))
    with FileLock(lock_path, timeout=10.0):
        with open(roadmap_path, "r", encoding="utf-8") as f:
            content = f.read()

        before, after = _split_around_sentinels(content)
        new_block = f"{START_SENTINEL}\n{inner}{END_SENTINEL}\n"

        if not after:
            new_content = before + "\n" + new_block
        else:
            new_content = before + new_block + after

        tmp_path = roadmap_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(new_content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, roadmap_path)
    logger.debug("roadmap.md AUTO-SPRINT block updated (%d bytes, table=%s)", len(new_content), table)
