"""planner-handoff.json v1 read/write/validate (per spec §3.3 + §6.1 + ADR-0048).

Env-var pattern (Oracle C1): receives PROJECT_ROOT, PROPOSALS_READY,
PROPOSALS_APPROVED_COUNT, FEATURES_ACTIVE, CURRENT_SPRINT, AWAITING_BUILDER,
RECOMMENDED_ROUTE via env vars.

v1.1 (per ADR-0048, 2026-09-09): added recommended_route as REQUIRED field,
consumed by rdd-builder P0 dispatch-quick decision (option 5).

v1.0 (per fix-v4-rdd-planner-scope-over-assignment): proposals_authored →
proposals_ready rename.

Backward compat: coexists with .planner-state.json (Stage 2) and
.planner-feedback.json (ADR-0042). Each file has its own FileLock.

KNOWN LIMITATION (per 2026-09-09 audit): write/read do NOT use FileLock +
atomic_write (unlike planner_state.py and planner_feedback.py). Single-writer
in current usage (planner_stage_exit.sh) but should be hardened before
concurrent calls. Tracked as separate fix.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def write_planner_handoff(
    project_root: str,
    proposals_ready: list,
    proposals_approved_count: int,
    features_active: list,
    current_sprint: str,
    awaiting_builder: list | None = None,
    recommended_route: str = "unknown",
) -> dict:
    """Write .planner-handoff.json v1.1 with REQUIRED recommended_route field.

    Args:
        project_root: absolute path to project root
        proposals_ready: list of proposal names ready for builder
        proposals_approved_count: integer count
        features_active: list of feature names
        current_sprint: e.g. "sprint-2026-09"
        awaiting_builder: list of change names waiting for builder P0
        recommended_route: enum "simple"|"complex"|"unknown" (per ADR-0048 §Decision 2)
                          Default "unknown" means planner has not computed advisory;
                          caller (planner_stage_exit.sh) should pass computed value.
    """
    handoff = {
        "schema": "planner-handoff-v1",
        "version": 1,
        "owner": "rdd-planner",
        "planner_complete_at": datetime.now(timezone.utc).isoformat(),
        "current_sprint": current_sprint,
        "proposals_ready": list(proposals_ready),
        "proposals_approved_count": proposals_approved_count,
        "features_active": list(features_active),
        "awaiting_builder": list(awaiting_builder or []),
        "recommended_route": recommended_route,
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
    proposals_ready = [p for p in os.environ.get("PROPOSALS_READY", "").split(",") if p.strip()]
    proposals_approved_count = int(os.environ.get("PROPOSALS_APPROVED_COUNT", "0"))
    features_active = [p for p in os.environ.get("FEATURES_ACTIVE", "").split(",") if p.strip()]
    awaiting_builder = [p for p in os.environ.get("AWAITING_BUILDER", "").split(",") if p.strip()]
    current_sprint = os.environ.get("CURRENT_SPRINT", f"sprint-{datetime.now().strftime('%Y-%m')}")
    recommended_route = os.environ.get("RECOMMENDED_ROUTE", "unknown")
    if recommended_route not in {"simple", "complex", "unknown"}:
        raise ValueError(f"RECOMMENDED_ROUTE must be simple|complex|unknown, got {recommended_route!r}")
    result = write_planner_handoff(
        project_root, proposals_ready, proposals_approved_count,
        features_active, current_sprint, awaiting_builder,
        recommended_route=recommended_route,
    )
    print(f"planner-handoff v1.1 written: {result['planner_complete_at']} (recommended_route={result['recommended_route']})")