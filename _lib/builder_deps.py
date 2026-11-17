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

# The structured risk vocabulary: `roadmap-meta.yaml` declares `risk: normal|high`.
# `high` means "this change is risky" without naming a category, so it maps to
# the whole risky vocabulary — the intersection inside decide_execution_mode()
# then fires. (The word list itself is unchanged; only the INPUT changes.)
RISK_LEVEL_KEYWORDS = {"high": sorted(RISK_KEYWORDS)}

# Capability flag: is the `lightweight` execution mode actually usable?
#
# The mode is only usable when it (a) creates the `openspec/<change>` branch and
# (b) its archive path merges / cleans / syncs. Until both are true, deciding
# "lightweight" produces changes that CANNOT be archived (the verifier's anchor
# is the branch tip, and a branch that does not exist fails closed).
#
# Fail-safe by construction: if the flag is forgotten, the mode stays disabled
# (slower, but correct) — the opposite of silently enabling a broken mode.
# Owner: `fix-lightweight-branch-and-archive` flips it together with its
# implementation (ADR-0036 §Verification V-G).
LIGHTWEIGHT_EXECUTION_READY = False


def decide_execution_mode(file_count: int, task_count: int, risk_keywords: list) -> dict:
    """Decide worktree vs lightweight (thresholds per ADR-0024, unchanged).

    `file_count` / `task_count` may be None (= unknown):
      * `file_count=None` → the file rule does NOT participate (an unknown
        input must not be read as "small"); the reason says `files=unknown`.
      * `task_count=None` → fail-closed: worktree, reason `tasks=unknown`.
    """
    rules_hit = []
    if file_count is None:
        rules_hit.append("files=unknown")
    elif file_count > 2:
        rules_hit.append(f"files={file_count}>2")
    if task_count is None:
        rules_hit.append("tasks=unknown")
    elif task_count > 3:
        rules_hit.append(f"tasks={task_count}>3")
    risk_overlap = set(risk_keywords or []) & RISK_KEYWORDS
    if risk_overlap:
        rules_hit.append(f"risk_keyword={sorted(risk_overlap)}")
    if rules_hit:
        return {"mode": "worktree", "reason": " AND ".join(rules_hit)}
    summary = f"files={file_count}<=2 AND tasks={task_count}<=3"
    if not LIGHTWEIGHT_EXECUTION_READY:
        # The mode exists in the contract but is not usable yet (ADR-0036 V-G):
        # it would produce changes that cannot be archived.
        return {
            "mode": "worktree",
            "reason": (
                f"{summary}, 但 lightweight 未落地"
                "（无实现分支 / 归档路径未补齐）"
            ),
        }
    return {"mode": "lightweight", "reason": summary}


def _plan_files(plan_path: Path) -> set:
    """Paths listed in a plan's `**Files:**` blocks (deduped, no line numbers).

    Format (per skills/rdd-workflow-writing-plans/SKILL.md §plan format):
        **Files:**
        - Create: `path/to/new_file.py`
        - Modify: `path/to/existing.py:123-145`
        - Test: `tests/path/test_x.py`
    Backticks and trailing `:123-145` line ranges are stripped.
    """
    try:
        text = plan_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return set()
    paths = set()
    in_files = False
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("**Files:**"):
            in_files = True
            continue
        if in_files:
            if stripped.startswith("- ") and ":" in stripped:
                kind, _, value = stripped[2:].partition(":")
                if kind.strip() not in ("Create", "Modify", "Test"):
                    in_files = False
                    continue
                path = value.strip().strip("`").strip()
                # Strip a trailing line range: `path.py:123-145`
                path = path.split(":")[0].strip().strip("`")
                if path:
                    paths.add(path)
            elif stripped.startswith("### ") or stripped.startswith("## "):
                in_files = False
            elif stripped and not stripped.startswith("- "):
                in_files = False
    return paths


def compute_mode_inputs(project_root: str, change_name: str) -> dict:
    """Compute the REAL inputs of the execution-mode decision.

    Every path is absolute (the decision must not depend on the cwd).

    Returns:
        {
          "file_count": int | None,   # None = unknown → does not participate
          "task_count": int | None,   # None = unknown → fail-closed (worktree)
          "risk_keywords": list[str],  # from the structured declaration
          "notes": list[str],          # what was unavailable and why
        }
    """
    from _lib.tasks_count import count_tasks

    root = Path(project_root).resolve()
    notes = []

    # --- tasks: the checkbox TOTAL of tasks.md (case-insensitive) ---
    # The total (not the open count): after archiving every box is checked, and
    # an open-count would read as "0 tasks" → fail-open.
    tasks_path = root / "openspec" / "changes" / change_name / "tasks.md"
    task_count = None
    try:
        text = tasks_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        text = None
    if text is not None:
        done, total = count_tasks(text)
        if total > 0:
            task_count = total
        else:
            notes.append("tasks=unknown (tasks.md has no checkbox)")
    else:
        notes.append("tasks=unknown (tasks.md missing)")

    # --- files: the plan's `**Files:**` paths ---
    plan_path = root / ".rddf" / "plans" / f"{change_name}.md"
    file_count = None
    if plan_path.is_file():
        paths = _plan_files(plan_path)
        if paths:
            file_count = len(paths)
        else:
            notes.append("files=unknown (plan has no `**Files:**` block)")
    else:
        notes.append("files=unknown (plan missing)")

    # --- risk: the STRUCTURED declaration (no text scanning) ---
    risk_keywords = []
    meta_path = root / "openspec" / "changes" / change_name / "roadmap-meta.yaml"
    try:
        import yaml
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001 - a missing/unreadable meta = normal risk
        meta = {}
    level = str(meta.get("risk", "normal") or "normal").strip().lower()
    if level in RISK_LEVEL_KEYWORDS:
        risk_keywords = list(RISK_LEVEL_KEYWORDS[level])
        notes.append(f"risk={level} (structured declaration)")
    elif level != "normal":
        notes.append(f"risk={level} (unknown level; treated as normal)")

    return {
        "file_count": file_count,
        "task_count": task_count,
        "risk_keywords": risk_keywords,
        "notes": notes,
    }


def compute_conflict(project_root: str, change_name: str) -> list:
    """Conflict dimension (ADR-0024's 4th row, never implemented).

    Returns a list of conflict descriptions; empty = no conflict.
      * another active change's plan touches the same files;
      * another change currently occupies a worktree (conservative: do not run
        in the main repository while another change is in flight).
    """
    root = Path(project_root).resolve()
    conflicts = []
    files = _plan_files(root / ".rddf" / "plans" / f"{change_name}.md")
    if files:
        changes_dir = root / "openspec" / "changes"
        if changes_dir.is_dir():
            for entry in sorted(changes_dir.iterdir()):
                if not entry.is_dir() or entry.name in ("archive", change_name):
                    continue
                other_plan = root / ".rddf" / "plans" / f"{entry.name}.md"
                if not other_plan.is_file():
                    continue
                overlap = files & _plan_files(other_plan)
                if overlap:
                    conflicts.append(
                        f"files overlap with change '{entry.name}': "
                        + ", ".join(sorted(overlap)[:3])
                    )
    wt_dir = root / ".rddf" / "wt"
    if wt_dir.is_dir():
        for entry in sorted(wt_dir.iterdir()):
            if entry.is_dir() and entry.name != change_name:
                conflicts.append(f"active worktree for change '{entry.name}'")
    return conflicts


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