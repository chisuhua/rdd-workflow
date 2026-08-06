"""``rddf guide`` subcommand handler.

Port of the 10-priority state-detection ladder from
``skills/guide/scripts/scan-state.sh::scan_state``. Reads the same set
of files and emits the same ``RECOMMEND`` / ``REASON`` strings so that
the AI agent's behavior is unchanged after migration.

Priority order (highest first; matches scan-state.sh lines 41-53):
    1.  arch-handoff present, plan-handoff absent, ADR >= 1  → "guide-plan"
    1b. arch-handoff present, ADR < 1                        → "guide-arch (recover)"
    2.  plan-handoff present, active_changes > 0             → "guide-ship"
    2b. plan-handoff present, active_changes == 0            → "guide-ship (cleanup)"
    3-5. worktree states (incomplete/detached/complete)      → "guide-ship"
    6.  committed change in HEAD, no worktree                → "guide-ship"
    7.  no roadmap.md                                         → "guide-arch"
    8.  no openspec/changes/                                  → "guide-plan"
    9.  proposal-suggestions.md has pending entry            → "guide-plan"
    10. default                                               → "guide-ship"

Stale ``workflow-state.md`` (pre-refactor format) emits a one-line
warning but does not change the recommendation.

Usage::

    python3 -m skills._lib.cli guide
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Optional, Tuple


def _read_json(path: Path) -> Optional[dict]:
    """Read a JSON file, returning None on missing/invalid."""
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _git_worktree_list(project_root: str) -> list[str]:
    """Return list of worktree paths that have an openspec/* branch.

    Matches scan-state.sh lines 110-118: ``git worktree list``,
    filtering for the ``[openspec/`` prefix in column 3.
    """
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
    """Return True if HEAD contains a committed openspec/changes/<name>/ directory.

    Matches scan-state.sh lines 143-153: iterates change dirs and
    checks ``git show HEAD:<path>``.
    """
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


def _check_stale_workflow_state(project_root: str) -> list[str]:
    """Return warning lines for stale pre-refactor state files."""
    warnings = []
    if (Path(project_root) / "workflow-state.md").is_file():
        warnings.append(
            "⚠️  Stale workflow-state.md detected (pre-refactor format)."
        )
        warnings.append(
            "   This file is no longer used and will be ignored."
        )
        warnings.append(
            "   Remove it manually if you want: rm workflow-state.md"
        )
    return warnings


def _scan_state(project_root: str) -> Tuple[str, str]:
    """Run the 10-priority ladder; return (RECOMMEND, REASON).

    This is the Python equivalent of scan-state.sh::scan_state. The
    return values match the strings emitted by the bash version.
    """
    state_dir = Path(project_root) / ".rddf" / "state"
    arch_handoff = state_dir / ".arch-handoff.json"
    design_handoff = state_dir / ".design-handoff.json"
    plan_handoff = state_dir / ".plan-handoff.json"

    arch = _read_json(arch_handoff)
    design = _read_json(design_handoff)
    plan = _read_json(plan_handoff)

    # 1. arch-handoff present, plan-handoff absent
    #    1a. ADR<1 → guide-arch (recover)
    #    1b. arch present, design absent → guide-design
    #    1c. arch present, design present → guide-plan
    if arch is not None and plan is None:
        adr_count = int(arch.get("adr_count", 0) or 0)
        if adr_count < 1:
            return (
                "guide-arch",
                "arch-done 未完成 (ADR 数量不足 → 回到 adr-create 阶段)",
            )
        if design is None:
            return ("guide-design", "arch-done 已完成 → 进入设计阶段")
        return ("guide-plan", "design-done 已完成 → 进入变更生成")

    # 2. plan-handoff present
    if plan is not None:
        active_count = int(plan.get("active_changes", 0) or 0)
        if active_count == 0:
            return (
                "guide-ship",
                "plan-handoff 残留 (无活跃 change -> 进入 ship 清理/归档)",
            )
        # Cross-validate: count non-archived change dirs in filesystem
        changes_dir = Path(project_root) / "openspec" / "changes"
        fs_active = 0
        if changes_dir.is_dir():
            for d in changes_dir.iterdir():
                if d.is_dir() and d.name != "archive":
                    fs_active += 1
        if fs_active == 0:
            return (
                "guide-arch",
                f"plan-handoff stale (says {active_count} active, but 0 in filesystem -> all archived)",
            )
        return ("guide-ship", "变更生成已完成 → 进入变更执行")

    # 3-5. worktree states
    worktrees = _git_worktree_list(project_root)
    for wt in worktrees:
        if _worktree_has_incomplete_tasks(wt):
            return ("guide-ship", "worktree 存在,任务未完成 → 继续执行")

    detached = len(worktrees)
    if detached > 0:
        return (
            "guide-ship",
            f"{detached} 个 worktree 在跑（可能在分离终端）",
        )

    if worktrees:
        return ("guide-ship", "worktree 存在,任务已完成 → 进入 archive")

    # 6. committed change in HEAD (no worktree yet)
    if _has_committed_change_in_head(project_root):
        return ("guide-ship", "有已 commit 的 change 待建 worktree")

    # 7. no roadmap.md
    roadmap_rel = "roadmap.md"
    if arch is not None:
        roadmap_rel = arch.get("roadmap_path") or "roadmap.md"
    roadmap_path = Path(project_root) / roadmap_rel
    if not roadmap_path.is_file():
        return ("guide-arch", f"无 {roadmap_rel} → 进入架构定义")

    # 8. no openspec/changes/ directory
    if not (Path(project_root) / "openspec" / "changes").is_dir():
        return ("guide-plan", "无 change → 进入变更生成")

    # 9-10. proposal-suggestions.md (current format: Markdown table)
    # Check if there are unapproved proposals in improvements/
    improvements_dir = Path(project_root) / "improvements"
    approved_path = Path(project_root) / "proposal-approved.md"
    
    pending = False
    if improvements_dir.is_dir():
        # Get all improvement names
        all_improvements = set()
        for f in improvements_dir.glob("*.md"):
            all_improvements.add(f.stem)
        
        # Get approved improvements from proposal-approved.md
        approved = set()
        if approved_path.is_file():
            try:
                content = approved_path.read_text()
                # Parse Markdown table: | [name](...) | ... |
                approved = set(re.findall(r"\|\s*\[([^\]]+)\]\(improvements/", content))
            except OSError:
                pass
        
        # If there are unapproved improvements, recommend guide-design
        if all_improvements - approved:
            pending = True

    if pending:
        return ("guide-design", "有未审查提案 → 进入设计阶段")
    return ("guide-ship", "无待创建 change → 准备 ship")


def cmd_guide(args: list[str]) -> int:
    """Handle ``rddf guide``.

    Args:
        args: Unused (the guide subcommand takes no arguments).
            ``--help`` / ``-h`` prints usage and returns 0.

    Returns:
        0 on success. State-detection errors are non-fatal: the
        function emits a recommendation based on whatever state it
        could read, plus any stale-state warnings.
    """
    if args and args[0] in ("-h", "--help"):
        _print_help()
        return 0

    project_root = os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()
    state_dir = Path(project_root) / ".rddf" / "state"

    recommend, reason = _scan_state(project_root)
    warnings = _check_stale_workflow_state(project_root)

    # Render
    print()
    print("🔍 项目状态扫描")
    print("━" * 40)
    print(f"  roadmap.md:           {'✅ 存在' if (Path(project_root) / 'roadmap.md').is_file() else '❌ 缺失'}")
    print(f"  .arch-handoff.json:   {'✅ 存在' if (state_dir / '.arch-handoff.json').is_file() else '· 缺失'}")
    print(f"  .design-handoff.json: {'✅ 存在' if (state_dir / '.design-handoff.json').is_file() else '· 缺失'}")
    print(f"  .plan-handoff.json:   {'✅ 存在' if (state_dir / '.plan-handoff.json').is_file() else '· 缺失'}")
    print(f"  iteration.json:       {'✅ 存在' if (state_dir / 'iteration.json').is_file() else '· 缺失'}")
    worktree_list = _git_worktree_list(project_root)
    print(f"  worktrees:            {len(worktree_list)}")
    print("━" * 40)
    print(f"  💡 建议: {recommend}")
    print(f"     {reason}")
    for w in warnings:
        print(f"  {w}")
    print()
    return 0


def _print_help() -> None:
    print("usage: rddf guide")
    print()
    print("Scan project state and emit a recommendation.")
    print("Outputs: project state summary + NEXT ACTION suggestion.")


__all__ = ["cmd_guide"]