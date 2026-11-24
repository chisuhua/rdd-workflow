"""``rddf status`` subcommand handler.

Four modes (per ``docs/superpowers/specs/2026-07-20-dashboard-design.md``
§2):

  - **Mode A** (default, no args): **two** tables, both derived from disk
    (no ``iteration.json``):
      1. 改进提案状态 — NAME / PRI / STATUS / PHASE, from
         ``.rddf/improvements/*.md`` + ``improvement-approved.md`` +
         ``openspec/changes/archive/`` (shared implementation:
         ``dashboard.collect_pending()``).
      2. active changes — NAME / STATUS / TASKS / PLAN / BUILDER, from
         ``openspec/changes/*/``, each ``tasks.md``, ``.rddf/plans/<name>.md``
         and ``.rddf/state/builder/<name>.json``.

  - **Mode B** (``<change-name>`` positional arg): single-change detail
    view, derived from disk. Shows name, disk-derived status, builder
    phase, tasks and plan path. Returns 1 if the named change is neither
    active nor archived.

  - **Mode D** (``--roadmap`` flag): roadmap status view. Reads
    ``roadmap-state.json`` via :func:`state_reader.read_roadmap_state`
    and prints a phases table with status and per-category counts.
    Returns 0 with a friendly notice when roadmap-state.json is absent.

**No ``iteration.json`` involvement** (per change
``rddf-status-based-on-improvements``): iteration.json is *procedural
state* (written by hooks / archive sync) and is not the maintenance truth
source for 改进提案状态 — ``.rddf/improvements/*.md`` is. Use
``rddf iteration`` to lint iteration.json, and ``rddf dashboard`` for the
full panorama.

Usage::

    python3 -m skills._lib.cli status                 # Mode A (two tables)
    python3 -m skills._lib.cli status <change-name>   # Mode B detail
    python3 -m skills._lib.cli status --roadmap       # Mode D roadmap

The project root is injected by ``cli.__main__`` via the
``RDDF_PROJECT_ROOT`` env var; falls back to ``os.getcwd()`` when unset.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

from skills._lib.cli import resolve_project_root  # noqa: E402  (per fix-33-handlers)
from _lib.builder_handoff import read_builder_handoff  # noqa: E402  (per fix-33-handlers)
from _lib.tasks_count import count_tasks  # noqa: E402

# Status -> emoji icon (single source of truth for Mode A/B rendering).
# This table serves the **disk-derived** vocabulary
# (``planned`` / ``in_worktree`` / ``completed`` / ``committed`` /
# ``archived`` / ``unknown``) — ``rddf status`` does NOT read
# ``iteration.json`` (see the module docstring).
# ``dashboard/renderer.py::_STATUS_ICON`` serves the **iteration.json**
# vocabulary (the schema enum) instead — the two tables are deliberately NOT
# the same set (``committed`` lives only here; ``proposed`` / ``review`` only
# there).  The overlap is locked by
# ``tests/unit/test_iteration_status_coverage.py``.
# here so this module has zero cross-package dependencies beyond
# state_reader (which is already read-only and cheap).
# Only the keys status_cmd actually renders (the disk-derived status set).
# The dashboard's wider map lives in ``dashboard/renderer.py::_STATUS_ICON``.
_STATUS_ICON = {
    "planned":      "📋",
    "in_worktree":  "🔧",
    "completed":    "✅",
    "archived":     "📦",
    "committed":    "💼",
    "unknown":      "?",
}

# Phase status -> emoji icon for Mode D roadmap rendering.
_PHASE_STATUS_ICON = {
    "completed":   "✅",
    "in_progress": "🔄",
    "pending":     "⏳",
    "unknown":     "❓",
}

_USAGE = "usage: rddf status [<name>|--roadmap]"


def _has_worktree(project_root: str, name: str) -> bool:
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


def _has_committed(project_root: str, name: str) -> bool:
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
    return name in _plan_committed_changes(project_root)


def _plan_committed_changes(project_root: str) -> set[str]:
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


def _tasks_complete(project_root: str, name: str) -> bool:
    """True when the change has a ``tasks.md`` and every task is checked."""
    path = os.path.join(project_root, "openspec", "changes", name, "tasks.md")
    try:
        with open(path, encoding="utf-8") as fh:
            done, total = count_tasks(fh.read())
    except (OSError, UnicodeDecodeError):
        return False
    return total > 0 and done == total


def _disk_change_status(project_root: str, name: str) -> str:
    """Derive a change's status from disk (same rules as the archived
    ``status`` skill's ``render_status_mode_a.sh``, now under
    ``docs/legacy/skills/status/scripts/``).

    Rules, in order:

    1. a git worktree on branch ``openspec/<name>`` ⇒ ``in_worktree``
    2. the change is committed ⇒ ``committed``
    3. the change's ``tasks.md`` is 100% checked ⇒ ``completed``
    4. otherwise ⇒ ``planned``

    ⚠ Rule 3 exists because rule 2 is unreachable in repos where
    ``openspec/`` is gitignored — without it every finished change was
    reported as ``planned``.
    """
    if _has_worktree(project_root, name):
        return "in_worktree"
    if _has_committed(project_root, name):
        return "committed"
    if _tasks_complete(project_root, name):
        return "completed"
    return "planned"


def _tasks_disp(project_root: str, name: str) -> str:
    """``done/total`` from the change's tasks.md, or ``-`` when unavailable."""
    path = os.path.join(project_root, "openspec", "changes", name, "tasks.md")
    try:
        with open(path, encoding="utf-8") as fh:
            done, total = count_tasks(fh.read())
    except (OSError, UnicodeDecodeError):
        return "-"
    if total > 0:
        return f"{done}/{total}"
    return "-"


