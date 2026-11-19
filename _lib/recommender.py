"""Single source of truth for the stage recommendation ladder.

ADR-0062: the ladder that answers "which stage runs next" lives here and
nowhere else. Two consumers import it:

- ``_lib/cli/guide_cmd.py``        — the ``rddf guide`` CLI
- ``_lib/workflow_synthesizer.py`` — ``rddf monitor`` / menu rendering

The third implementation (``skills/guide/scripts/scan-state.sh``, bash) was
archived with the skill per ADR-0063, so no second ladder can drift from
this one.

Behaviour is frozen to what ``guide_cmd._scan_state`` did before the
consolidation (ADR-0062 Decision 4). ``scan_state`` returns
``(action, reason, confidence)``; the CLI ignores ``confidence`` because its
output format has never carried one.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple


def _read_json(path: Path) -> Optional[dict]:
    """Read a JSON file, returning None on missing/invalid.

    The top-level value MUST be a JSON object. A handoff whose content is
    an array (or any other non-dict) is not a valid handoff. Without this,
    a non-object handoff would be treated as "stage complete" by the
    consumers.
    """
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def openspec_worktrees(project_root: str) -> list[str]:
    """Return worktree paths that carry an ``openspec/*`` branch."""
    try:
        r = subprocess.run(
            ["git", "worktree", "list"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return []
    if r.returncode != 0:
        return []
    paths = []
    for line in r.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[2].startswith("[openspec/"):
            paths.append(parts[0])
    return paths


def _worktree_has_incomplete_tasks(worktree_path: str) -> bool:
    """Return True if any tasks.md under the worktree has unchecked tasks."""
    wt = Path(worktree_path) / "openspec" / "changes"
    if not wt.is_dir():
        return False
    for tasks_md in wt.glob("*/tasks.md"):
        try:
            content = tasks_md.read_text()
        except OSError:
            continue
        if "- [ ]" in content:
            return True
    return False


