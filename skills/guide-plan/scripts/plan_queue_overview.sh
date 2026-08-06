#!/usr/bin/env bash
# _lib/plan_queue_overview.sh — extracted from guide-plan.md L211-L261
# Exports: show_queue_overview()
#
# Shows 5-state queue visualization: candidates, planned, blocked, ready-for-ship, stale deps.
# Uses iteration.list_planned/list_blocked/list_ready_for_ship + state.sh::count_pending_suggestions.
# Falls back gracefully (empty arrays) if iteration module fails to load.

show_queue_overview() {
  PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  export PROJECT_ROOT

  echo ""
  echo "📊 当前队列状态:"
  source "$(dirname "${BASH_SOURCE[0]:-$0}")/../../_lib/state.sh"
  local PENDING_SUGGESTIONS_COUNT
  PENDING_SUGGESTIONS_COUNT=$(count_pending_suggestions "$PROJECT_ROOT")
  PY_PROJECT_ROOT="$PROJECT_ROOT" PENDING_SUGGESTIONS_COUNT="$PENDING_SUGGESTIONS_COUNT" python3 <<'PYEOF' 2>/dev/null
import os, sys, json
from datetime import datetime, timezone
project_root = os.environ.get("PY_PROJECT_ROOT", ".")

# P3-3b: candidates sourced from _lib/state.sh via env var (set by bash caller)
candidates = int(os.environ.get("PENDING_SUGGESTIONS_COUNT", "0"))

try:
    from skills._lib import iteration as it
    d = it.load(project_root)
    planned = it.list_planned(d)
    blocked = it.list_blocked(d)
    ready = it.list_ready_for_ship(d)
    changes_for_stale = d.get("changes", [])
except Exception:
    planned = blocked = ready = []
    changes_for_stale = []

now = datetime.now(timezone.utc)
stale = 0
for c in changes_for_stale:
    if c.get("status") not in ("proposed", "in_worktree"):
        continue
    last = c.get("last_deps_at")
    if not last:
        stale += 1
        continue
    try:
        age_hours = (now - datetime.fromisoformat(last.replace("Z", "+00:00"))).total_seconds() / 3600
        if age_hours > 24:
            stale += 1
    except (ValueError, TypeError):
        stale += 1

print(f"  🆕 候选: {candidates} [💡 选 1 个创建]")
print(f"  📋 骨架: {len(planned)}")
print(f"  ⏸️  阻塞: {len(blocked)} [⚠️ 等待 blocker 解除]")
ready_marker = " [✅ 满足 plan-done 门控]" if ready else ""
print(f"  🚀 可 ship: {len(ready)}{ready_marker}")
print(f"  ⚠️  deps 过期: {stale} [> 24h 未更新]")
PYEOF
}