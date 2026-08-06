"""``rddf discover-ship-changes`` subcommand handler.

Returns the unified candidate set that may need guide-ship action:
the union of disk directories, plan-handoff names, iteration entries
(not archived), openspec/* branches, and openspec/* worktree branches.
Each candidate carries normalized fields and a ``flags`` list.

Usage::

    rddf discover-ship-changes [--json|--pretty] [--project-root <path>]

Output is a JSON array; one entry per candidate, ordered by priority
(in_progress > executable > others).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def cmd_discover_ship_changes(args: list[str]) -> int:
    """Handle ``rddf discover-ship-changes [--json|--pretty]``.

    Args:
        args: Subcommand args. Recognized: ``--json``, ``--pretty``,
            ``--project-root <path>``. ``--json`` and ``--pretty`` are
            synonymous for this subcommand (kept for symmetry with
            ``rddf dashboard``).

    Returns:
        0 on success, 1 on error.
    """
    project_root = os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()
    pretty = False
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("--json", "--pretty"):
            pretty = True
        elif a == "--project-root":
            i += 1
            if i >= len(args):
                print("❌ discover-ship-changes: --project-root needs a value", file=sys.stderr)
                return 1
            project_root = args[i]
        elif a in ("-h", "--help"):
            _print_help()
            return 0
        else:
            print(f"❌ discover-ship-changes: unknown arg {a!r}", file=sys.stderr)
            _print_help()
            return 1
        i += 1

    try:
        from skills._lib.discover_ship_changes import discover
    except ImportError as e:
        print(f"❌ discover-ship-changes: import failed: {e}", file=sys.stderr)
        return 1

    try:
        candidates = [c.to_dict() for c in discover(Path(project_root))]
    except Exception as e:
        print(f"❌ discover-ship-changes: {e}", file=sys.stderr)
        return 1

    if pretty:
        print(json.dumps(candidates, indent=2))
    else:
        print(json.dumps(candidates))
    return 0


def _print_help() -> None:
    print("usage: rddf discover-ship-changes [--json|--pretty] [--project-root <path>]")
    print()
    print("Print the unified candidate set as JSON (one entry per change).")
    print()
    print("flags:")
    print("  --json, --pretty   Pretty-print JSON output")
    print("  --project-root <p> Override project root (default: $RDDF_PROJECT_ROOT or cwd)")


__all__ = ["cmd_discover_ship_changes"]