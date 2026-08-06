"""``rddf archive-sync`` subcommand handler.

Created: add-archive-post-commit-hook-and-force-flag (P0, 2026-08-05).
Purpose: manually reconcile iteration.json entries that drifted from
the actual archive state. Covers the gaps left by tools that bypass
``archive.sh::archive_change`` (e.g. bare ``git mv`` + ``openspec
archive`` + ``git commit`` without the post-commit hook installed).

Reuses ``sync_iteration_after_archive`` from
``skills._lib/iteration/post_archive.py`` (shipped via
fix-archive-iteration-sync). The helper is fail-open and idempotent,
so this CLI is safe to run repeatedly.

Usage::

    rddf archive-sync <name1> [name2 ...]
    rddf archive-sync --all    # reconcile every change whose
                               # openspec dir is missing but whose
                               # archive dir exists

Exit codes:
    0: all names reconciled (helper returned None)
    1: at least one name produced a warning (helper returned a string)
    2: invalid usage (no names provided)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List


def _resolve_archive_dirs(project_root: str) -> List[str]:
    """Return change names whose openspec/changes/<name>/ is missing
    but whose openspec/changes/archive/<date>-<name>/ exists.

    Used by ``--all`` to find candidates for reconciliation.
    """
    archive_base = Path(project_root) / "openspec" / "changes" / "archive"
    if not archive_base.is_dir():
        return []

    # Collect every name that appears in any archive dir.
    archived_names = set()
    for child in archive_base.iterdir():
        if not child.is_dir():
            continue
        # Format: YYYY-MM-DD-<name>; skip entries without the date prefix
        parts = child.name.split("-", 3)
        if len(parts) < 4:
            continue
        name = parts[3]
        active_dir = Path(project_root) / "openspec" / "changes" / name
        if not active_dir.is_dir():
            archived_names.add(name)
    return sorted(archived_names)


def cmd_archive_sync(args: list[str]) -> int:
    """Handle ``rddf archive-sync <name1> [name2 ...] [--all]``.

    Args:
        args: Positional change names. ``--all`` reconciles every
            drift candidate (see ``_resolve_archive_dirs``).

    Returns:
        0 on full success; 1 if any helper call returned a warning;
        2 on invalid usage.
    """
    project_root = os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()

    if not args:
        print(
            "❌ archive-sync: no change names provided. "
            "Usage: rddf archive-sync <name1> [name2 ...] [--all]",
            file=sys.stderr,
        )
        return 2

    # Lazy import keeps the CLI import-safe (mirrors other cmd modules).
    from skills._lib.iteration import post_archive as pa

    if args == ["--all"]:
        names = _resolve_archive_dirs(project_root)
        if not names:
            print("ℹ️  archive-sync: no drift candidates found")
            return 0
        print(f"📋 archive-sync: reconciling {len(names)} drift candidate(s)")
    else:
        names = args

    failure_count = 0
    for name in names:
        result = pa.sync_iteration_after_archive(
            project_root=project_root,
            change_name=name,
            archive_commit_sha=None,
        )
        if result is None:
            print(f"✅ {name}: iteration.json updated")
        else:
            print(f"⚠️  {name}: {result}")
            failure_count += 1

    if failure_count:
        print(
            f"\n⚠️  archive-sync: {failure_count}/{len(names)} change(s) had warnings",
            file=sys.stderr,
        )
        return 1
    print(f"\n✅ archive-sync: {len(names)} change(s) reconciled")
    return 0


__all__ = ["cmd_archive_sync"]
