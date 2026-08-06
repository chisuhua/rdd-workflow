#!/usr/bin/env python3
"""Entry-point script for _lib/plan_done_gate.sh::write_plan_handoff.

Reads env vars:
- PROJECT_ROOT (required)
- ACTIVE_CHANGES_COUNT (number, optional — auto-computed from filesystem if unset)
- CURRENT_CHANGE (name of first active change, optional — auto-computed)

All values flow through os.environ only — no bash string interpolation.
Oracle C1 safe.
"""
import os
import sys
from pathlib import Path


def main():
    project_root = os.environ.get("PROJECT_ROOT")
    if not project_root:
        print("ERROR: PROJECT_ROOT env var not set", file=sys.stderr)
        sys.exit(1)

    # Compute repo root from this script's location (grandparent of _lib/).
    # Needed when PROJECT_ROOT points to a temp/scratch directory.
    _repo_root = str(Path(__file__).resolve().parent.parent.parent)
    if _repo_root not in sys.path:
        sys.path.insert(0, _repo_root)

    from skills.guide_plan.scripts import plan_done_gate as pdg

    # Auto-compute CHANGE_COUNT + CURRENT_CHANGE if not provided
    active_changes_dir = os.path.join(project_root, "openspec", "changes")
    changes = []
    if os.path.isdir(active_changes_dir):
        for entry in sorted(os.listdir(active_changes_dir)):
            full = os.path.join(active_changes_dir, entry)
            if os.path.isdir(full) and entry != "archive":
                changes.append(entry)

    change_count_str = os.environ.get("ACTIVE_CHANGES_COUNT")
    current_change = os.environ.get("CURRENT_CHANGE")
    if change_count_str is not None and change_count_str != "":
        change_count = int(change_count_str)
    else:
        change_count = len(changes)
    if current_change is None or current_change == "":
        current_change = changes[0] if changes else ""

    result = pdg.write_plan_handoff(
        project_root=project_root,
        change_count=change_count,
        current_change=current_change,
    )

    print(
        "✅ Handoff state written: .rddf/state/.plan-handoff.json "
        f"(active_changes={result['active_changes']}, "
        f"current_change={result['current_change']})"
    )


if __name__ == "__main__":
    main()
