"""``rddf status`` subcommand handler.

Four modes (per ``docs/superpowers/specs/2026-07-20-dashboard-design.md``
§2):

  - **Mode A** (default, no args): global change overview table built
    from ``iteration.json`` via :func:`state_reader.read_iteration`.
    Columns: name, status emoji, tasks_done/tasks_total, plan_path y/n.

  - **Mode B** (``<change-name>`` positional arg): single-change
    detail view. Reads ``iteration.json`` and prints name, status,
    phase/category, tasks, plan path, and blocker. Returns 1 if the
    named change is not present in iteration.json.

  - **Mode D** (``--roadmap`` flag): roadmap status view. Reads
    ``roadmap-state.json`` via :func:`state_reader.read_roadmap_state`
    and prints a phases table with status and per-category counts.
    Returns 0 with a friendly notice when roadmap-state.json is absent.

  - **Mode E** (``--iteration`` flag): iteration view, delegated to
    :func:`skills._lib.iteration.render.print_view` (the same renderer
    used by the ``status`` AI skill's Mode E).

Usage::

    python3 -m skills._lib.cli status                 # Mode A table
    python3 -m skills._lib.cli status <change-name>   # Mode B detail
    python3 -m skills._lib.cli status --roadmap       # Mode D roadmap
    python3 -m skills._lib.cli status --iteration     # Mode E view

The project root is injected by ``cli.__main__`` via the
``RDDF_PROJECT_ROOT`` env var; falls back to ``os.getcwd()`` when unset.
"""
from __future__ import annotations

import os
import sys

# Status -> emoji icon (single source of truth for Mode A/B rendering).
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

# Phase status -> emoji icon for Mode D roadmap rendering.
_PHASE_STATUS_ICON = {
    "completed":   "✅",
    "in_progress": "🔄",
    "pending":     "⏳",
    "unknown":     "❓",
}


def _render_iteration_read_error(
    iter_data: object, read_error: str, iter_path: str, mode: str = "name"
) -> int:
    """Render a corrupt-iteration.json error and return exit code 1.

    Shared by ``_mode_a`` and ``_mode_b`` so both modes produce
    identical diagnostic output. Does NOT suggest
    ``skill_use("propose", ...)`` because the corruption is not
    fixable by proposing a new change — it would silently wipe the
    existing data.

    Args:
        iter_data: Parsed data (``None`` since corrupt).
        read_error: Error string from :func:`read_iteration_or_corrupt`.
        iter_path: Absolute path to iteration.json.
        mode: ``"name"`` (single-change mode B) or ``"table"`` (mode A).
            Reserved for future divergence; today both produce the
            same message.

    Returns:
        Always 1 (corrupt iteration.json is a hard error).
    """
    print("❌ iteration.json fails schema validation")
    print(f"   path: {iter_path}")
    print(f"   error: {read_error}")
    print(
        "   fix: restore from a iteration.json.corrupt.<ts> backup in "
        ".rddf/state/, or edit the file manually"
    )
    return 1


def cmd_status(args: list[str]) -> int:
    """Handle ``rddf status [<name>|--roadmap|--iteration]``.

    Routing precedence:
        1. ``-h`` / ``--help`` -> print help, return 0.
        2. ``--iteration`` flag anywhere in args -> Mode E (delegated
           to ``iteration.render.print_view``).
        3. ``--roadmap`` flag anywhere in args -> Mode D (roadmap
           status table).
        4. First non-flag, non-empty positional arg -> Mode B
           (single-change detail view).
        5. No args (or only flags Mode A/E recognize) -> Mode A
           (default overview table).

    Args:
        args: Args after the ``status`` token. Recognized flags:
            ``--iteration`` (Mode E), ``--roadmap`` (Mode D),
            ``-h``/``--help``. Any other non-flag token is treated as
            a change name for Mode B.

    Returns:
        0 on success, 1 on error (e.g. change not found in Mode B),
        2 on bad flag.
    """
    use_iteration_mode = False
    use_roadmap_mode = False
    change_name: str | None = None

    for flag in args:
        if flag == "--iteration":
            use_iteration_mode = True
        elif flag == "--roadmap":
            use_roadmap_mode = True
        elif flag in ("-h", "--help"):
            _print_help()
            return 0
        elif flag.startswith("-"):
            # Unknown flag (starts with ``-``). Reject explicitly so a
            # typo like ``--itertion`` doesn't get silently treated as
            # a change name in Mode B.
            print(f"❌ status: unknown flag {flag!r}", file=sys.stderr)
            print(
                "   usage: rddf status [<name>|--roadmap|--iteration]",
                file=sys.stderr,
            )
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
            print(
                "   usage: rddf status [<name>|--roadmap|--iteration]",
                file=sys.stderr,
            )
            return 2

    project_root = os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()

    # Mode E takes precedence over Mode D and Mode B if multiple flags
    # were supplied (--iteration is the most specific view).
    if use_iteration_mode:
        return _mode_e(project_root)
    if use_roadmap_mode:
        return cmd_roadmap(project_root)
    if change_name is not None:
        return cmd_status_detail(change_name, project_root)
    return _mode_a(project_root)


