#!/usr/bin/env bats

load ../test_helper

# P3-1 + P3-2: USAGE.md must reflect the new entry points (guide / rdd-arch /
# rdd-planner / rdd-builder / rdd-verifier per ADR-0043 stage-merge) and must
# NOT contain stale references to the pre-refactor migration note or the
# deprecated workflow-state.md / workflow-progress.md state files. These tests
# lock the documentation against future regression to the old monolithic-
# workflow wording.

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

@test "USAGE.md example shows new entry points (guide / rdd-arch / rdd-planner / rdd-builder / rdd-verifier)" {
  # v4 stage-merge (ADR-0043) renamed guide-arch→rdd-arch, guide-plan→rdd-planner
  # (with rdd-builder integrating plan+ship+design per ADR-0025), guide-ship→
  # rdd-builder, and added rdd-verifier (5th phase per ADR-0034).
  [ -f "USAGE.md" ]
  grep -qE 'skill_use\("rdd-arch"\)' USAGE.md
  grep -qE 'skill_use\("rdd-planner"\)' USAGE.md
  grep -qE 'skill_use\("rdd-builder"\)' USAGE.md
  grep -qE 'skill_use\("rdd-verifier"\)' USAGE.md
  grep -qE 'skill_use\("guide"\)' USAGE.md
}
