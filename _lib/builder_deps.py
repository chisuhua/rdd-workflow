"""Phase 1.5 deps + execution_mode decision (per spec §3.4, Oracle C2).

Reuses ADR-0024 execution_mode matrix; absorbs guide-plan's deps responsibilities.

ADR-0048 (2026-09-09) addition: `read_planner_recommended_route` reads
.planner-handoff.json::recommended_route for rdd-builder P0 dispatch-quick
decision (option 5). NOT used in decide_execution_mode (which only runs in
P1.5); only consumed at P0 approval gate.
"""
from pathlib import Path
import json

RISK_KEYWORDS = {"refactor", "migration", "breaking", "schema-change"}


def decide_execution_mode(file_count: int, task_count: int, risk_keywords: list) -> dict:
    rules_hit = []
    if file_count > 2:
        rules_hit.append(f"files={file_count}>2")
    if task_count > 3:
        rules_hit.append(f"tasks={task_count}>3")
    risk_overlap = set(risk_keywords) & RISK_KEYWORDS
    if risk_overlap:
        rules_hit.append(f"risk_keyword={sorted(risk_overlap)}")
    if rules_hit:
        return {"mode": "worktree", "reason": " AND ".join(rules_hit)}
    return {"mode": "lightweight", "reason": f"files={file_count}<=2 AND tasks={task_count}<=3"}


def read_planner_recommended_route(project_root: Path) -> str:
    """Read .planner-handoff.json::recommended_route for P0 dispatch-quick decision.

    Per ADR-0048 §Decision 3, rdd-builder P0 uses this advisory signal to
    decide whether to recommend option 5 (dispatch-to-quick).

    Returns:
        "simple" | "complex" | "unknown"

    Note: Returns "unknown" if handoff missing or field absent. This is
    INTENTIONAL — rdd-builder P0 still works (just won't recommend option 5).
    """
    handoff_path = Path(project_root) / ".rddf" / "state" / ".planner-handoff.json"
    if not handoff_path.exists():
        return "unknown"
    try:
        with open(handoff_path) as f:
            handoff = json.load(f)
    except (json.JSONDecodeError, OSError):
        return "unknown"
    route = handoff.get("recommended_route", "unknown")
    if route not in {"simple", "complex", "unknown"}:
        return "unknown"
    return route


def analyze_deps(
    change_name: str,
    proposal_path: str,
    manual_deps: list,
    cross_repo: bool,
    hub_issue_status=None,
) -> dict:
    deps_status = {
        "blockers": [],
        "manual_deps": list(manual_deps),
        "cross_repo_pending": [],
    }
    if cross_repo and hub_issue_status == "pending":
        deps_status["cross_repo_pending"].append("hub_issue_pending")
    return deps_status


def analyze_deps_with_strict_gate(blockers: list) -> dict:
    if blockers:
        return {"passes": False, "failures": blockers, "warnings": [], "passes_list": []}
    return {"passes": True, "failures": [], "warnings": [], "passes_list": ["strict_deps_gate"]}