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
  # v2.0.3: the "Worktree 创建完成" display block was removed during
  # v2.0 refactor. P2-7 fix is now vacuously true (no $wt anywhere in
  # the current guide-ship.md). We return empty block + skip the test
  # in the calling tests to preserve the contract that the helper exists.
  awk '
    /^\*\*Worktree 创建完成/ { in_header = 1; next }
    in_header && /^```$/ { in_header = 0; in_block = 1; next }
    in_block && /^```$/ { exit }
    in_block { print }
  ' skills/guide-ship.md
}

# v2.0.3: the P2-7 display block was removed entirely. The P2-7
# guarantee (no unprefixed $wt in user-facing display blocks) is now
# vacuously true since the block no longer exists. The remaining $wt
# usages (lines 471-474, 492, 1246) are local for-loop variables
# (`for wt in "${wt_list[@]}"`) — these are in-scope and correct.
@test "P2-7: guide-ship.md has no unprefixed \$wt (P2-7 fix)" {
  [ -f "skills/guide-ship.md" ]
  # v2.0.3: only allow $wt in the worktree cleanup for-loop context.
  # The for-loop variable `for wt in "${wt_list[@]}"` is local; the
  # original P2-7 bug was using $wt OUTSIDE any loop where it was undefined.
  if grep -nE '\$\{?wt[^_a-zA-Z}' "skills/guide-ship.md" | grep -v 'for wt in' | grep -q .; then
    echo "FAIL: guide-ship.md uses \$wt outside a for-loop context:"
    grep -nE '\$\{?wt[^_a-zA-Z]' "skills/guide-ship.md" | grep -v 'for wt in'
    return 1
  fi
}

@test "P2-7: guide-ship.md uses \$WT_PATH for paths (P2-7 fix)" {
  [ -f "skills/guide-ship.md" ]
  # Either $WT_PATH is present, or the file has no worktree-path display at all.
  if grep -qE '\$WT_PATH' "skills/guide-ship.md"; then
    return 0
  fi
  # No $WT_PATH and no worktree path display = trivially passes P2-7
  if ! grep -qE "Worktree.*路径|worktree.*path" "skills/guide-ship.md"; then
    return 0
  fi
  echo "FAIL: guide-ship.md has worktree path display but no \$WT_PATH"
  return 1
}

@test "P2-7: guide-ship.md display block has no unprefixed \$wt" {
  [ -f "skills/guide-ship.md" ]
  # v2.0.3: The "Worktree 创建完成" display block was removed during the
  # v2.0 refactor. The P2-7 fix is vacuously true (no user-facing display
  # block can have an unprefixed $wt if no such block exists).
  # The global P2-7 check above (test 1) covers the actual current invariant.
  local block
  block=$(get_display_block)
  if [ -z "$block" ]; then
    skip "Worktree 创建完成 display block was removed in v2.0 — see P2-7 global check above"
  fi
  if echo "$block" | grep -qE '\$wt[^_a-zA-Z]'; then
    echo "FAIL: display block still uses unprefixed \$wt:"
    echo "$block" | grep -nE '\$wt[^_a-zA-Z]'
    return 1
  fi
}

@test "P2-7: guide-ship.md display block uses \$WT_PATH for paths" {
  [ -f "skills/guide-ship.md" ]
  # v2.0.3: same rationale as test 3 — display block no longer exists.
  local block
  block=$(get_display_block)
  if [ -z "$block" ]; then
    skip "Worktree 创建完成 display block was removed in v2.0 — see P2-7 global check above"
  fi
  echo "$block" | grep -qE '\$WT_PATH'
}
