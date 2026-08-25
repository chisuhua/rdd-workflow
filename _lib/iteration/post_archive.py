"""skills/_lib/iteration/post_archive.py — synchronization helper for archive.

Extracted per fix-archive-iteration-sync (P0, 2026-08-05):

  sync_iteration_after_archive(project_root, change_name, archive_commit_sha)
    Safely transition a change to 'archived' in iteration.json:
      - Sets status='archived' if not already
      - Sets archived_at (preserves existing if already set — idempotent)
      - Sets archive_commit_sha (preserves existing if already set — idempotent)
      - Sets tasks_done (counted from archive tasks.md if present)
      - Sets plan_path (.rddf/plans/<name>.md)

    Returns:
      None on success
      str (warning message) on failure/missing — caller should log and
      continue; this helper never raises (fail open per MUST NOT clause).

Designed to be called from all archive entry points:
  - archive.sh::archive_change (worktree mode, via auto-merge)
  - tools/archive_on_main.sh (on-main mode, via --confirm-main)
  - rddf status --archive <name>  (CLI invoked)

Not a "writer" — calls existing store.add_or_update_change() so all
schema validation and lock semantics are reused.
"""
from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _resolve_opencode_session_id() -> str:
    """Best-effort: import the package-level session id used by rddf hooks.

    Falls back to "" if not available. Required by store.add_or_update_change
    env-var contract (PYTHONPATH entry script side).
    """
    try:
        from skills._lib import config  # type: ignore
        return getattr(config, "OPENCODE_SESSION_ID", "") or ""
    except Exception:
        return ""


def count_done_tasks(tasks_path: str) -> int:
    """Count `- [x]` markers in a tasks.md file (case-insensitive on 'x').

    Returns:
        Number of completed tasks. Returns 0 if file is missing or unreadable.

    Implementation:
        Simple substring regex — tasks.md has a stable format with
        `- [x] <task description>` per line. The full file is small
        (typically < 100 lines), so re.findall is O(n) with negligible cost.
    """
    p = Path(tasks_path)
    if not p.is_file():
        return 0
    try:
        text = p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        logger.warning("count_done_tasks: cannot read %s: %s", tasks_path, exc)
        return 0
    # Match "- [x]" or "- [X]" at the start of a list-item entry
    return len(re.findall(r"^\s*-\s*\[x\]\s", text, flags=re.MULTILINE | re.IGNORECASE))


def _find_archive_tasks_md(project_root: str, change_name: str) -> Optional[str]:
    """Locate the tasks.md in archive/, if it exists.

    Searches:
      1. openspec/changes/archive/<*>-<name>/tasks.md (date-prefixed)
      2. openspec/changes/archive/<name>/tasks.md (no date)

    Returns:
        Path to tasks.md if found, else None.
    """
    archive_dir = Path(project_root) / "openspec" / "changes" / "archive"
    if not archive_dir.is_dir():
        return None

    # Date-prefixed pattern: 2026-08-05-<name>
    for child in archive_dir.iterdir():
        if child.is_dir() and child.name.endswith(f"-{change_name}"):
            tm = child / "tasks.md"
            if tm.is_file():
                return str(tm)

    # No prefix
    direct = archive_dir / change_name / "tasks.md"
    if direct.is_file():
        return str(direct)

    return None


def sync_iteration_after_archive(
    project_root: str,
    change_name: str,
    archive_commit_sha: Optional[str] = None,
) -> Optional[str]:
    """Transition a change to 'archived' in iteration.json (idempotent).

    Behavior:
      - Iteration.json missing → return warning string, NO raise
      - Iteration.json schema-invalid → return warning string, NO raise
      - Change entry not found → return warning string, NO raise
      - All other cases → modify the entry in place, save, return None

    Idempotency:
      - archived_at: preserved if already set (NOT overwritten)
      - archive_commit_sha: preserved if already set (NOT overwritten)
      - status: set to 'archived' (was 'proposed'/'in_worktree'/etc.)
      - tasks_done: derived from archive tasks.md; preserved if already set
      - plan_path: set to .rddf/plans/<name>.md if not already set

    Args:
        project_root: Absolute path to the project root.
        change_name: Name of the change (matches directory + iteration entry).
        archive_commit_sha: Optional git commit SHA of the archive action.

    Returns:
        None on success.
        str (warning message) on non-fatal failure.
    """
    iter_path = Path(project_root) / ".rddf" / "state" / "iteration.json"
    if not iter_path.is_file():
        msg = f"iteration.json not found at {iter_path}; cannot sync {change_name}"
        logger.warning(msg)
        return msg

    # Lazy import to avoid circular dependency (store.py imports from iteration package)
    from skills._lib.iteration import store  # type: ignore

    try:
        data = store.load(project_root)
    except Exception as exc:
        msg = f"sync_iteration_after_archive: iteration.json unreadable for {change_name}: {exc}"
        logger.warning(msg)
        return msg

    # Locate change entry
    existing = None
    for c in data.get("changes", []):
        if c.get("name") == change_name:
            existing = c
            break
    if existing is None:
        # P0 fix-iteration-phantom-from-deps (2026-08-25): previously
        # this returned a warning and gave up. That left iteration.json
        # out of sync with disk state when an archive ran before
        # propose.md registered the entry. Fall back to on-disk
        # reconciliation (force_mark_archived) which scans
        # openspec/changes/archive/<date>-<name>/ and creates the entry
        # from ground truth. This is idempotent and safe to retry.
        from skills._lib.iteration.repair import force_mark_archived
        recovered = force_mark_archived(
            project_root, change_name, archive_commit_sha=archive_commit_sha,
        )
        if recovered:
            logger.info(
                "sync_iteration_after_archive: change '%s' missing from "
                "iteration.json; auto-recovered via on-disk scan",
                change_name,
            )
            return None
        msg = (
            f"change '{change_name}' not found in iteration.json AND "
            f"no archive dir on disk; archive sync skipped"
        )
        logger.warning(msg)
        return msg

    # Build fields dict — preserve existing values for idempotency
    fields: dict = {"name": change_name, "status": "archived"}

    # archived_at: only set if not already present
    if "archived_at" not in existing:
        from datetime import datetime, timezone
        fields["archived_at"] = datetime.now(timezone.utc).isoformat()

    # archive_commit_sha: only set if not already present AND caller provided one
    if archive_commit_sha and "archive_commit_sha" not in existing:
        fields["archive_commit_sha"] = archive_commit_sha

    # tasks_done: derive from archive tasks.md if present, preserve otherwise
    if "tasks_done" not in existing:
        tasks_md = _find_archive_tasks_md(project_root, change_name)
        if tasks_md:
            done = count_done_tasks(tasks_md)
            fields["tasks_done"] = done

    # plan_path: standard convention
    if "plan_path" not in existing:
        fields["plan_path"] = f".rddf/plans/{change_name}.md"

    # Apply mutation via store (handles lock + schema validation + atomic write)
    try:
        new_data = store.add_or_update_change(data, **fields)
        store.save(project_root, new_data)
    except Exception as exc:
        msg = (
            f"sync_iteration_after_archive: failed to persist for "
            f"{change_name}: {exc}"
        )
        logger.warning(msg)
        return msg

    return None
