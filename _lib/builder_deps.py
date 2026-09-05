"""Phase 1.5 deps + execution_mode decision (per spec §3.4, Oracle C2).

Reuses ADR-0024 execution_mode matrix; absorbs guide-plan's deps responsibilities.
"""
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