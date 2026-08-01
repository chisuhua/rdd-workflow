#!/usr/bin/env bash
# skills/guide-ship/scripts/ship_done.sh
# Phase 5 loop check. When count_orphaned_sessions > 0, warns with first 3
# orphaned IDs (+N more overflow) and appends option 5 before 'i. 其他输入'.
# Baseline output unchanged when orphans == 0.
check_remaining_work() {
  local PROJECT_ROOT="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../_lib" && pwd)/sessions_count.sh"
  local REMAINING REMAINING_WT ORPHANS
  REMAINING=$(ls -d "$PROJECT_ROOT"/openspec/changes/*/ 2>/dev/null | grep -v archive/ | wc -l | tr -d '[:space:]')
  REMAINING_WT=$(git worktree list 2>/dev/null | awk '$3 ~ /^openspec\// {print $1}' | wc -l | tr -d '[:space:]')
  ORPHANS=$(count_orphaned_sessions "$PROJECT_ROOT")
  if [ "$REMAINING_WT" -gt 0 ] || [ "$REMAINING" -gt 0 ]; then echo "📋 还有 $REMAINING_WT 个 worktree 在跑,$REMAINING 个未处理 change"; else echo "✅ 所有 changes 已处理完毕"; fi
  echo ""
  if [ "$ORPHANS" -gt 0 ]; then
    local IDS; IDS=$(PROJECT_ROOT="$PROJECT_ROOT" python3 -c 'import json, os; d=json.load(open(os.path.join(os.environ["PROJECT_ROOT"], ".rddf/state/sessions.json"))); ids=[s["session_id"] for s in d.get("sessions",[]) if s.get("state")=="orphaned"]; print(", ".join(ids[:3]) + (" ... +{} more".format(len(ids)-3) if len(ids)>3 else ""))' 2>/dev/null || echo "???")
    echo "⚠️ 发现 $ORPHANS 个 orphaned rddf-sessions ($IDS)"
    echo "   建议清理: skill_use(\"rddf-session\", \"abandon\", ...) 或 archive-history"
  fi
  echo "请选择:"
  echo "1. 继续处理 (skill_use(\"guide-ship\")) - 还有 worktree 要处理"
  echo "2. 回到 spec 端 (skill_use(\"guide-arch\") 或 skill_use(\"guide-plan\")) - 创建更多 changes"
  echo "3. 本次 session 结束 - 退出 ship-done,稍后继续"
  echo "4. 项目完成 - 不再做任何 change(此项目归档)"
  [ "$ORPHANS" -gt 0 ] && echo "5. 🧹 清理 $ORPHANS 个 orphaned sessions (skill_use(\"rddf-session\", \"abandon\", ...) 或 archive-history)"
  echo "i. 其他输入"
}
