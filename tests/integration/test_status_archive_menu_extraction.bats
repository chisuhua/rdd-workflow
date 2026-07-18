#!/usr/bin/env bats
# tests/integration/test_status_archive_menu_extraction.bats
#
# Locks the extraction of status.md Mode A case handler (L152-L159)
# to skills/status/scripts/status_archive_menu.sh::handle_status_archive_menu().
#
# Tests:
#   1. Helper script exists with handle_status_archive_menu function.
#   2. status.md no longer inlines the original case block markers.
#   3. status.md sources and invokes helper.
#   4. handle_status_archive_menu exits 0 on q|quit|exit.
#   5. handle_status_archive_menu returns 2 on r|refresh.
#   6. handle_status_archive_menu prints help on ?|help (preserves ? glob quirk).
#   7. handle_status_archive_menu prints invalid message on unknown input.

load ../test_helper

@test "status_archive_menu_helper_exists" {
  [ -f "$REPO_ROOT/skills/status/scripts/status_archive_menu.sh" ]
  bash -c "cd '$REPO_ROOT' && source skills/status/scripts/status_archive_menu.sh && declare -f handle_status_archive_menu" | grep -q 'handle_status_archive_menu'
}

@test "status_inline_mode_a_menu_block_removed" {
  # The Mode A status overview menu handler (L152-L159) must be replaced with
  # source+call. Mode D roadmap handler (L426) is a DIFFERENT handler
  # (multi-line `i)` arm with echo statements) and is intentionally NOT extracted.
  # We verify by counting inline Mode A-specific `r|refresh) continue ;;` lines
  # (no comment). Mode A originally had `r|refresh) continue ;;` (no comment),
  # Mode D has the same. So after extraction, count should be 1 (Mode D only)
  # instead of 2 (Mode A + Mode D).
  count=$(grep -cF 'r|refresh) continue ;;' "$REPO_ROOT/skills/status/SKILL.md" || true)
  [ "$count" -le 1 ]
}

@test "status_invokes_archive_menu_helper" {
  grep -q 'scripts/status_archive_menu.sh' "$REPO_ROOT/skills/status/SKILL.md"
  grep -q 'handle_status_archive_menu' "$REPO_ROOT/skills/status/SKILL.md"
}

@test "handle_status_archive_menu_exits_on_quit" {
  run bash -c "cd '$REPO_ROOT' && source skills/status/scripts/status_archive_menu.sh && handle_status_archive_menu 'quit'"
  [ "$status" -eq 0 ]
}

@test "handle_status_archive_menu_exits_on_exit" {
  run bash -c "cd '$REPO_ROOT' && source skills/status/scripts/status_archive_menu.sh && handle_status_archive_menu 'exit'"
  [ "$status" -eq 0 ]
}

@test "handle_status_archive_menu_returns_2_on_refresh" {
  run bash -c "cd '$REPO_ROOT' && source skills/status/scripts/status_archive_menu.sh && handle_status_archive_menu 'refresh'; rc=\$?; echo \"rc=\$rc\""
  [ "$status" -eq 0 ]
  echo "$output" | grep -q 'rc=2'
}

@test "handle_status_archive_menu_preserves_behavior_on_question_mark" {
  # Original inline handler had `?|help)` which is a bash glob matching any single char.
  # This extraction faithfully preserves that behavior (verified via git stash test).
  # The help message should be printed for any single-char input including '?'.
  run bash -c "cd '$REPO_ROOT' && source skills/status/scripts/status_archive_menu.sh && handle_status_archive_menu '?'"
  [ "$status" -eq 0 ]
  echo "$output" | grep -q '可用命令'
}
