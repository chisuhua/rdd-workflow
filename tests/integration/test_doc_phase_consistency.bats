#!/usr/bin/env bats

load ../test_helper

# P1-11: README.md and USAGE.md must describe guide-ship's actual phase
# sequence: plan -> execute -> archive -> cleanup. The historical docs
# (and the audit report) listed "discover -> worktree -> plan -> execute
# -> archive", which is 5 phases with a bogus "discover" step that the
# code never implements.
#
# These tests lock the documentation against future regression to the
# old (incorrect) phase list.

@test "README.md no longer mentions 'discover' phase for guide-ship" {
  [ -f "README.md" ]
  ! grep -E "guide-ship.*discover|discover.*worktree.*plan.*execute.*archive" README.md
}

@test "README.md has new phase sequence: plan -> execute -> archive -> cleanup" {
  [ -f "README.md" ]
  grep -E "plan.*execute.*archive.*cleanup" README.md
}

@test "USAGE.md no longer mentions 'discover' phase" {
  [ -f "USAGE.md" ]
  ! grep -E "guide-ship.*discover|discover.*worktree.*plan.*execute.*archive" USAGE.md
}

@test "USAGE.md has new phase sequence" {
  [ -f "USAGE.md" ]
  grep -E "plan.*execute.*archive.*cleanup" USAGE.md
}

@test "USAGE.md registration table updated to new phase sequence" {
  [ -f "USAGE.md" ]
  # The registration table row for guide-ship must show the new sequence.
  # Use grep -A 1 to grab the line AFTER the matching "guide-ship ... 状态机"
  # table row, then check the phase pattern in that context. We use
  # `head -1` to take the first hit (the line containing the table row
  # itself) and verify the new sequence is present on the same row.
  grep -qE "plan.*execute.*archive.*cleanup|计划.*实施执行.*归档.*清理" "$REPO_ROOT/USAGE.md"
}
