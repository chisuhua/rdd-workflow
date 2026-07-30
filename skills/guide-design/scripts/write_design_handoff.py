"""skills/guide-design/scripts/write_design_handoff.py — write .design-handoff.json (v1 schema).

Extracted from add-guide-design-phase change design.md §2.1 Phase 5.
Env-var only pattern (Oracle C1): receives PROJECT_ROOT and PROPOSALS_REVIEWED
via environment variables, no bash string interpolation.
"""

import json
import os
from datetime import datetime, timezone


def write_design_handoff(project_root: str, proposals_reviewed: int) -> dict:
    """Build and write .rddf/state/.design-handoff.json. Returns the written dict.

    Args:
        project_root: Absolute path to project root.
        proposals_reviewed: Number of proposals with decisions (approved+rejected+deferred).

    Returns:
        Dict matching design_handoff_schema.json v1 structure.
    """
    handoff = {
        "design_complete_at": datetime.now(timezone.utc).isoformat(),
        "proposals_reviewed": proposals_reviewed,
        "all_proposals_have_decision": True,
        "version": 1,
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
    try:
        proposals_reviewed = int(proposals_raw)
    except (ValueError, TypeError):
        proposals_reviewed = 0

    result = write_design_handoff(project_root, proposals_reviewed)
    print(f"✅ design-handoff written: {result['design_complete_at']}")
    print(f"   proposals reviewed: {proposals_reviewed}")