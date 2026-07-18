#!/usr/bin/env bats
# tests/integration/test_plan_propose_menu_extraction.bats
#
# Locks the extraction of guide-plan.md Phase 2 propose/create menu case handler
# (L284-L290) to skills/guide-plan/scripts/plan_propose_menu.sh::handle_plan_propose_menu().
#
# Tests:
#   1. Helper script exists with handle_plan_propose_menu function.
#   2. guide-plan.md no longer inlines the original case block markers.
#   3. guide-plan.md sources and invokes helper.
#   4. handle_plan_propose_menu exits 0 on q|quit|exit.
#   5. handle_plan_propose_menu returns 2 on r|refresh.
#   6. handle_plan_propose_menu prints help on ?|help.
#   7. handle_plan_propose_menu prints invalid message on unknown input.

load ../test_helper

@test "plan_propose_menu_helper_exists" {
  [ -f "$REPO_ROOT/skills/guide-plan/scripts/plan_propose_menu.sh" ]
  bash -c "cd '$REPO_ROOT' && source skills/guide-plan/scripts/plan_propose_menu.sh && declare -f handle_plan_propose_menu" | grep -q 'handle_plan_propose_menu'
}

@test "guide_plan_inline_propose_menu_block_removed" {
  # The Phase 2 propose/create menu handler (L284-L290) must be replaced with
  # source+call. Phase 1 scan menu (L134) and Phase 4 plan-done fallback (L475)
  # are out of scope:
  #   - Phase 1 is identical generic handler but task explicitly scoped to Phase 2.
  #   - Phase 4 is a DIFFERENT handler with additional `1)` and `2)` options
  #     (comment "重新执行门控检查" instead of "重新展示菜单").
  # We verify by counting inline `r|refresh) continue ;;  # 重新展示菜单` arms.
  # After extraction: 1 remaining (Phase 1 still inline) instead of 2.
  count=$(grep -cF 'r|refresh) continue ;;  # 重新展示菜单' "$REPO_ROOT/skills/guide-plan/SKILL.md" || true)
  [ "$count" -le 1 ]
}

@test "guide_plan_invokes_propose_menu_helper" {
  grep -q 'scripts/plan_propose_menu.sh' "$REPO_ROOT/skills/guide-plan/SKILL.md"
  grep -q 'handle_plan_propose_menu' "$REPO_ROOT/skills/guide-plan/SKILL.md"
}

@test "handle_plan_propose_menu_exits_on_quit" {
  run bash -c "cd '$REPO_ROOT' && source skills/guide-plan/scripts/plan_propose_menu.sh && handle_plan_propose_menu 'quit'"
  [ "$status" -eq 0 ]
}

@test "handle_plan_propose_menu_exits_on_exit" {
  run bash -c "cd '$REPO_ROOT' && source skills/guide-plan/scripts/plan_propose_menu.sh && handle_plan_propose_menu 'exit'"
  [ "$status" -eq 0 ]
}

@test "handle_plan_propose_menu_returns_2_on_refresh" {
  run bash -c "cd '$REPO_ROOT' && source skills/guide-plan/scripts/plan_propose_menu.sh && handle_plan_propose_menu 'refresh'; rc=\$?; echo \"rc=\$rc\""
  [ "$status" -eq 0 ]
  echo "$output" | grep -q 'rc=2'
}

@test "handle_plan_propose_menu_prints_help_on_question_mark" {
  run bash -c "cd '$REPO_ROOT' && source skills/guide-plan/scripts/plan_propose_menu.sh && handle_plan_propose_menu 'help'"
  [ "$status" -eq 0 ]
  echo "$output" | grep -q '可用命令'
}

@test "handle_plan_propose_menu_prints_invalid_on_unknown_input" {
  run bash -c "cd '$REPO_ROOT' && source skills/guide-plan/scripts/plan_propose_menu.sh && handle_plan_propose_menu 'unknown'"
  [ "$status" -eq 0 ]
  echo "$output" | grep -q '无效输入'
}
