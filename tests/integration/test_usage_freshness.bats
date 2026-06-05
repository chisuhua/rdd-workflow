#!/usr/bin/env bats

load ../test_helper

# P3-1 + P3-2: USAGE.md must reflect the new entry points (guide / guide-spec /
# guide-ship) and must NOT contain stale references to the pre-refactor
# migration note or the deprecated workflow-state.md / workflow-progress.md
# state files. These tests lock the documentation against future regression
# to the old monolithic-workflow wording.

@test "USAGE.md no longer has Pre-refactor migration note" {
  [ -f "USAGE.md" ]
  ! grep -q "Pre-refactor migration note" USAGE.md
}

@test "USAGE.md no longer references workflow-state.md" {
  [ -f "USAGE.md" ]
  ! grep -q "workflow-state\.md" USAGE.md
}

@test "USAGE.md no longer references workflow-progress.md" {
  [ -f "USAGE.md" ]
  ! grep -q "workflow-progress\.md" USAGE.md
}

@test "USAGE.md example shows new entry points (guide / guide-spec / guide-ship)" {
  [ -f "USAGE.md" ]
  grep -qE 'skill_use\("guide-spec"\)' USAGE.md
  grep -qE 'skill_use\("guide-ship"\)' USAGE.md
  grep -qE 'skill_use\("guide"\)' USAGE.md
}
