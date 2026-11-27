"""Disk-derived status of a change — the single implementation.

Both consumers import it under the same name::

    from _lib.change_status import derive_status as _derive

- ``_lib/cli/status_cmd`` — ``rddf status`` Mode A/B (user-visible view);
- ``_lib/verifier/discovery`` — the batch verifier queue.

Keeping ONE implementation is the point: two copies of "is this change
in_worktree / committed / completed / planned" is exactly the drift this
module removes. ``tests/unit/test_change_status_shared.py`` asserts the
object identity of the two imports.

Rules, in order:

1. a git worktree on branch ``openspec/<name>`` ⇒ ``in_worktree``
2. the change is committed ⇒ ``committed``
3. the change's ``tasks.md`` is 100% checked ⇒ ``completed``
4. otherwise ⇒ ``planned``

⚠ Rule 3 exists because rule 2 is unreachable in repos where ``openspec/``
is gitignored — without it every finished change was reported as ``planned``.

The functions are pure probes (never raise): a broken git or a missing file
degrades to the next rule instead of blanking the view.
"""
from __future__ import annotations

import json
import os
import subprocess

from _lib.tasks_count import count_tasks


def has_worktree(project_root: str, name: str) -> bool:
    """True when a git worktree exists on branch ``openspec/<name>``."""
    try:
        out = subprocess.check_output(
            ["git", "worktree", "list"], cwd=project_root
        ).decode()
    except Exception:
        return False
    for line in out.splitlines():
        parts = line.split()
        if not parts:
            continue
        branch = parts[-1].strip("[]")
        if branch == f"openspec/{name}":
            return True
    return False


def has_committed(project_root: str, name: str) -> bool:
    """True when the change has already been committed (landed).

    Two independent probes, in order:

    1. **git** — the change directory is present in ``HEAD``. This can only
       say something when ``openspec/`` is **tracked**: repos configured with
       ``git.openspec_tracked: false`` (this repo — the whole
       ``openspec/changes/`` tree is gitignored, ADR-0036) can never
       satisfy it, so the ``committed`` status used to be unreachable there.
    2. **plan-done record** — ``.rddf/state/.plan-handoff.json`` lists the
       change in ``committed_changes``. That is the disk-side record of
       "committed" and is independent of git tracking.
    """
    try:
        rc = subprocess.run(
            ["git", "show", f"HEAD:openspec/changes/{name}/.openspec.yaml"],
            cwd=project_root,
            capture_output=True,
        ).returncode
        if rc == 0:
            return True
    except Exception:
        pass
    return name in plan_committed_changes(project_root)


def plan_committed_changes(project_root: str) -> set[str]:
    """``committed_changes`` from ``.rddf/state/.plan-handoff.json``.

    Empty set when the file is missing, unreadable, not a mapping, or the
    key is absent — the probe must never raise.
    """
    path = os.path.join(project_root, ".rddf", "state", ".plan-handoff.json")
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, UnicodeDecodeError, ValueError):
        return set()
    if not isinstance(data, dict):
        return set()
    changes = data.get("committed_changes")
    if not isinstance(changes, list):
        return set()
    return {c for c in changes if isinstance(c, str)}


def tasks_complete(project_root: str, name: str) -> bool:
    """True when the change has a ``tasks.md`` and every task is checked."""
    path = os.path.join(project_root, "openspec", "changes", name, "tasks.md")
    try:
        with open(path, encoding="utf-8") as fh:
            done, total = count_tasks(fh.read())
    except (OSError, UnicodeDecodeError):
        return False
    return total > 0 and done == total


def derive_status(project_root: str, name: str) -> str:
    """Derive a change's status from disk — see the module docstring.

    Returns one of ``in_worktree`` / ``committed`` / ``completed`` /
    ``planned``. No ``iteration.json`` involvement: it is procedural
    bookkeeping, not the truth source.
    """
    if has_worktree(project_root, name):
        return "in_worktree"
    if has_committed(project_root, name):
        return "committed"
    if tasks_complete(project_root, name):
        return "completed"
    return "planned"
