"""Tasks.md sidecar generation for archive flow (fix-tasks-md-archive-residue).

Created: fix-tasks-md-archive-residue (P0, 2026-08-05).
Purpose: prevent the "archived 0/total" anomaly where archive_dir/
tasks.md keeps unchecked boxes but iteration.json shows 0/18.
Solution: at archive time, snapshot tasks.md to a sidecar and
derive tasks_done from the sidecar's [x] count.

Public API (called from skills/_lib/archive.sh::archive_change):
  write_tasks_md_sidecar(change_dir)  — creates sidecar + skeleton
  count_tasks(text)                     — counts (done, total) checkboxes
  count_done_tasks(text)                — the `done` half of count_tasks

Idempotent: re-running does not overwrite an existing sidecar.
Graceful: if tasks.md doesn't exist, no sidecar is created.
"""
from __future__ import annotations

from pathlib import Path


_SKELETON_HEADER = (
    "# Tasks: archived snapshot — original author-time estimates\n"
    "# This change has been shipped. See tasks.md.archived-snapshot\n"
    "# for the pre-archive state.\n"
)


# The canonical counter lives in `_lib/tasks_count.py` (no package deps) so the
# three call sites outside `_lib.iteration` can import it without triggering
# this package's re-export shim. Re-exported here because the archive flow
# historically imported it from this module.
from _lib.tasks_count import count_done_tasks, count_tasks  # noqa: F401


def write_tasks_md_sidecar(change_dir: str) -> bool:
    """Snapshot tasks.md and replace it with an archived skeleton.

    Args:
        change_dir: Absolute path to the change directory (e.g.
            ``/path/to/openspec/changes/archive/2026-08-05-mychange/``).

    Returns:
        True if the sidecar was created, False if tasks.md was missing
        (no-op) or the sidecar already exists (idempotent skip).

    Side effects:
        - Creates ``tasks.md.archived-snapshot`` (copy of original)
        - Replaces ``tasks.md`` with an archived-skeleton header
    """
    tasks = Path(change_dir) / "tasks.md"
    if not tasks.is_file():
        return False
    sidecar = tasks.with_name(tasks.name + ".archived-snapshot")
    if sidecar.is_file():
        return False  # idempotent: don't overwrite
    sidecar.write_text(tasks.read_text(encoding="utf-8"), encoding="utf-8")
    tasks.write_text(_SKELETON_HEADER, encoding="utf-8")
    return True


__all__ = ["write_tasks_md_sidecar", "count_done_tasks", "count_tasks"]
