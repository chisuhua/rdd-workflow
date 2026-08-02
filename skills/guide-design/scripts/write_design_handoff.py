"""skills/guide-design/scripts/write_design_handoff.py — write .design-handoff.json (v2 schema).

Extracted from add-guide-design-phase change design.md §2.1 Phase 5.
v2 schema (D3 of move-proposal-creation-to-design) adds `changes_pre_created`
so guide-plan intake can skip already-built changes.

Env-var only pattern (Oracle C1): receives PROJECT_ROOT, PROPOSALS_REVIEWED,
and CHANGES_PRE_CREATED (comma-separated) via environment variables, no bash
string interpolation into Python code.
"""

import json
import os
from datetime import datetime, timezone


def write_design_handoff(
    project_root: str,
    proposals_reviewed: int,
    changes_pre_created: list[str] | None = None,
) -> dict:
    """Build and write .rddf/state/.design-handoff.json (v2). Returns the written dict.

    Args:
        project_root: Absolute path to project root.
        proposals_reviewed: Number of proposals with decisions (approved+rejected+deferred).
        changes_pre_created: List of change names created during design approve.
            Consumed by guide-plan intake to skip recreation. Defaults to empty.

    Returns:
        Dict matching design_handoff_schema.json v2 structure.
    """
    if changes_pre_created is None:
        changes_pre_created = []

    handoff = {
        "design_complete_at": datetime.now(timezone.utc).isoformat(),
        "proposals_reviewed": proposals_reviewed,
        "all_proposals_have_decision": True,
        "version": 2,
        "changes_pre_created": list(changes_pre_created),
    }

    state_dir = os.path.join(project_root, ".rddf", "state")
    os.makedirs(state_dir, exist_ok=True)
    handoff_path = os.path.join(state_dir, ".design-handoff.json")
    with open(handoff_path, "w") as f:
        json.dump(handoff, f, indent=2)

    return handoff


if __name__ == "__main__":
    project_root = os.environ.get("PROJECT_ROOT", os.getcwd())
    proposals_raw = os.environ.get("PROPOSALS_REVIEWED", "0")
    pre_created_raw = os.environ.get("CHANGES_PRE_CREATED", "")

    try:
        proposals_reviewed = int(proposals_raw)
    except (ValueError, TypeError):
        proposals_reviewed = 0

    changes_pre_created = [n.strip() for n in pre_created_raw.split(",") if n.strip()]

    result = write_design_handoff(project_root, proposals_reviewed, changes_pre_created)
    print(f"✅ design-handoff v2 written: {result['design_complete_at']}")
    print(f"   proposals reviewed: {proposals_reviewed}")
    print(f"   changes pre-created: {changes_pre_created}")
