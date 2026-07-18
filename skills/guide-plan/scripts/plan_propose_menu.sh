#!/usr/bin/env bash
# skills/guide-plan/scripts/plan_propose_menu.sh
# Extracted from guide-plan.md Phase 2 propose/create menu case handler (L284-L290).
# Exports: handle_plan_propose_menu()
#
# Generic interactive menu choice handler for plan phase propose/create menus
# (Phase 1 scan menu and Phase 2 propose menu).
# Handles q|quit|exit, r|refresh, ?|help, and * (invalid) choices.
#
# Usage:
#   source "$(dirname "${BASH_SOURCE[0]:-$0}")/scripts/plan_propose_menu.sh"
#   handle_plan_propose_menu "$choice"
#   rc=$?
#   [ "$rc" -eq 2 ] && continue  # r|refresh -> re-display menu
#
# Return codes:
#   0 - normal (help shown or invalid input handled)
#   2 - refresh requested (caller should `continue` the menu loop)
#   (exit 0) - on q|quit|exit
#
# Note: The original inline handlers used `continue` directly, which only works
# inside a loop in the same shell. Extraction to a function requires return-code
# signaling instead: callers check for rc=2 and execute `continue` themselves.

handle_plan_propose_menu() {
  local choice="$1"
  case "$choice" in
    q|quit|exit) exit 0 ;;
    r|refresh) return 2 ;;
    ?|help) echo "可用命令: [数字选项], q(退出), r(刷新), ?(帮助)" ;;
    *) echo "❌ 无效输入 '$choice',请重试或输入 ? 查看帮助" ;;
  esac
  return 0
}
