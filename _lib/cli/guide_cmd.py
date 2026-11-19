"""``rddf guide`` — project state scan + stage recommendation (ADR-0062).

Thin consumer: the priority ladder lives in ``_lib/recommender.py``. This
module only renders it. The former in-module ``_scan_state`` ladder was
removed when the three implementations were consolidated (ADR-0062); the
bash one went away with ``skills/guide/`` (ADR-0063).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from skills._lib.cli import resolve_project_root  # noqa: E402  (per fix-33-handlers)
from skills._lib.recommender import openspec_worktrees, scan_state


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

    try:
        recommend, reason, _confidence = scan_state(project_root)
    except Exception as exc:  # non-fatal contract (see docstring)
        print(f"⚠️  state scan failed ({exc}); emitting a safe default", file=sys.stderr)
        recommend, reason = "rdd-builder", "状态扫描失败 → 从 builder 阶段继续"
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
    worktree_list = openspec_worktrees(project_root)
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
