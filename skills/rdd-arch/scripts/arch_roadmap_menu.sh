#!/usr/bin/env bash
# skills/guide-arch/scripts/arch_roadmap_menu.sh
# Extracted from guide-arch.md L126/L201/L333/L458 (4 identical case handlers).
# Exports: handle_arch_menu()
#
# Generic interactive menu choice handler for arch phase menus
# (Phase 1 setup, Phase 2 adr-create, Phase 3 architecture, Phase 4 roadmap-define).
# Handles q|quit|exit, r|refresh, ?|help, and * (invalid) choices.
#
# Usage:
#   source "$(dirname "${BASH_SOURCE[0]:-$0}")/scripts/arch_roadmap_menu.sh"
#   handle_arch_menu "$choice"
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

handle_arch_menu() {
  local choice="$1"
  case "$choice" in
    q|quit|exit) exit 0 ;;
    r|refresh) return 2 ;;
    ?|help) echo "可用命令: [数字选项], q(退出), r(刷新), ?(帮助)" ;;
    *) echo "❌ 无效输入 '$choice',请重试或输入 ? 查看帮助" ;;
  esac
  return 0
}
