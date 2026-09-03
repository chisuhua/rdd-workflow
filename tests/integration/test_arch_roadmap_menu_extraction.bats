#!/usr/bin/env bats
# tests/integration/test_arch_roadmap_menu_extraction.bats
#
# Locks the extraction of rdd-arch.md inline case handlers (L126/L201/L333/L458)
# to skills/rdd-arch/scripts/arch_roadmap_menu.sh::handle_arch_menu().
#
# Tests:
#   1. Helper script exists with handle_arch_menu function.
#   2. rdd-arch.md no longer inlines the original case block markers.
#   3. rdd-arch.md sources and invokes helper at each phase.
#   4. handle_arch_menu exits 0 on q|quit|exit.
#   5. handle_arch_menu returns 2 on r|refresh.
#   6. handle_arch_menu prints help on ?|help.
#   7. handle_arch_menu prints invalid message on unknown input.

load ../test_helper

@test "arch_roadmap_menu_helper_exists" {
  [ -f "$REPO_ROOT/skills/rdd-arch/scripts/arch_roadmap_menu.sh" ]
  bash -c "cd '$REPO_ROOT' && source skills/rdd-arch/scripts/arch_roadmap_menu.sh && declare -f handle_arch_menu" | grep -q 'handle_arch_menu'
}

@test "guide_arch_inline_menu_block_removed" {
  # The 4 identical generic handlers (Phase 1 setup, Phase 2 adr-create,
  # Phase 3 architecture, Phase 4 roadmap-define) must be replaced with
  # source+call. The Phase 5 arch-done fallback handler at L582 is a DIFFERENT
  # handler (uses "重新执行门控检查" comment + has additional `1)` option for
  # back-to-adr-create) and is intentionally NOT extracted.
  # We verify by checking the unique comment of the generic 4-arm handlers
  # ("重新展示菜单") no longer appears in any inline `case` arm. After extraction,
  # this comment only appears in the source+call replacement lines like
  # `[ $? -eq 2 ] && continue  # r|refresh -> 重新展示菜单`, NOT in
  # `r|refresh) continue ;;  # 重新展示菜单` inline case arms.
  count=$(grep -cF 'r|refresh) continue ;;  # 重新展示菜单' "$REPO_ROOT/skills/rdd-arch/SKILL.md" || true)
  [ "$count" -eq 0 ]
}

@test "guide_arch_invokes_menu_helper_at_each_phase" {
  # 4 phases (setup, adr-create, architecture, roadmap-define) all source + call.
  count=$(grep -c 'scripts/arch_roadmap_menu.sh' "$REPO_ROOT/skills/rdd-arch/SKILL.md")
  [ "$count" -ge 4 ]
  count=$(grep -c 'handle_arch_menu' "$REPO_ROOT/skills/rdd-arch/SKILL.md")
  [ "$count" -ge 4 ]
}

@test "handle_arch_menu_exits_on_quit" {
  run bash -c "cd '$REPO_ROOT' && source skills/rdd-arch/scripts/arch_roadmap_menu.sh && handle_arch_menu 'q'"
  [ "$status" -eq 0 ]
}

@test "handle_arch_menu_exits_on_exit" {
  run bash -c "cd '$REPO_ROOT' && source skills/rdd-arch/scripts/arch_roadmap_menu.sh && handle_arch_menu 'exit'"
  [ "$status" -eq 0 ]
}

@test "handle_arch_menu_returns_2_on_refresh" {
  run bash -c "cd '$REPO_ROOT' && source skills/rdd-arch/scripts/arch_roadmap_menu.sh && handle_arch_menu 'r'; rc=\$?; echo \"rc=\$rc\""
  [ "$status" -eq 0 ]
  echo "$output" | grep -q 'rc=2'
}

@test "handle_arch_menu_prints_help_on_question_mark" {
  run bash -c "cd '$REPO_ROOT' && source skills/rdd-arch/scripts/arch_roadmap_menu.sh && handle_arch_menu '?'"
  [ "$status" -eq 0 ]
  echo "$output" | grep -q '可用命令'
}

@test "handle_arch_menu_prints_invalid_on_unknown_input" {
  run bash -c "cd '$REPO_ROOT' && source skills/rdd-arch/scripts/arch_roadmap_menu.sh && handle_arch_menu 'zzz'"
  [ "$status" -eq 0 ]
  echo "$output" | grep -q '无效输入'
}
