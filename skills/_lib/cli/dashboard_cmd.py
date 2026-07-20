"""``rddf dashboard`` subcommand handler.

Parses ``--json`` / ``--plain`` flags, delegates to
``skills._lib.dashboard.collect()`` to assemble a ``DashboardData``
instance, then ``skills._lib.dashboard.renderer.render()`` to format
it. All state reads are read-only (the dashboard package never writes
to any state file - see ``state_reader.py``'s read-only contract).

Usage::

    python3 -m skills._lib.cli dashboard            # terminal (auto-degrade)
    python3 -m skills._lib.cli dashboard --json     # JSON for scripts/CI
    python3 -m skills._lib.cli dashboard --plain    # ASCII-only

The project root is injected by ``cli.__main__`` via the
``RDDF_PROJECT_ROOT`` env var; we fall back to ``os.getcwd()`` if it
is unset (e.g. when the handler is called directly from a test).
"""
from __future__ import annotations

import os
import sys


def cmd_dashboard(args: list[str]) -> int:
    """Handle ``rddf dashboard [--json|--plain]``.

    Args:
        args: Subcommand args after the ``dashboard`` token, e.g.
            ``["--json"]`` or ``[]``.

    Returns:
        0 on success, 1 on error.
    """
    # Parse flags - any of --json / --plain selects the corresponding
    # mode; default (no flag) lets the renderer auto-degrade based on
    # isatty(stdout).
    mode = "terminal"
    for flag in args:
        if flag == "--json":
            mode = "json"
        elif flag == "--plain":
            mode = "plain"
        elif flag in ("-h", "--help"):
            _print_help()
            return 0
        else:
            print(f"❌ dashboard: unknown flag {flag!r}", file=sys.stderr)
            print("   usage: rddf dashboard [--json|--plain]", file=sys.stderr)
            return 1

    project_root = os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()

    # Lazy imports so ``rddf help`` and other subcommands don't pay the
    # cost of importing the dashboard package + state_reader + iteration.
    try:
        from skills._lib.dashboard import collect
        from skills._lib.dashboard.renderer import render
    except ImportError as e:
        print(f"❌ dashboard: failed to import dashboard package: {e}", file=sys.stderr)
        return 1

    try:
        data = collect(project_root)
        output = render(data, mode=mode)
    except Exception as e:
        print(f"❌ dashboard: {e}", file=sys.stderr)
        return 1

    sys.stdout.write(output)
    return 0


def _print_help() -> None:
    print("usage: rddf dashboard [--json|--plain]")
    print()
    print("Show the unified 7-section dashboard.")
    print()
    print("flags:")
    print("  --json    Output as a single JSON object (for scripts/CI)")
    print("  --plain   ASCII-only output (no emoji, no box-drawing)")
    print("  (default) Terminal mode with auto-degrade to plain when piped")


__all__ = ["cmd_dashboard"]
