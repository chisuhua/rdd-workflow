"""``rddf guide`` subcommand handler.

Port of the 10-priority state-detection ladder from
``skills/guide/scripts/scan-state.sh::scan_state``. Reads the same set
of files and emits the same ``RECOMMEND`` / ``REASON`` strings so that
the AI agent's behavior is unchanged after migration.

Priority order (highest first):
    0.  v3 legacy handoff (.plan/.design-handoff.json, no .planner-handoff.json)
        → "rdd-builder" + legacy warning (MUST precede branch 1)
    1.  arch-handoff present, planner-handoff absent, ADR >= 1 → "rdd-planner"
    1b. arch-handoff present, ADR < 1                        → "rdd-arch (recover)"
    1c. planner-handoff present but unparsable                → "rdd-planner"
    2.  planner-handoff present (valid), active change on disk → "rdd-builder"
    2b. planner-handoff present (valid), no active change      → "rdd-builder"
    3-5. worktree states (incomplete/detached/complete)      → "rdd-builder"
    6.  committed change in HEAD, no worktree                → "rdd-builder"
    7.  no roadmap.md                                         → "rdd-arch"
    8.  no openspec/changes/                                  → "rdd-builder"
    9.  improvement-suggestions.md has pending entry            → "rdd-builder"
    10. default                                               → "rdd-builder"

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
import sys
from pathlib import Path
from typing import Optional, Tuple
from skills._lib.cli import resolve_project_root  # noqa: E402  (per fix-33-handlers)


def _read_json(path: Path) -> Optional[dict]:
    """Read a JSON file, returning None on missing/invalid.

    The top-level value MUST be a JSON object. A handoff whose content is
    an array (or any other non-dict) is not a valid handoff — the same
    rule the library consumers apply (``state_reader.read_*_handoff``) and
    the same rule the bash consumer applies (``_handoff_valid``). Without
    this, the three consumers would disagree on such a file.
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


def _count_active_changes(project_root: str) -> int:
    """Number of non-archived change directories on disk.

    Replaces the v3 ``active_changes`` field, which ``planner-handoff-v1``
    does not define — reading it always resolved to 0 and made every
    v4 project look like a leftover.
    """
    changes_dir = Path(project_root) / "openspec" / "changes"
    if not changes_dir.is_dir():
        return 0
    return sum(
        1 for d in changes_dir.iterdir() if d.is_dir() and d.name != "archive"
    )


