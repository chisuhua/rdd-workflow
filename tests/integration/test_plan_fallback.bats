load test_helper

@test "plan_intake: check_direct_create_fallback offers direct-create when no approved" {
  source "$PROJECT_ROOT/skills/guide-plan/scripts/plan_intake.sh"
  
  mkdir -p "$BATS_TMPDIR/test-fallback/openspec/changes/archive/2026-01-01-old-change"
  
  run check_direct_create_fallback "$BATS_TMPDIR/test-fallback"
  [ "$status" -eq 0 ]
  [[ "$output" =~ "直接创建" ]]
}

@test "plan_intake: check_direct_create_fallback returns 1 when approved exists" {
  source "$PROJECT_ROOT/skills/guide-plan/scripts/plan_intake.sh"
  
  mkdir -p "$BATS_TMPDIR/test-no-fallback"
  touch "$BATS_TMPDIR/test-no-fallback/proposal-approved.md"
  
  run check_direct_create_fallback "$BATS_TMPDIR/test-no-fallback"
  [ "$status" -eq 1 ]
}

@test "plan_intake: check_direct_create_fallback returns 1 when no archive history" {
  source "$PROJECT_ROOT/skills/guide-plan/scripts/plan_intake.sh"
  
  mkdir -p "$BATS_TMPDIR/test-empty"
  
  run check_direct_create_fallback "$BATS_TMPDIR/test-empty"
  [ "$status" -eq 1 ]
}
