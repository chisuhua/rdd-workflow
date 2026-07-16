#!/usr/bin/env bats
# tests/integration/test_plan_feature_progress_extraction.bats
# Round B extraction: guide-plan.md L263-L297 feature progress (~34 lines)
# was a single inline bash code block. Extracted to
# skills/_lib/plan_feature_progress.sh::show_feature_progress().
#
# These tests lock the refactor in place:
#   1. plan_feature_progress.sh exists with show_feature_progress function.
#   2. guide-plan.md L263-L297 inline block removed.
#   3. guide-plan.md sources and calls show_feature_progress.
#   4. Oracle C1 safety check.

setup() {
  WT=/workspace/project/rdd-workflow
}

@test "plan_feature_progress_helper_exists" {
  [ -f "$WT/skills/_lib/plan_feature_progress.sh" ]
  bash -c "cd '$WT' && source skills/_lib/plan_feature_progress.sh && declare -f show_feature_progress" | grep -q 'show_feature_progress'
}

@test "guide_plan_feature_inline_block_removed" {
  # No 'Feature 进度' block content
  ! grep -q 'Feature 进度:' "$WT/skills/guide-plan.md"
  ! grep -q '所有 sub-change 已归档' "$WT/skills/guide-plan.md"
}

@test "guide_plan_invokes_helper" {
  grep -q 'source.*_lib/plan_feature_progress.sh' "$WT/skills/guide-plan.md"
  grep -q 'show_feature_progress' "$WT/skills/guide-plan.md"
}

@test "show_feature_progress_handles_no_features" {
  local tmpdir
  tmpdir=$(mktemp -d)
  cd "$tmpdir"
  output=$(PROJECT_ROOT="$tmpdir" bash -c "source '$WT/skills/_lib/plan_feature_progress.sh' && show_feature_progress" 2>&1 || true)
  rm -rf "$tmpdir"
  # Empty repo should print "(无 multi-change feature)"
  echo "$output" | grep -qE '无 multi-change feature|\(无'
}

@test "oracle_c1_no_bash_string_interpolation_in_python" {
  ! grep -n "python3.*'\$" "$WT/skills/_lib/plan_feature_progress.sh"
}