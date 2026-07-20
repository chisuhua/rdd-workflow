"""``rddf status`` subcommand handler.

Two modes (per ``docs/superpowers/specs/2026-07-20-dashboard-design.md``
§2):

  - **Mode A** (default, no args): global change overview table built
    from ``iteration.json`` via :func:`state_reader.read_iteration`.
    Columns: name, status emoji, tasks_done/tasks_total, plan_path y/n.

  - **Mode E** (``--iteration`` flag): iteration view, delegated to
    :func:`skills._lib.iteration.render.print_view` (the same renderer
    used by the ``status`` AI skill's Mode E).

Usage::

    python3 -m skills._lib.cli status               # Mode A table
    python3 -m skills._lib.cli status --iteration    # Mode E view

The project root is injected by ``cli.__main__`` via the
``RDDF_PROJECT_ROOT`` env var; falls back to ``os.getcwd()`` when unset.
"""
from __future__ import annotations

import os
import sys

# Status -> emoji icon (single source of truth for Mode A rendering).
# Kept in sync with ``dashboard/renderer.py::_STATUS_ICON``; duplicated
# here so this module has zero cross-package dependencies beyond
# state_reader (which is already read-only and cheap).
_STATUS_ICON = {
    "planned":      "📋",
    "proposed":     "📋",
    "in_worktree":  "🔧",
    "review":       "🔧",
    "completed":    "✅",
    "done":         "✔",
    "archived":     "📦",
    "committed":    "💼",
    "unknown":      "?",
}


def cmd_status(args: list[str]) -> int:
    """Handle ``rddf status [--iteration]``.

    Args:
        args: Args after the ``status`` token. Recognized flags:
            ``--iteration`` (select Mode E), ``-h``/``--help``.

    Returns:
        0 on success, 1 on error, 2 on bad flag.
    """
    use_iteration_mode = False
    for flag in args:
        if flag == "--iteration":
            use_iteration_mode = True
        elif flag in ("-h", "--help"):
            _print_help()
            return 0
        else:
            print(f"❌ status: unknown flag {flag!r}", file=sys.stderr)
            print("   usage: rddf status [--iteration]", file=sys.stderr)
            return 2

    project_root = os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()

    if use_iteration_mode:
        return _mode_e(project_root)
    return _mode_a(project_root)


def _mode_a(project_root: str) -> int:
    """Mode A: global change overview table.

    Reads ``iteration.json`` via :func:`state_reader.read_iteration`
    (read-only, never writes a backup file even on corruption) and
    renders a 4-column table. Missing iteration.json renders a friendly
    notice rather than raising.
    """
    from skills._lib.state_reader import read_iteration

    try:
        iter_data = read_iteration(project_root)
    except Exception as e:
        print(f"❌ status: failed to read iteration.json: {e}", file=sys.stderr)
        return 1

    if iter_data is None:
        print("📭 iteration.json not found")
        print('   initialize via: skill_use("propose", "<change-name>")')
        return 0

    phase = iter_data.get("current_phase", "default")
    updated_at = iter_data.get("updated_at", "")
    changes = iter_data.get("changes", []) or []

    print("📊 Change status overview")
    print(f"   Phase: {phase}    Updated: {updated_at}")
    print(f"   Total changes tracked: {len(changes)}")
    print()

    if not changes:
        print("(no changes tracked)")
        return 0

    # Header
    print(f"{'NAME':<32} {'STATUS':<16} {'TASKS':<10} {'PLAN':<6}")
    print(f"{'-' * 32} {'-' * 16} {'-' * 10} {'-' * 6}")

    for c in changes:
        name = (c.get("name") or "?")[:32]
        status = c.get("status") or "unknown"
        icon = _STATUS_ICON.get(status, "?")
        status_disp = f"{icon} {status}"[:16]

        tasks_done = int(c.get("tasks_done") or 0)
        tasks_total = int(c.get("tasks_total") or 0)
        if tasks_total > 0:
            tasks = f"{tasks_done}/{tasks_total}"
        else:
            tasks = "-"

        plan = "y" if c.get("plan_path") else "n"

        print(f"{name:<32} {status_disp:<16} {tasks:<10} {plan:<6}")

    return 0


def _mode_e(project_root: str) -> int:
    """Mode E: iteration view, delegated to ``iteration.render.print_view``.

    ``print_view`` already handles missing iteration.json gracefully
    (prints a friendly notice and returns 0), so we just forward.
    """
    try:
        from skills._lib.iteration.render import print_view
    except ImportError as e:
        print(f"❌ status: failed to import iteration.render: {e}", file=sys.stderr)
        return 1

    try:
        return print_view(project_root)
    except Exception as e:
        print(f"❌ status: iteration view failed: {e}", file=sys.stderr)
        return 1


def _print_help() -> None:
    print("usage: rddf status [--iteration]")
    print()
    print("Show change status.")
    print()
    print("modes:")
    print("  (default)     Mode A: global change overview table")
    print("                Columns: name, status emoji, tasks_done/total, plan y/n")
    print("  --iteration   Mode E: iteration view (same as `status` AI skill Mode E)")


__all__ = ["cmd_status"]