def _has_committed_change_in_head(project_root: str) -> bool:
    """Return True if HEAD contains a committed openspec/changes/<name>/."""
    changes_dir = Path(project_root) / "openspec" / "changes"
    if not changes_dir.is_dir():
        return False
    for d in changes_dir.iterdir():
        if not d.is_dir() or d.name == "archive":
            continue
        try:
            r = subprocess.run(
                ["git", "show", f"HEAD:openspec/changes/{d.name}"],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            continue
        if r.returncode == 0:
            return True
    return False


def _count_active_changes(project_root: str) -> int:
    """Number of non-archived change directories on disk.

    ``planner-handoff-v1`` defines no ``active_changes`` field — reading it
    always resolved to 0 and made every v4 project look like a leftover.
    The filesystem cannot lie.
    """
    changes_dir = Path(project_root) / "openspec" / "changes"
    if not changes_dir.is_dir():
        return 0
    return sum(
        1 for d in changes_dir.iterdir() if d.is_dir() and d.name != "archive"
    )


def scan_state(project_root: str) -> Tuple[str, str, str]:
    """Run the priority ladder; return ``(action, reason, confidence)``.

    Consumes the v4 planner handoff (``.planner-handoff.json``); the v3
    handoff files are read only as a legacy fallback.

    Never raises for filesystem/git failures: helpers return safe defaults.
    """
    state_dir = Path(project_root) / ".rddf" / "state"
    arch_handoff = state_dir / ".arch-handoff.json"
    planner_handoff = state_dir / ".planner-handoff.json"
    # v3 legacy handoffs — read ONLY as fallback, never written by v4 stages
    v3_plan_handoff = state_dir / ".plan-handoff.json"
    v3_design_handoff = state_dir / ".design-handoff.json"

    arch = _read_json(arch_handoff)
    planner = _read_json(planner_handoff)
    v3_plan = _read_json(v3_plan_handoff)
    v3_design = _read_json(v3_design_handoff)

    # Effective planner marker: the v4 handoff wins; the v3 files are a
    # read-only legacy fallback. A corrupt file does not count as a marker.
    #
    # The marker KIND matters: a v3 DESIGN handoff means "design done,
    # change generation next"; a v3 PLAN handoff means "changes exist,
    # execution/cleanup next". They are different stages.
    planner_effective = planner
    marker_kind = "v4" if planner is not None else ""
    if planner_effective is None:
        if v3_plan is not None:
            planner_effective = v3_plan
            marker_kind = "v3-plan"
        elif v3_design is not None:
            planner_effective = v3_design
            marker_kind = "v3-design"
    if marker_kind and marker_kind != "v4":
        print(
            "⚠️  legacy v3 handoff detected (.plan-handoff.json / "
            ".design-handoff.json); migrate to .planner-handoff.json",
            file=sys.stderr,
        )

    # 1c. planner-handoff present but unparsable → planner not complete.
    #     MUST precede branch 1: branch 1 matches on "arch present + no
    #     effective marker", and a corrupt file yields no marker — so branch 1
    #     would always win and this diagnostic would be unreachable.
    if planner_handoff.is_file() and planner is None and arch is not None:
        return (
            "rdd-planner",
            "planner-handoff 损坏（JSON 无法解析）→ 视为 planner 未完成，回到 planner 阶段",
            "high",
        )

    # 1. arch-handoff present, no planner marker → planner stage
    #    1a. ADR<1 → rdd-arch (recover)
    if arch is not None and planner_effective is None:
        adr_count = int(arch.get("adr_count", 0) or 0)
        if adr_count < 1:
            return (
                "rdd-arch",
                "arch-done 未完成 (ADR 数量不足 → 回到 adr-create 阶段)",
                "high",
            )
        return (
            "rdd-planner",
            "arch-done 已完成 → 进入 planner 阶段（.planner-handoff.json 尚未生成）",
            "high",
        )

    # 2. planner marker present → builder
    if planner_effective is not None:
        if marker_kind == "v3-design":
            # v3 design semantics (pre-existing behaviour): design reviewed,
            # changes not generated yet → next is change generation.
            return ("rdd-builder", "design-done 已完成 → 进入变更生成", "high")

        active_count = 0
        if marker_kind == "v3-plan":
            # v3 plan semantics: the handoff carries an `active_changes` count
            active_count = int(planner_effective.get("active_changes", 0) or 0)
            if active_count == 0:
                return (
                    "rdd-builder",
                    "plan-handoff 残留 (无活跃 change -> 进入 ship 清理/归档)",
                    "high",
                )
        else:
            # v4 semantics: planner-handoff-v1 defines no `active_changes`
            # field, so the filesystem is the only reliable source.
            fs_active = _count_active_changes(project_root)
            if fs_active == 0:
                return ("rdd-builder", "planner-handoff 已完成 → 进入变更生成", "high")

        # Cross-validate the v3 handoff against the filesystem: it claims
        # active changes but none exist on disk.
        if marker_kind == "v3-plan":
            fs_active = _count_active_changes(project_root)
            if fs_active == 0:
                return (
                    "rdd-arch",
                    f"plan-handoff stale (says {active_count} active, "
                    "but 0 in filesystem -> all archived)",
                    "high",
                )
        return ("rdd-builder", "变更生成已完成 → 进入变更执行", "high")

    # 3-5. worktree states (only reachable when no handoff exists at all)
    worktrees = openspec_worktrees(project_root)
    for wt in worktrees:
        if _worktree_has_incomplete_tasks(wt):
            return ("rdd-builder", "worktree 存在,任务未完成 → 继续执行", "medium")

    if worktrees:
        return (
            "rdd-builder",
            f"{len(worktrees)} 个 worktree 在跑（可能在分离终端）",
            "medium",
        )

    # 6. committed change in HEAD (no worktree yet)
    if _has_committed_change_in_head(project_root):
        return ("rdd-builder", "有已 commit 的 change 待建 worktree", "medium")

    # 7. no roadmap.md
    roadmap_rel = "roadmap.md"
    if arch is not None:
        roadmap_rel = arch.get("roadmap_path") or "roadmap.md"
    roadmap_path = Path(project_root) / roadmap_rel
    if not roadmap_path.is_file():
        return ("rdd-arch", f"无 {roadmap_rel} → 进入架构定义", "high")

    # 8. no openspec/changes/ directory
    if not (Path(project_root) / "openspec" / "changes").is_dir():
        return ("rdd-builder", "无 change → 进入变更生成", "high")

    # 9-10. improvement-suggestions.md (current format: Markdown table)
    improvements_dir = Path(project_root) / ".rddf/improvements"
    approved_path = Path(project_root) / "improvement-approved.md"

    pending = False
    if improvements_dir.is_dir():
        all_improvements = {f.stem for f in improvements_dir.glob("*.md")}
        approved = set()
        if approved_path.is_file():
            try:
                content = approved_path.read_text()
                approved = set(
                    re.findall(r"\|\s*\[([^\]]+)\]\(.rddf/improvements/", content)
                )
            except OSError:
                pass
        if all_improvements - approved:
            pending = True

    if pending:
        return ("rdd-builder", "有未审查提案 → 进入设计阶段", "high")
    return ("rdd-builder", "无待创建 change → 准备 ship", "high")
