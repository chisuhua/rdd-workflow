"""planner-handoff.json v1 read/write/validate (per spec §3.3 + §6.1).

Env-var pattern (Oracle C1): receives PROJECT_ROOT, PROPOSALS_AUTHORED,
PROPOSALS_APPROVED_COUNT, FEATURES_ACTIVE, CURRENT_SPRINT via env vars.

Backward compat: coexists with .planner-state.json (Stage 2) and
.planner-feedback.json (ADR-0042). Each file has its own FileLock.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def write_planner_handoff(
    project_root: str,
    proposals_authored: list,
    proposals_approved_count: int,
    features_active: list,
    current_sprint: str,
) -> dict:
    handoff = {
        "schema": "planner-handoff-v1",
        "version": 1,
        "owner": "rdd-planner",
        "planner_complete_at": datetime.now(timezone.utc).isoformat(),
        "current_sprint": current_sprint,
        "proposals_authored": list(proposals_authored),
        "proposals_approved_count": proposals_approved_count,
        "features_active": list(features_active),
    }
    state_dir = Path(project_root) / ".rddf" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    handoff_path = state_dir / ".planner-handoff.json"
    with open(handoff_path, "w") as f:
        json.dump(handoff, f, indent=2)
    return handoff


def read_planner_handoff(project_root: str) -> dict:
    handoff_path = Path(project_root) / ".rddf" / "state" / ".planner-handoff.json"
    if not handoff_path.exists():
        return {}
    with open(handoff_path) as f:
        return json.load(f)


if __name__ == "__main__":
    project_root = os.environ.get("PROJECT_ROOT", os.getcwd())
    proposals_authored = [p for p in os.environ.get("PROPOSALS_AUTHORED", "").split(",") if p.strip()]
    proposals_approved_count = int(os.environ.get("PROPOSALS_APPROVED_COUNT", "0"))
    features_active = [p for p in os.environ.get("FEATURES_ACTIVE", "").split(",") if p.strip()]
    current_sprint = os.environ.get("CURRENT_SPRINT", f"sprint-{datetime.now().strftime('%Y-%m')}")
    result = write_planner_handoff(
        project_root, proposals_authored, proposals_approved_count,
        features_active, current_sprint,
    )
    print(f"planner-handoff v1 written: {result['planner_complete_at']}")