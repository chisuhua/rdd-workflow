"""Single CLI entry point: ``python3 -m skills._lib.cli <subcommand> [args...]``.

Responsibilities (per ``docs/superpowers/specs/2026-07-20-dashboard-design.md``
§4.3):

1. **Worktree-safe project root**: use ``git rev-parse --git-common-dir``
   (NOT ``--show-toplevel``). Inside a worktree, ``--show-toplevel``
   returns the worktree path, but state files (``.rddf/state/``) live
   in the main repo. ``--git-common-dir`` returns ``<main>/.git`` for
   the main repo and ``<main>/.git/worktrees/<name>`` for a worktree;
   we strip back to the main repo root in both cases.

2. **Worktree detection**: if running inside a worktree, print an info
   line ``ℹ️  running from worktree, reading state from <main_repo>``
   so the user understands why state is being read from elsewhere.

3. **Non-rdd-workflow project detection**: if ``.rddf/state/`` does
   not exist at the resolved project root, print
   ``ℹ️  not a rdd-workflow project`` and exit 0 (this is not an
   error - the user may have invoked the CLI from the wrong dir and
   a non-zero exit would surprise them).

4. **Subcommand routing**: delegate to :func:`skills._lib.cli.route`.
   Unknown subcommand -> ``❌ unknown command: <name>`` + exit 2.

This module is intentionally thin: all rendering logic lives in the
``*_cmd.py`` handler modules and the libraries they delegate to
(``dashboard``, ``iteration``, ``rddf_session``).
"""
from __future__ import annotations

import os
import subprocess
import sys

from skills._lib.cli import list_commands, route


def resolve_project_root() -> str:
    """Return the main git repo root, worktree-safe.

    Uses ``git rev-parse --git-common-dir`` which returns:
      - ``<main>/.git`` when run in the main repo
      - ``<main>/.git/worktrees/<name>`` when run in a linked worktree

    We strip the trailing ``/.git`` (or ``/.git/worktrees/<name>``) to
    recover the main repo root in both cases.

    Falls back to ``os.getcwd()`` if git is unavailable or the cwd is
    not inside a git repo (so the non-rdd-workflow detection below
    still gets a chance to run and print a friendly message).
    """
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return os.getcwd()
    if r.returncode != 0:
        return os.getcwd()

    common_dir = r.stdout.strip()
    if not common_dir:
        return os.getcwd()
    # git rev-parse --git-common-dir may return a relative path (e.g. ".git")
    # when run from the repo root. Resolve to absolute before pattern matching.
    if not os.path.isabs(common_dir):
        common_dir = os.path.abspath(common_dir)

    if "/.git/worktrees/" in common_dir:
        # common_dir is "<main>/.git/worktrees/<name>"; main root is 3 levels up
        return os.path.abspath(os.path.join(common_dir, "..", "..", ".."))
    if common_dir.endswith("/.git"):
        return os.path.abspath(os.path.join(common_dir, ".."))
    # Bare repo or unusual layout - dirname is the best we can do.
    return os.path.dirname(common_dir)


def _is_in_worktree() -> bool:
    """Return True if cwd is inside a linked worktree (not the main repo).

    Compares ``git rev-parse --git-common-dir`` against
    ``git rev-parse --git-dir``: in the main repo they are equal; in a
    linked worktree they differ (common-dir points to ``<main>/.git``,
    git-dir points to ``<main>/.git/worktrees/<name>``).
    """
    try:
        common = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        git_dir = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False
    if common.returncode != 0 or git_dir.returncode != 0:
        return False
    c = os.path.abspath(common.stdout.strip())
    g = os.path.abspath(git_dir.stdout.strip())
    return c != g


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns a process exit code.

    Args:
        argv: Argument list (excluding the program name). Defaults to
            ``sys.argv[1:]`` when ``None``.
    """
    if argv is None:
        argv = sys.argv[1:]

    if not argv or argv[0] in ("-h", "--help", "help"):
        _print_help()
        return 0

    subcommand = argv[0]
    rest = argv[1:]

    # Legacy alias: ``session`` → ``sessions`` (bash rddf had this alias).
    _ALIASES = {"session": "sessions"}
    subcommand = _ALIASES.get(subcommand, subcommand)

    # Validate subcommand name BEFORE resolving project root so that
    # ``rddf help`` and unknown-command errors don't pay the git cost.
    if subcommand not in list_commands():
        print(f"❌ unknown command: {subcommand}", file=sys.stderr)
        print(f"   available: {', '.join(list_commands())}", file=sys.stderr)
        return 2

    project_root = resolve_project_root()

    # Worktree detection + info line (only when actually in a worktree).
    if _is_in_worktree():
        print(f"ℹ️  running from worktree, reading state from {project_root}")

    # Non-rdd-workflow project detection.
    state_dir = os.path.join(project_root, ".rddf", "state")
    if not os.path.isdir(state_dir):
        print(f"ℹ️  not a rdd-workflow project (no {state_dir})")
        return 0

    # Inject project_root as an env var so handlers can read it
    # without re-resolving. Handlers import this via os.environ.
    os.environ["RDDF_PROJECT_ROOT"] = project_root

    try:
        return route(subcommand, rest)
    except Exception as e:  # pragma: no cover - defensive
        print(f"❌ {subcommand} failed: {e}", file=sys.stderr)
        return 1


def _print_help() -> None:
    """Print top-level help to stdout."""
    print("usage: python3 -m skills._lib.cli <subcommand> [args...]")
    print()
    print("subcommands:")
    print("  archive <n>  Archive a change (merge → openspec archive → cleanup)")
    print("  cleanup      Clean orphaned worktrees and branches")
    print("  dashboard    Unified dashboard (7 sections). Flags: --json, --plain")
    print("  deps         Dependency analysis table from deps-analysis.json")
    print("  discover-ship-changes  Unified change candidates for guide-ship")
    print("  feature      Feature grouping (summary, graph, status, order)")
    print("  guide        Project state scan + recommendation (guide-arch/guide-plan/guide-ship)")
    print("  init [tgt]   Install rdd-workflow to target's .opencode/skills/")
    print("  iteration    Validate iteration.json (lint, allowed-fields)")
    print("  l2-trend     L2 violation count trend for archived changes")
    print("  monitor      Live monitor (--watch=<sec>)")
    print("  sessions     Session management (read-only). Subcmds: show <id>, current, gc")
    print("  status       Change status overview. Flags: --iteration, --roadmap, <name>")
    print("  validate     Quality gate checks")
    print("  version      Print rddf version")
    print()
    print(f"available: {', '.join(list_commands())}")


if __name__ == "__main__":
    sys.exit(main())