def _scan_state(project_root: str) -> Tuple[str, str]:
    """Run the priority ladder; return (RECOMMEND, REASON).

    Python equivalent of scan-state.sh::scan_state. Consumes the v4
    planner handoff (``.planner-handoff.json``); v3 handoff files are
    read only as a legacy fallback.
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
    # read-only legacy fallback (never written by v4 stages). A corrupt file
    # does not count as a marker.
    #
    # The marker KIND matters: a v3 DESIGN handoff means "design done,
    # change generation next"; a v3 PLAN handoff means "changes exist,
    # execution/cleanup next". They are different stages and must not
    # share one code path.
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
        )

    # 1. arch-handoff present, no planner marker → planner stage
    #    1a. ADR<1 → rdd-arch (recover)
    if arch is not None and planner_effective is None:
        adr_count = int(arch.get("adr_count", 0) or 0)
        if adr_count < 1:
            return (
                "rdd-arch",
                "arch-done 未完成 (ADR 数量不足 → 回到 adr-create 阶段)",
            )
        return (
            "rdd-planner",
            "arch-done 已完成 → 进入 planner 阶段（.planner-handoff.json 尚未生成）",
        )

    # 2. planner marker present → builder
    if planner_effective is not None:
        if marker_kind == "v3-design":
            # v3 design semantics (pre-existing behaviour): design reviewed,
            # changes not generated yet → next is change generation.
            return ("rdd-builder", "design-done 已完成 → 进入变更生成")

        active_count = 0
        if marker_kind == "v3-plan":
            # v3 plan semantics: the handoff carries an `active_changes` count
            active_count = int(planner_effective.get("active_changes", 0) or 0)
            if active_count == 0:
                return (
                    "rdd-builder",
                    "plan-handoff 残留 (无活跃 change -> 进入 ship 清理/归档)",
                )
        else:
            # v4 semantics: planner-handoff-v1 defines no `active_changes`
            # field, so the filesystem is the only reliable source.
            fs_active = _count_active_changes(project_root)
            if fs_active == 0:
                return ("rdd-builder", "planner-handoff 已完成 → 进入变更生成")

        # Cross-validate the v3 handoff against the filesystem: it claims
        # active changes but none exist on disk.
        if marker_kind == "v3-plan":
            fs_active = _count_active_changes(project_root)
            if fs_active == 0:
                return (
                    "rdd-arch",
                    f"plan-handoff stale (says {active_count} active, "
                    "but 0 in filesystem -> all archived)",
                )
        return ("rdd-builder", "变更生成已完成 → 进入变更执行")

    # 3-5. worktree states
    worktrees = _git_worktree_list(project_root)
    for wt in worktrees:
        if _worktree_has_incomplete_tasks(wt):
            return ("rdd-builder", "worktree 存在,任务未完成 → 继续执行")

    detached = len(worktrees)
    if detached > 0:
        return (
            "rdd-builder",
            f"{detached} 个 worktree 在跑（可能在分离终端）",
        )

    if worktrees:
        return ("rdd-builder", "worktree 存在,任务已完成 → 进入 archive")

    # 6. committed change in HEAD (no worktree yet)
    if _has_committed_change_in_head(project_root):
        return ("rdd-builder", "有已 commit 的 change 待建 worktree")

    # 7. no roadmap.md
    roadmap_rel = "roadmap.md"
    if arch is not None:
        roadmap_rel = arch.get("roadmap_path") or "roadmap.md"
    roadmap_path = Path(project_root) / roadmap_rel
    if not roadmap_path.is_file():
        return ("rdd-arch", f"无 {roadmap_rel} → 进入架构定义")

    # 8. no openspec/changes/ directory
    if not (Path(project_root) / "openspec" / "changes").is_dir():
        return ("rdd-builder", "无 change → 进入变更生成")

    # 9-10. improvement-suggestions.md (current format: Markdown table)
    # Check if there are unapproved proposals in .rddf/improvements/
    improvements_dir = Path(project_root) / ".rddf/improvements"
    approved_path = Path(project_root) / "improvement-approved.md"
    
    pending = False
    if improvements_dir.is_dir():
        # Get all improvement names
        all_improvements = set()
        for f in improvements_dir.glob("*.md"):
            all_improvements.add(f.stem)
        
        # Get approved .rddf/improvements from improvement-approved.md
        approved = set()
        if approved_path.is_file():
            try:
                content = approved_path.read_text()
                # Parse Markdown table: | [name](...) | ... |
                approved = set(re.findall(r"\|\s*\[([^\]]+)\]\(.rddf/improvements/", content))
            except OSError:
                pass
        
        # If there are unapproved .rddf/improvements, recommend guide-design
        if all_improvements - approved:
            pending = True

    if pending:
        return ("rdd-builder", "有未审查提案 → 进入设计阶段")
    return ("rdd-builder", "无待创建 change → 准备 ship")


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

    project_root = os.environ.get("RDDF_PROJECT_ROOT") or resolve_project_root()
    state_dir = Path(project_root) / ".rddf" / "state"

    recommend, reason = _scan_state(project_root)
    warnings = _check_stale_workflow_state(project_root)

    # Render
    print()
    print("🔍 项目状态扫描")
    print("━" * 40)
    print(f"  roadmap.md:           {'✅ 存在' if (Path(project_root) / 'roadmap.md').is_file() else '❌ 缺失'}")
    print(f"  .arch-handoff.json:   {'✅ 存在' if (state_dir / '.arch-handoff.json').is_file() else '· 缺失'}")
    print(f"  .planner-handoff.json:{'✅ 存在' if (state_dir / '.planner-handoff.json').is_file() else '· 缺失'}")
    legacy = [
        n
        for n in (".plan-handoff.json", ".design-handoff.json")
        if (state_dir / n).is_file()
    ]
    if legacy:
        print(f"  ⚠️  legacy v3 handoff: {', '.join(legacy)}（请迁移到 .planner-handoff.json）")
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