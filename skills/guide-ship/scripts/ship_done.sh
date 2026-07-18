#!/usr/bin/env bash
# skills/guide-ship/scripts/ship_done.sh
# Phase 5 "Loop check" logic from guide-ship.md extracted into a reusable helper.
# Was a ~26-line inline bash block at L617-L643 counting remaining unprocessed
# changes and active openspec/* worktrees, then printing a dual-variant menu
# (different intro line depending on REMAINING/REMAINING_WT counts).
#
# Functions exported:
#   - check_remaining_work <project_root>
#       Counts unprocessed openspec/changes/* (excluding archive/) and
#       active openspec/* worktree branches. Prints one of two menu
#       variants depending on whether any work remains:
#         - "📋 还有 ..." header when REMAINING_WT>0 or REMAINING>0
#         - "✅ 所有 changes 已处理完毕" when both are 0
#       Both variants print the same 5-option menu (1/2/3/4/i).
#       Mirrors the original Phase 5 loop-check block exactly.

check_remaining_work() {
  local PROJECT_ROOT="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

  # Count remaining unprocessed changes
  local REMAINING
  REMAINING=$(ls -d "$PROJECT_ROOT"/openspec/changes/*/ 2>/dev/null | grep -v archive/ | wc -l)
  local REMAINING_WT
  REMAINING_WT=$(git worktree list 2>/dev/null | awk '$3 ~ /^openspec\// {print $1}' | wc -l)

  if [ "$REMAINING_WT" -gt 0 ] || [ "$REMAINING" -gt 0 ]; then
      echo "📋 还有 $REMAINING_WT 个 worktree 在跑,$REMAINING 个未处理 change"
      echo ""
      echo "请选择:"
      echo "1. 继续处理 (skill_use(\"guide-ship\")) - 还有 worktree 要处理"
      echo "2. 回到 spec 端 (skill_use(\"guide-arch\") 或 skill_use(\"guide-plan\")) - 创建更多 changes"
      echo "3. 本次 session 结束 - 退出 ship-done,稍后继续"
      echo "4. 项目完成 - 不再做任何 change(此项目归档)"
      echo "i. 其他输入"
  else
      echo "✅ 所有 changes 已处理完毕"
      echo ""
      echo "请选择:"
      echo "1. 继续处理 (skill_use(\"guide-ship\")) - 还有 worktree 要处理"
      echo "2. 回到 spec 端 (skill_use(\"guide-arch\") 或 skill_use(\"guide-plan\")) - 创建更多 changes"
      echo "3. 本次 session 结束 - 退出 ship-done,稍后继续"
      echo "4. 项目完成 - 不再做任何 change(此项目归档)"
      echo "i. 其他输入"
  fi
}
