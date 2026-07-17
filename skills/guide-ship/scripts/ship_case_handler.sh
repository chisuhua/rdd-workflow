#!/usr/bin/env bash
# skills/_lib/ship_case_handler.sh — extracted from guide-ship.md (8 identical blocks)
# Exports: handle_invalid_choice()
#
# Handles user input for menu loops in guide-ship.md. Replaces 8
# identical case handler blocks. Call from within a while loop;
# exit 0 terminates the process, all other cases return 0 to
# let the loop continue naturally.

handle_invalid_choice() {
  local choice="$1"
  case "$choice" in
    q|quit|exit) exit 0 ;;
    r|refresh) : ;;  # caller: continue loop (skip rest)
    '?'|help) echo "可用命令: [数字选项], q(退出), r(刷新), ?(帮助)" ;;
    *) echo "❌ 无效输入 '$choice',请重试或输入 ? 查看帮助" ;;
  esac
}