def _archived_change_dir(project_root: str, name: str) -> str | None:
    """Absolute path of the archived copy of ``name``, or None."""
    archive_dir = os.path.join(project_root, "openspec", "changes", "archive")
    if not os.path.isdir(archive_dir):
        return None
    try:
        entries = sorted(os.listdir(archive_dir))
    except OSError:
        return None
    for entry in entries:
        if entry.endswith(f"-{name}"):
            return os.path.join(archive_dir, entry)
    return None


def cmd_status(args: list[str]) -> int:
    """Handle ``rddf status [<name>|--roadmap]``.

    Routing precedence:
        1. ``-h`` / ``--help`` -> print help, return 0.
        2. ``--roadmap`` flag anywhere in args -> Mode D (roadmap
           status table).
        3. First non-flag, non-empty positional arg -> Mode B
           (single-change detail view).
        4. No args (or only flags Mode D recognizes) -> Mode A
           (default: 改进提案状态 + active changes).

    Args:
        args: Args after the ``status`` token. Recognized flags:
            ``--roadmap`` (Mode D), ``-h``/``--help``. Any other
            non-flag token is treated as a change name for Mode B.

    Returns:
        0 on success, 1 on error (e.g. change not found in Mode B),
        2 on bad flag.
    """
    use_roadmap_mode = False
    change_name: str | None = None

    for flag in args:
        if flag == "--roadmap":
            use_roadmap_mode = True
        elif flag in ("-h", "--help"):
            _print_help()
            return 0
        elif flag.startswith("-"):
            # Unknown flag (starts with ``-``). Reject explicitly so a
            # typo like ``--itertion`` doesn't get silently treated as
            # a change name in Mode B.
            print(f"❌ status: unknown flag {flag!r}", file=sys.stderr)
            print(f"   {_USAGE}", file=sys.stderr)
            return 2
        elif change_name is None and flag:
            # First non-flag positional arg -> change name for Mode B.
            change_name = flag
        else:
            # Extra positional arg: we don't support multi-name queries.
            print(
                f"❌ status: unexpected extra argument {flag!r}",
                file=sys.stderr,
            )
            print(f"   {_USAGE}", file=sys.stderr)
            return 2

    project_root = os.environ.get("RDDF_PROJECT_ROOT") or resolve_project_root()

    if use_roadmap_mode:
        return cmd_roadmap(project_root)
    if change_name is not None:
        return cmd_status_detail(change_name, project_root)
    return _mode_a(project_root)


