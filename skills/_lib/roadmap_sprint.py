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

Design choices:
- Atomic write (write to .tmp then rename) so a partial render never
  leaves the file with a half-updated block.
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
from typing import Optional

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
        lines.append(f"_🗄️ Archived (top 5): " + ", ".join(f"`{c.get('name', '?')}`" for c in archived[:5]) + "_")

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


def update_roadmap(roadmap_path: str, data: dict) -> None:
    """Rewrite roadmap.md to refresh the AUTO-SPRINT block in place.

    - Atomic write (.tmp + rename).
    - Preserves all content outside the sentinels.
    - If sentinels are missing, appends the full block to the end.
    - Returns silently if `roadmap_path` does not exist (caller should
      have ensured the file exists; this avoids clobbering).
    """
    if not os.path.isfile(roadmap_path):
        logger.debug("roadmap.md not found at %s; skipping AUTO-SPRINT update", roadmap_path)
        return

    with open(roadmap_path, "r", encoding="utf-8") as f:
        content = f.read()

    before, after = _split_around_sentinels(content)
    inner = render_sprint_table(data)
    new_block = f"{START_SENTINEL}\n{inner}{END_SENTINEL}\n"

    if not after:
        # First-run: append the full block
        new_content = before + "\n" + new_block
    else:
        # Existing sentinels: replace the inner block, keep the after text
        new_content = before + new_block + after

    tmp_path = roadmap_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(new_content)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, roadmap_path)
    logger.debug("roadmap.md AUTO-SPRINT block updated (%d bytes)", len(new_content))