def cmd_status_detail(name: str, project_root: str) -> int:
    """Mode B: single-change detail view.

    Reads ``iteration.json`` via :func:`state_reader.read_iteration`,
    finds the change entry matching ``name``, and prints a compact
    detail block:

        Change: <name>
        Status: <icon> <status>
        Phase: <phase> / <category>
        Tasks: <done>/<total>
        Plan: <plan_path or "no plan">
        Blocker: <blocker or "none">

    Args:
        name: Change name (directory under ``openspec/changes/``).
        project_root: Absolute path to the project root.

    Returns:
        0 on success, 1 if iteration.json is missing/unreadable or the
        named change is not found in it.
    """
    from skills._lib.state_reader import read_iteration_or_corrupt

    iter_path = f"{project_root}/.rddf/state/iteration.json"
    iter_data, read_error = read_iteration_or_corrupt(project_root)
    if read_error is not None:
        return _render_iteration_read_error(iter_data, read_error, iter_path)

    if iter_data is None:
        print("📭 iteration.json not found")
        print(f"   expected at {iter_path}")
        print('   initialize via: skill_use("propose", "<change-name>")')
        return 1

    changes = iter_data.get("changes", []) or []
    entry: dict | None = None
    for c in changes:
        if c.get("name") == name:
            entry = c
            break

    if entry is None:
        print(f"❌ change '{name}' not found")
        return 1

    status = entry.get("status") or "unknown"
    icon = _STATUS_ICON.get(status, "?")

    phase = entry.get("phase") or "-"
    category = entry.get("category") or "-"
    phase_disp = f"{phase} / {category}" if phase != "-" or category != "-" else "-"

    tasks_done = int(entry.get("tasks_done") or 0)
    tasks_total = int(entry.get("tasks_total") or 0)
    status = entry.get("status") or "unknown"
    if tasks_total > 0:
        if status == "archived":
            tasks_disp = f"archived (snapshot {tasks_done}/{tasks_total})"
        else:
            tasks_disp = f"{tasks_done}/{tasks_total}"
    else:
        tasks_disp = "-"

    plan_path = entry.get("plan_path")
    plan_disp = plan_path if plan_path else "no plan"

    blocker = entry.get("blocker")
    blocker_disp = blocker if blocker else "none"

    print(f"Change: {name}")
    print(f"Status: {icon} {status}")
    print(f"Phase: {phase_disp}")
    print(f"Tasks: {tasks_disp}")
    print(f"Plan: {plan_disp}")
    print(f"Blocker: {blocker_disp}")
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
    """Mode A: global change overview table.

    Reads ``iteration.json`` via :func:`state_reader.read_iteration`
    (read-only, never writes a backup file even on corruption) and
    renders a 4-column table. Missing iteration.json renders a friendly
    notice rather than raising.
    """
    from skills._lib.state_reader import read_iteration_or_corrupt

    iter_path = f"{project_root}/.rddf/state/iteration.json"
    iter_data, read_error = read_iteration_or_corrupt(project_root)
    if read_error is not None:
        return _render_iteration_read_error(iter_data, read_error, iter_path)

    if iter_data is None:
        print("📭 iteration.json not found")
        print(f"   expected at {iter_path}")
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
    print("usage: rddf status [<name>|--roadmap|--iteration]")
    print()
    print("Show change status.")
    print()
    print("modes:")
    print("  (default)     Mode A: global change overview table")
    print("                Columns: name, status emoji, tasks_done/total, plan y/n")
    print("  <name>        Mode B: single-change detail view")
    print("                Shows: status, phase/category, tasks, plan, blocker")
    print("  --roadmap     Mode D: roadmap status (phases + per-category counts)")
    print("  --iteration   Mode E: iteration view (same as `status` AI skill Mode E)")


__all__ = ["cmd_status", "cmd_status_detail", "cmd_roadmap"]
