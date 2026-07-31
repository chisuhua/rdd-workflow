"""Plan-done gate validator + plan-handoff writer.

Extracted from skills/guide-plan.md lines 518-677 (~150-line inline bash block).

Two responsibilities:
1. Triple-gate validation (bash) — Gate 0 (ready-for-ship), Gate 1 (active changes
   count >= 1), Gate 2 (artifacts committed). See plan_done_gate.sh.
2. Handoff writer (Python + bash) — Writes .rddf/state/.plan-handoff.json with
   5 fields: plan_complete_at, active_changes, all_artifacts_committed,
   ship_started_at (null), current_change.

Public function:
- write_plan_handoff(): Build and write .plan-handoff.json. Returns the written dict.

Gate validation (run_plan_done_gate) is bash-only — it involves git operations
and Python iteration module calls that don't map cleanly to a single Python function.
"""

import json
import os
from datetime import datetime, timezone


def write_plan_handoff(
    project_root: str,
    change_count: int,
    current_change: str,
) -> dict:
    """Build and write .plan-handoff.json. Returns the written dict.

    Args:
        project_root: Absolute path to project root.
        change_count: Number of active changes (from gate validation).
        current_change: Name of first active change (or "" if none).

    Returns:
        Dict matching plan-handoff schema with 6 fields:
        - plan_complete_at: ISO timestamp (UTC)
        - active_changes: int
        - all_artifacts_committed: bool (always True — gating is upstream)
        - ship_started_at: None (initial value)
        - current_change: str
        - execution_mode_decisions: dict mapping change_name -> {mode, reason}
    """
    handoff = {
        "plan_complete_at": datetime.now(timezone.utc).isoformat(),
        "active_changes": change_count,
        "all_artifacts_committed": True,
        "ship_started_at": None,
        "current_change": current_change,
        "execution_mode_decisions": _load_execution_mode_decisions(project_root),
    }

    state_dir = os.path.join(project_root, ".rddf", "state")
    os.makedirs(state_dir, exist_ok=True)
    handoff_path = os.path.join(state_dir, ".plan-handoff.json")
    with open(handoff_path, "w") as f:
        json.dump(handoff, f, indent=2)

    return handoff


def _load_execution_mode_decisions(project_root: str) -> dict:
    """Load execution_mode_recommendations from deps-analysis.json.

    Only keeps entries whose change has an active (non-archive) directory
    under openspec/changes/, filtering stale decisions for archived changes.

    Returns empty dict if deps-analysis.json missing or malformed.
    """
    deps_path = os.path.join(project_root, ".rddf", "state", "deps-analysis.json")
    if not os.path.isfile(deps_path):
        return {}

    try:
        with open(deps_path, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}

    recommendations = data.get("execution_mode_recommendations", {})
    if not recommendations:
        return {}

    active_dir = os.path.join(project_root, "openspec", "changes")
    active_names = set()
    if os.path.isdir(active_dir):
        for entry in os.listdir(active_dir):
            entry_path = os.path.join(active_dir, entry)
            if os.path.isdir(entry_path) and entry != "archive":
                active_names.add(entry)

    return {
        name: rec
        for name, rec in recommendations.items()
        if name in active_names
    }
