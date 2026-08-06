#!/usr/bin/env bats
# tests/integration/test_execute_step7_extraction.bats
# Round B Task B9 extraction: execute.md L195-L282 Step 7 final report block
# (~88 lines) extracted to _lib/execute_step7.{py,sh,env.py}.
#
# These tests lock the refactor in place:
#   1. execute_step7.{sh,py,env.py} exist with correct functions.
#   2. execute.md inline bash block removed (Step 7 report).
#   3. execute.md sources and calls helpers.
#   4. No Oracle C1 bash string interpolation ($VAR in python3 source).
#   5. Helper runs correctly with scratch tasks.md.
#   6. Handles missing change gracefully.
#   7. Uses worktree.sh (no raw awk for branch parsing).
#   8. Includes next-step instructions.

load ../test_helper

@test "execute_step7_helper_exists" {
  # v2.0.8 Phase 2: helpers moved from _lib/ to per-skill scripts/
  assert_file_exists "$REPO_ROOT/skills/execute/scripts/execute_step7.sh"
  assert_file_exists "$REPO_ROOT/skills/execute/scripts/execute_step7.py"
  assert_file_exists "$REPO_ROOT/skills/execute/scripts/execute_step7_env.py"
  bash -c "cd '$REPO_ROOT' && source skills/execute/scripts/execute_step7.sh && declare -f run_step7_report" | grep -q 'run_step7_report'
}

@test "execute_inline_step7_block_removed" {
  # The old inline bash block (~L195-L282) must be removed
  ! grep -q 'Step 7.*输出明确' "$REPO_ROOT/skills/execute/SKILL.md"
  ! grep -q 'iteration.json 同步失败' "$REPO_ROOT/skills/execute/SKILL.md"
}

@test "execute_invokes_step7_helper" {
  grep -q 'source.*scripts/execute_step7.sh' "$REPO_ROOT/skills/execute/SKILL.md"
  grep -q 'run_step7_report' "$REPO_ROOT/skills/execute/SKILL.md"
}

@test "oracle_c1_no_bash_string_interpolation_step7" {
  # Must not have $VAR interpolated into Python source code
  ! grep -n "python3.*'\\\\$" "$REPO_ROOT/skills/execute/scripts/execute_step7.sh"
}

@test "run_step7_report_runs_in_scratch" {
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/openspec/changes/test-change"
  cat > "$tmpdir/openspec/changes/test-change/tasks.md" <<'EOF'
- [x] Task 1
- [ ] Task 2
EOF
  output=$(PROJECT_ROOT="$tmpdir" CHANGE_NAME="test-change" bash -c "source '$REPO_ROOT/skills/execute/scripts/execute_step7.sh' && run_step7_report" 2>&1 || true)
  rm -rf "$tmpdir"
  echo "$output" | grep -qE '执行完成|Change:'
}

@test "run_step7_report_handles_missing_change" {
  local tmpdir
  tmpdir=$(mktemp -d)
  output=$(PROJECT_ROOT="$tmpdir" CHANGE_NAME="nonexistent" bash -c "source '$REPO_ROOT/skills/execute/scripts/execute_step7.sh' && run_step7_report" 2>&1 || true)
  rm -rf "$tmpdir"
  # Should print something (not crash)
  echo "$output" | grep -qE 'Change:|0/0|nonexistent'
}

@test "run_step7_report_uses_porcelain_not_raw_awk" {
  # Should NOT use raw awk for openspec/ branch parsing
  # (uses git worktree list --porcelain internally in the Python code)
  ! grep -n "awk.*openspec/" "$REPO_ROOT/skills/execute/scripts/execute_step7.sh"
}

@test "run_step7_report_includes_next_steps_section" {
  local tmpdir
  tmpdir=$(mktemp -d)
  output=$(PROJECT_ROOT="$tmpdir" CHANGE_NAME="test" bash -c "source '$REPO_ROOT/skills/execute/scripts/execute_step7.sh' && run_step7_report" 2>&1 || true)
  rm -rf "$tmpdir"
  # Should print "下一步" or similar next-step guidance
  echo "$output" | grep -qE '下一步|📋'
}
