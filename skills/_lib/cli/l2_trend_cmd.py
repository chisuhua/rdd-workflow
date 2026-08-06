"""``rddf l2-trend`` subcommand handler.

Created: collect-l2-violation-count-on-archive (P2, 2026-08-05).
Prints a chronological table of archived changes with their recorded
L2 violation count after archive.
"""
from __future__ import annotations

import os
import sys


def cmd_l2_trend(args: list[str]) -> int:
    """Handle ``rddf l2-trend``.

    Args:
        args: Ignored (no flags yet).

    Returns:
        0 always.
    """
    project_root = os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()
    iter_path = os.path.join(project_root, ".rddf", "state", "iteration.json")

    if not os.path.isfile(iter_path):
        print("📭 iteration.json not found — no L2 trend data available")
        return 0

    try:
        from skills._lib.iteration.store import list_archived, load

        data = load(project_root)
    except Exception as e:
        print(f"❌ l2-trend: failed to load iteration.json: {e}", file=sys.stderr)
        return 1

    archived = list_archived(data)
    if not archived:
        print("(no archived changes)")
        return 0

    archived = sorted(
        archived,
        key=lambda c: (c.get("archived_at") or "")
    )

    print("📉 L2 violation count trend")
    print()
    print(f"{'Change':<40} {'L2 count':<10} {'Archived at':<24}")
    print(f"{'-' * 40} {'-' * 10} {'-' * 24}")
    for c in archived:
        name = c.get("name", "?")[:40]
        count = c.get("l2_violation_count_after")
        count_disp = str(count) if count is not None else "not recorded"
        archived_at = c.get("archived_at") or "-"
        print(f"{name:<40} {count_disp:<10} {archived_at:<24}")

    return 0


__all__ = ["cmd_l2_trend"]