def _builder_phase(project_root: str, change_name: str, status: str) -> str:
    """Builder stage of a change, or ``-`` when unknown.

    Archived changes always show ``-``: their builder state stays on disk
    (``phase-3``) and showing it would read as "still in P3". Missing or
    unparsable builder state also degrades to ``-`` — the status view must
    never fail because of one broken state file.
    """
    if status == "archived":
        return "-"
    try:
        data = read_builder_handoff(project_root, change_name)
    except (OSError, ValueError):
        return "-"
    return data.get("current_phase") or "-"


def cmd_status_detail(name: str, project_root: str) -> int:
    """Mode B: single-change detail view, derived from disk.

    Prints a compact detail block:

        Change: <name>
        Status: <icon> <status>
        Builder phase: <phase or ->
        Tasks: <done>/<total>
        Plan: <plan path or "no plan">

    The status is derived from the filesystem (worktree / committed HEAD /
    skeleton) and the tasks counter reads ``tasks.md`` directly — no
    iteration.json involvement.

    Args:
        name: Change name (directory under ``openspec/changes/``).
        project_root: Absolute path to the project root.

    Returns:
        0 on success, 1 if the named change is neither active nor archived.
    """
    active_dir = os.path.join(project_root, "openspec", "changes", name)
    archived_dir = _archived_change_dir(project_root, name)

    if os.path.isdir(active_dir):
        status = _disk_change_status(project_root, name)
        tasks_disp = _tasks_disp(project_root, name)
        plan_path = os.path.join(project_root, ".rddf", "plans", f"{name}.md")
        plan_disp = plan_path if os.path.isfile(plan_path) else "no plan"
    elif archived_dir is not None:
        # Archived changes keep an exit-0 "archived" view: their directory
        # lives under openspec/changes/archive/<date>-<name>/.
        status = "archived"
        tasks_disp = "archived"
        plan_disp = "no plan"
    else:
        print(f"❌ change '{name}' not found")
        return 1

    icon = _STATUS_ICON.get(status, "?")

    print(f"Change: {name}")
    print(f"Status: {icon} {status}")
    print(f"Builder phase: {_builder_phase(project_root, name, status)}")
    print(f"Tasks: {tasks_disp}")
    print(f"Plan: {plan_disp}")
    return 0


def cmd_roadmap(project_root: str) -> int:
    """Mode D: roadmap status view.

    Reads ``roadmap-state.json`` via :func:`state_reader.read_roadmap_state`
    and prints a phases table:

        🗺️  Roadmap status
        Current phase: <phase>

        <icon> <phase-id>: <done>/<total> changes (<status>)
           - <category>: <done>/<total>

    Returns:
        0 on success or when roadmap-state.json is absent (prints a
        friendly notice in the latter case).
    """
    from skills._lib.state_reader import read_roadmap_state

    try:
        rstate = read_roadmap_state(project_root)
    except Exception as e:
        print(
            f"❌ status: failed to read roadmap-state.json: {e}",
            file=sys.stderr,
        )
        return 1

    if rstate is None:
        print("(no roadmap state)")
        return 0

    current_phase = rstate.get("current_phase", "unknown")
    phases = rstate.get("phases", {}) or {}

    print("🗺️  Roadmap status")
    print(f"Current phase: {current_phase}")
    print()

    if not phases:
        print("(no phases defined)")
        return 0

    # Header
    print(f"{'PHASE':<16} {'STATUS':<14} {'DONE/TOTAL':<12}")
    print(f"{'-' * 16} {'-' * 14} {'-' * 12}")

    for phase_id, phase_data in phases.items():
        status = phase_data.get("status", "unknown")
        icon = _PHASE_STATUS_ICON.get(status, "❓")
        status_disp = f"{icon} {status}"[:14]

        categories = phase_data.get("categories", {}) or {}
        total = sum(len(c.get("changes", [])) for c in categories.values())
        done = sum(
            len(c.get("completed_changes", [])) for c in categories.values()
        )
        ratio = f"{done}/{total}"

        print(f"{phase_id:<16} {status_disp:<14} {ratio:<12}")

        # Per-category breakdown (only for phases that have changes).
        for cat_id, cat_data in categories.items():
            cat_total = len(cat_data.get("changes", []) or [])
            if cat_total == 0:
                continue
            cat_done = len(cat_data.get("completed_changes", []) or [])
            print(f"   - {cat_id}: {cat_done}/{cat_total}")

    return 0


