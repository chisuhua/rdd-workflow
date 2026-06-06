#!/usr/bin/env bats
#
# Wave 5 / T28: verify guide-ship.md P2-7 fix.
# See plan checkbox:
#   - [ ] 28. wt variable fix (P2-7)
#
# P2-7: the Worktree-创建完成 status display block referenced
#       undefined $wt and $name. Fix: use $WT_PATH and ${CHANGE_NAME}
#       (which are in scope at the call site).

load ../test_helper

# Helper: extract the Worktree-创建完成 status display block from
# guide-ship.md. The block sits between the ``` fence after
# "Worktree 创建完成 → 进入执行模式选择" and the next ``` fence.
# Scoping tests to this block avoids false positives from $wt used
# as a for-loop variable in worktree-cleanup loops (which is correct
# usage).
get_display_block() {
  awk '
    /^\*\*Worktree 创建完成/ { in_header = 1; next }
    in_header && /^```$/ { in_header = 0; in_block = 1; next }
    in_block && /^```$/ { exit }
    in_block { print }
  ' skills/guide-ship.md
}

@test "P2-7: guide-ship.md display block has no unprefixed \$wt" {
  [ -f "skills/guide-ship.md" ]
  # The display block (user-facing status panel) must not use
  # the undefined $wt variable. The fix uses $WT_PATH instead.
  local block
  block=$(get_display_block)
  [ -n "$block" ] || { echo "FAIL: display block is empty"; return 1; }
  # $wt followed by anything that's not a letter/underscore = unprefixed
  if echo "$block" | grep -qE '\$wt[^_a-zA-Z]'; then
    echo "FAIL: display block still uses unprefixed \$wt:"
    echo "$block" | grep -nE '\$wt[^_a-zA-Z]'
    return 1
  fi
}

@test "P2-7: guide-ship.md display block uses \$WT_PATH for paths" {
  [ -f "skills/guide-ship.md" ]
  # The display block should reference $WT_PATH (the in-scope variable
  # that holds the worktree path).
  local block
  block=$(get_display_block)
  [ -n "$block" ] || { echo "FAIL: display block is empty"; return 1; }
  echo "$block" | grep -qE '\$WT_PATH'
}
