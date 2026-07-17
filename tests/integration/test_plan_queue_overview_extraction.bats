#!/usr/bin/env bats
# tests/integration/test_plan_queue_overview_extraction.bats
# Round B extraction: guide-plan.md L211-L261 queue overview (~50 lines)
# was a single inline bash code block. Extracted to
# skills/_lib/plan_queue_overview.sh::show_queue_overview().
#
# These tests lock the refactor in place:
#   1. plan_queue_overview.sh exists with show_queue_overview function.
#   2. guide-plan.md L211-L261 inline block removed.
#   3. guide-plan.md sources and calls show_queue_overview.
#   4. Oracle C1 safety check.

setup() {
  WT=/workspace/project/rdd-workflow
}

@test "plan_queue_overview_helper_exists" {
  [ -f "$WT/skills/guide-plan/scripts/plan_queue_overview.sh" ]
  bash -c "cd '$WT' && source skills/guide-plan/scripts/plan_queue_overview.sh && declare -f show_queue_overview" | grep -q 'show_queue_overview'
}

@test "guide_plan_queue_inline_block_removed" {
  # No '队列概览' block content
  ! grep -q 'PY_PROJECT_ROOT.*PENDING_SUGGESTIONS_COUNT' "$WT/skills/guide-plan/SKILL.md"
  ! grep -q '5 队列可视化' "$WT/skills/guide-plan/SKILL.md"
}

@test "guide_plan_invokes_helper" {
  grep -q 'source.*scripts/plan_queue_overview.sh' "$WT/skills/guide-plan/SKILL.md"
  grep -q 'show_queue_overview' "$WT/skills/guide-plan/SKILL.md"
}

@test "show_queue_overview_prints_5_states" {
  output=$(bash -c "cd '$WT' && source skills/guide-plan/scripts/plan_queue_overview.sh && show_queue_overview" 2>&1 || true)
  # Should print 4 state lines (candidate/planned/blocked/ready + 1 stale)
  echo "$output" | grep -q '候选'
  echo "$output" | grep -q '骨架'
  echo "$output" | grep -q '阻塞'
  echo "$output" | grep -q 'ship'
}

@test "show_queue_overview_handles_no_repo" {
  local tmpdir
  tmpdir=$(mktemp -d)
  cd "$tmpdir"
  output=$(PROJECT_ROOT="$tmpdir" bash -c "source '$WT/skills/guide-plan/scripts/plan_queue_overview.sh' && show_queue_overview" 2>&1 || true)
  rm -rf "$tmpdir"
  # Should print empty states (or fallback)
  echo "$output" | grep -q '队列'
}

@test "oracle_c1_no_bash_string_interpolation_in_python" {
  # Bash wrapper must NOT inject env vars into Python source
  ! grep -n "python3.*'\$" "$WT/skills/guide-plan/scripts/plan_queue_overview.sh"
}