def _mode_a(project_root: str) -> int:
    """Mode A: 改进提案状态 + active changes（both derived from disk).

    Section 1 (改进提案状态) comes from the shared
    ``dashboard.collect_pending()`` — the same reader the dashboard's
    Pending section uses, so the two views cannot drift.

    Section 2 (active changes) is derived from ``openspec/changes/*/``:
    status from the filesystem, tasks from ``tasks.md``, plan presence
    from ``.rddf/plans/<name>.md``, builder stage from
    ``.rddf/state/builder/<name>.json``.

    Returns:
        0 on success (including when there is nothing to show).
    """
    from skills._lib.dashboard import collect_pending
    from skills._lib.state_reader import list_change_dirs

    # ---- Section 1: 改进提案状态 ----
    try:
        snapshot = collect_pending(project_root)
    except Exception as exc:
        print(f"❌ status: failed to collect improvement proposals: {exc}",
              file=sys.stderr)
        return 1

    print("📋 Improvement proposals")
    print(f"   Total pending: {len(snapshot.suggestions)}")
    print()

    if snapshot.suggestions:
        print(f"{'NAME':<44} {'PRI':<6} {'STATUS':<12} {'PHASE':<14}")
        print(f"{'-' * 44} {'-' * 6} {'-' * 12} {'-' * 14}")
        for entry in snapshot.suggestions:
            name = (entry.name or "?")[:44]
            pri = (entry.priority or "-")[:6]
            status_disp = (entry.status or "-")[:12]
            phase = (entry.phase or "-")[:14]
            print(f"{name:<44} {pri:<6} {status_disp:<12} {phase:<14}")
    else:
        print("(no pending improvement proposals)")

    if snapshot.errors:
        print()
        print(f"⚠️ {len(snapshot.errors)} improvement file(s) with metadata problems "
              f"(unreadable or invalid front matter)")
        for err in snapshot.errors[:5]:
            print(f"   - {err}")

    # ---- Section 2: active changes (disk-derived) ----
    print()
    print("🔧 Active changes")
    changes = list_change_dirs(project_root)
    print(f"   Total active: {len(changes)}")
    print()

    if not changes:
        print("(no active changes)")
        return 0

    print(f"{'NAME':<44} {'STATUS':<14} {'TASKS':<10} {'PLAN':<6} {'BUILDER':<10}")
    print(f"{'-' * 44} {'-' * 14} {'-' * 10} {'-' * 6} {'-' * 10}")

    for name in changes:
        status = _disk_change_status(project_root, name)
        icon = _STATUS_ICON.get(status, "?")
        status_disp = f"{icon} {status}"[:14]
        plan = "y" if os.path.isfile(
            os.path.join(project_root, ".rddf", "plans", f"{name}.md")
        ) else "n"
        print(
            f"{name[:44]:<44} {status_disp:<14} {_tasks_disp(project_root, name):<10} "
            f"{plan:<6} {_builder_phase(project_root, name, status):<10}"
        )

    return 0


def _print_help() -> None:
    print(_USAGE)
    print()
    print("Show improvement-proposal status and active changes (both derived")
    print("from disk; iteration.json is not consulted).")
    print()
    print("modes:")
    print("  (default)     Mode A: 改进提案状态 + active changes")
    print("                Columns: name, priority, status, phase | name, status,")
    print("                tasks, plan y/n, builder stage")
    print("  <name>        Mode B: single-change detail view")
    print("                Shows: status, builder phase, tasks, plan")
    print("  --roadmap     Mode D: roadmap status (phases + per-category counts)")
    print()
    print("iteration.json linting: rddf iteration")


__all__ = ["cmd_status", "cmd_status_detail", "cmd_roadmap"]
