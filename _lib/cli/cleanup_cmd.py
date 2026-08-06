"""``rddf cleanup`` subcommand handler.

Display-only listing of git worktrees and orphan ``openspec/`` branches.
Never deletes anything. Ported from the old bash ``rddf_cleanup()`` at
``./rddf`` lines 860-910.

Usage::

    python3 -m skills._lib.cli cleanup

The project root is injected by ``cli.__main__`` via the
``RDDF_PROJECT_ROOT`` env var; falls back to ``os.getcwd()`` when unset.
"""
from __future__ import annotations

import os
import subprocess

from skills._lib.state_reader import list_worktrees


def cmd_cleanup(args: list[str]) -> int:
    """List openspec worktrees and orphan branches (display-only, no deletion).

    Args:
        args: Unused (reserved for future flags).

    Returns:
        0 always (display-only command).
    """
    # --help handling
    if any(a in ("-h", "--help") for a in args):
        _print_help()
        return 0

    project_root = os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()

    print("🧹 清理孤立 Worktree 和 Branch")
    print("──")

    # ── Worktrees ──────────────────────────────────────────────
    all_wts = list_worktrees()
    openspec_wts = [wt for wt in all_wts if wt.get("is_openspec")]

    if not openspec_wts:
        print(" (无 openspec worktree)")
    else:
        print(" 发现 openspec worktree:")
        for wt in openspec_wts:
            path = wt.get("path") or "?"
            branch = wt.get("branch") or "?"
            change_name = branch.replace("refs/heads/openspec/", "", 1)
            print(f"   · {path} → openspec/{change_name}")

    # ── Orphan branches ───────────────────────────────────────
    try:
        result = subprocess.run(
            ["git", "branch", "--list", "openspec/*"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=project_root,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        print("  (git branch listing failed)")
        return 0

    orphan_branches = [
        line.strip().lstrip("* ")
        for line in result.stdout.splitlines()
        if line.strip()
    ]

    # Build set of branches that have an active worktree.
    active_branches = {
        wt.get("branch", "").replace("refs/heads/", "", 1)
        for wt in all_wts
        if wt.get("branch")
    }

    orphans = [b for b in orphan_branches if b not in active_branches]

    if not orphans:
        print(" (无孤立分支)")
    else:
        print(" 孤立分支:")
        for br in orphans:
            print(f"   · {br}")

    return 0


def _print_help() -> None:
    print("usage: rddf cleanup")
    print()
    print("List openspec worktrees and orphan openspec/ branches.")
    print("Display-only — no deletion performed.")
    print()
    print("  example:")
    print("    rddf cleanup")


__all__ = ["cmd_cleanup"]