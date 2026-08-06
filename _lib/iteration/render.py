"""Iteration state - CLI / status rendering.

Extracted from ``skills/_lib/iteration.py`` (v2.0.8 split). This module
holds the user-facing rendering of the iteration view (the
``status --iteration`` Mode E output). It is the only piece of
iteration.py that talks to stdout; all CRUD and query logic lives in
``store.py``.

``print_view`` was originally extracted from ``status.md`` Mode E
Step 2/2b so the rendering logic could be unit-tested without
invoking the bash skill, and so future consumers (TUI dashboard, CI
summary) get identical output.

All public names here are re-exported from ``skills._lib.iteration``
(the package ``__init__.py``), so existing
``from skills._lib.iteration import print_view`` imports continue to
work unchanged.
"""
from __future__ import annotations

import datetime
import os

from skills._lib.iteration.store import (
    derive_feature_name,
    list_archived,
    list_planned,
    load,
)


def print_view(project_root: str, show_planned: bool = True) -> int:
    """Render the iteration view to stdout for `status --iteration`.

    Extracted from status.md Mode E Step 2/2b (lines 580-659) so the
    rendering logic can be unit-tested without invoking the bash
    skill, and so future consumers (TUI dashboard, CI summary) get
    identical output.

    Args:
        project_root: absolute path to the git repo root.
        show_planned: when True (default), also render the planned
            changes list (S10).

    Returns:
        0 always. Missing iteration.json renders a friendly notice
        instead of raising.
    """
    iter_file = os.path.join(project_root, ".rddf", "state", "iteration.json")
    if not os.path.isfile(iter_file):
        print("📭 iteration.json 不存在")
        print("   说明: 尚未运行过 propose (roadmap 模式)")
        print('   初始化: skill_use("propose", "<name>")')
        return 0

    data = load(project_root)
    phase = data.get("current_phase", "default")
    updated_at = data.get("updated_at", "")

    print("📊 当前迭代视图")
    print(f"   Phase: {phase}    Updated: {updated_at}")
    active_count = sum(
        1 for c in data.get("changes", []) if c.get("status") in ("proposed", "in_worktree", "completed")
    )
    archived_count = sum(
        1 for c in data.get("changes", []) if c.get("status") == "archived"
    )
    print(f"   活跃: {active_count} | 已归档: {archived_count}")
    print()

    active = [
        c for c in data.get("changes", [])
        if c.get("status") in ("proposed", "in_worktree", "completed")
    ]
    if not active:
        print("  (无 active change)")
    else:
        print("| Feature | Change | Phase | Cat | Status | Blocker | Group | Conflicts | Tasks | Plan |")
        print("|---------|--------|-------|-----|--------|---------|-------|-----------|-------|------|")
        for c in active:
            feature = derive_feature_name(c["name"])
            status_icon = {"proposed": "📋", "in_worktree": "🔄", "completed": "✅"}.get(c.get("status"), "?")
            blocker = c.get("blocker") or "-"
            group = str(c.get("parallel_group") or "-")
            conflicts = ",".join(c.get("conflicts") or []) or "-"
            done = c.get("tasks_done", 0)
            total = c.get("tasks_total", 0)
            tasks = f"{done}/{total}" if total else "-"
            plan = "✅" if c.get("plan_path") else "-"
            phase_short = (c.get("phase") or "-")[:8]
            cat_short = (c.get("category") or "-")[:10]
            print(
                f"| {feature} | {c['name']} | {phase_short} | {cat_short} | "
                f"{status_icon} {c.get('status')} | {blocker} | {group} | "
                f"{conflicts} | {tasks} | {plan} |"
            )
        print()

    archived = list_archived(data)
    if archived:
        print("🗄️  最近归档 (top 5):")
        for c in archived[:5]:
            l2_count = c.get("l2_violation_count_after")
            l2_kind = c.get("l2_violation_kind")
            if l2_count is not None:
                l2_disp = f"L2: {l2_count} ({l2_kind or 'unknown'})"
            else:
                l2_disp = "L2: not recorded"
            print(f"   ✅ {c['name']}  ({c.get('archived_at', '')}) — {l2_disp}")
        if len(archived) > 5:
            print(f"   ... (共 {len(archived)} 个归档)")
        print()

    now = datetime.datetime.now(datetime.timezone.utc)
    for c in active:
        last_deps = c.get("last_deps_at")
        if not last_deps:
            continue
        try:
            last = datetime.datetime.fromisoformat(last_deps.replace("Z", "+00:00"))
        except ValueError:
            continue
        age_hours = (now - last).total_seconds() / 3600
        if age_hours > 24:
            print(f"⚠️  {c['name']}: deps 信息已 {age_hours:.0f}h 未更新, 建议重跑 deps")

    if show_planned:
        planned = list_planned(data)
        if planned:
            for c in planned:
                b = c.get("blocker") or ""
                bs = f" (blocked by {b})" if b else ""
                print(f"  📋 {c['name']}{bs}")
        else:
            print("(none)")

    return 0
