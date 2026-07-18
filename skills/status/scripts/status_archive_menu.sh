#!/usr/bin/env bash
# skills/status/scripts/status_archive_menu.sh
# Extracted from status.md Mode A case handler (L152-L159).
# Exports: handle_status_archive_menu()
#
# Interactive menu choice handler for status Mode A (status overview) menu.
# Handles q|quit|exit, r|refresh, ?|help, i (custom input), and * (invalid).
#
# Usage:
#   source "$(dirname "${BASH_SOURCE[0]:-$0}")/scripts/status_archive_menu.sh"
#   handle_status_archive_menu "$choice"
#   rc=$?
#   [ "$rc" -eq 2 ] && continue  # r|refresh -> re-display menu
#
# Return codes:
#   0 - normal (help shown, custom input handled, or invalid input handled)
#   2 - refresh requested (caller should `continue` the menu loop)
#   (exit 0) - on q|quit|exit
#
# Note: The original inline handler used `continue` directly, which only works
# inside a loop in the same shell. Extraction to a function requires return-code
# signaling instead: callers check for rc=2 and execute `continue` themselves.

handle_status_archive_menu() {
  local choice="$1"
  case "$choice" in
    q|quit|exit) exit 0 ;;
    r|refresh) return 2 ;;
    ?|help) echo "可用命令: [数字选项], i(自定义输入), q(退出), r(刷新), ?(帮助)" ;;
    i)         echo -n "  自定义操作: "; read -r CUSTOM; echo "   收到: '$CUSTOM' - 尝试路由" ;;
    *) echo "❌ 无效输入 '$choice',请重试或输入 ? 查看帮助" ;;
  esac
  return 0
}
