"""Single writer for the tasks_done / tasks_total pair (fix-iteration-tasks-total).

Before this module the pair had asymmetric writers: ``tasks_done`` was written
by ``skills/execute/scripts/execute_step7.py`` （该技能已于 2026-11-20 归档到 `docs/legacy/`，见 change `retire-execute-skill`） and by the archive
sync, while
``tasks_total`` had **no writer at all**. ``_lib/verifier/discovery.py::
_is_eligible`` requires ``done == total > 0``, so the eligible set was
permanently empty and batch verification silently found nothing — the archive
gate then needed a hand-written verdict cache to pass.

Two phases, two different rules:

  ``plan``     Record ``tasks_total`` only. A plan is not execution: a
               ``proposed`` change MUST NOT become ``in_worktree`` at P1 (that
               transition belongs to P2). ``tasks_done`` is left untouched.

  ``execute``  Record ``tasks_done`` and ``tasks_total`` together, from the
               SAME ``count_tasks()`` call, so ``done > total`` is
               unreachable. Status becomes ``in_worktree``; a recorded higher
               ``tasks_done`` is preserved so re-running P2 cannot walk the
               progress backwards (idempotency, per the improvement's AC).

No ``tasks.md`` (the rdd-quick path) ⇒ **no write at all**. Creating a 0/0
entry would make an unchanged change look like a real one.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

# Dependency-free module: importing _lib.iteration.archive_sidecar from here
# would re-enter this package's initialisation (circular).
from _lib.tasks_count import count_tasks

logger = logging.getLogger(__name__)

_PHASES = ("plan", "execute")


def _tasks_md(project_root: str, change_name: str) -> Path:
    return Path(project_root) / "openspec" / "changes" / change_name / "tasks.md"


def record_tasks_snapshot(
    project_root: str,
    change_name: str,
    *,
    phase: str,
) -> Optional[str]:
    """Record task counts for `change_name` into iteration.json.

    Args:
        project_root: absolute path to the project root.
        change_name: change name (matches the tasks.md directory).
        phase: ``"plan"`` (P1) or ``"execute"`` (P2).

    Returns:
        None on success (or on a legitimate no-op such as "no tasks.md").
        A warning string when the write was skipped for a reason the caller
        may want to surface. Never raises — callers in the phase scripts are
        under ``set -euo pipefail`` and a bookkeeping failure must not abort
        the phase.
    """
    if phase not in _PHASES:
        raise ValueError(f"phase must be one of {_PHASES}, got {phase!r}")

    tasks_md = _tasks_md(project_root, change_name)
    if not tasks_md.is_file():
        # rdd-quick has no tasks.md. Not an error, and definitely not a
        # reason to create an entry.
        return f"no tasks.md for {change_name}; task snapshot skipped"

    try:
        done, total = count_tasks(tasks_md.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as exc:
        return f"cannot read {tasks_md}: {exc}"

    if total == 0:
        return f"{tasks_md} has no checkboxes; task snapshot skipped"

    # Import through the skills._lib shim: importing _lib.iteration directly
    # collides with the package's own re-export shim (circular init).
    from skills._lib import iteration as it  # type: ignore

    try:
        data = it.load(project_root)
    except Exception as exc:  # noqa: BLE001 - fail open, caller logs
        return f"iteration.json unreadable: {exc}"

    existing = next(
        (c for c in data.get("changes", []) if c.get("name") == change_name), None
    )
    if existing is None:
        # Creation is P0's job (it knows the status the approval produced).
        return (
            f"{change_name} not in iteration.json; "
            f"tasks snapshot skipped (P0 owns entry creation)"
        )

    current_status = existing.get("status") or "proposed"
    if current_status in ("archived", "archived_partial"):
        # Already archived: the archive sync owns this entry's counts now.
        return (
            f"{change_name} is {current_status}; "
            f"tasks snapshot skipped (archive sync owns archived entries)"
        )

    if phase == "plan":
        fields: dict = {
            "name": change_name,
            "status": current_status,          # do NOT flip proposed -> in_worktree
            "tasks_total": total,
        }
    else:
        previous_done = existing.get("tasks_done")
        # Idempotency: never walk a recorded count backwards. A re-run with an
        # unchanged tasks.md yields the same value; a shrunk one keeps the max.
        keep_done = done
        if isinstance(previous_done, int) and previous_done > done:
            keep_done = previous_done
        fields = {
            "name": change_name,
            "status": "in_worktree",
            "tasks_done": keep_done,
            "tasks_total": total,
        }

    try:
        it.save(project_root, it.add_or_update_change(data, **fields))
    except Exception as exc:  # noqa: BLE001 - fail open
        return f"failed to record task snapshot for {change_name}: {exc}"

    return None


__all__ = ["record_tasks_snapshot"]
