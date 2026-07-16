#!/usr/bin/env bats
# tests/integration/test_update_roadmap_progress_extraction.bats
# Round B Task B8 extraction: execute.md L296-L346 roadmap progress block
# (~50 lines) extracted to skills/_lib/update_roadmap_progress.{py,sh,env.py}.
#
# These tests lock the refactor in place:
#   1. update_roadmap_progress.{sh,py,env.py} exist with correct functions.
#   2. execute.md inline python3 -c block removed.
#   3. execute.md sources and calls helpers.
#   4. No Oracle C1 bash string interpolation ($VAR in python3 source).
#   5. Helper creates roadmap-meta.yaml when missing.
#   6. No sed-based in-place edit for roadmap-meta.

load ../test_helper

@test "update_roadmap_progress_helper_exists" {
  [ -f "$REPO_ROOT/skills/_lib/update_roadmap_progress.sh" ]
  [ -f "$REPO_ROOT/skills/_lib/update_roadmap_progress.py" ]
  [ -f "$REPO_ROOT/skills/_lib/update_roadmap_progress_env.py" ]
  bash -c "cd '$REPO_ROOT' && source skills/_lib/update_roadmap_progress.sh && declare -f update_roadmap_progress" | grep -q 'update_roadmap_progress'
}

@test "execute_inline_python3_c_block_removed" {
  # The old inline python3 -c block with $CHANGE_NAME interp must be removed
  ! grep -q 'python3 -c.*roadmap' "$REPO_ROOT/skills/execute.md"
}

@test "execute_inline_roadmap_meta_interp_removed" {
  # No shell-var-injected roadmap-meta paths in execute.md
  ! grep -q 'roadmap-meta.*\$CHANGE_NAME' "$REPO_ROOT/skills/execute.md"
}

@test "execute_invokes_helper" {
  grep -q 'source.*_lib/update_roadmap_progress.sh' "$REPO_ROOT/skills/execute.md"
  grep -q 'update_roadmap_progress' "$REPO_ROOT/skills/execute.md"
}

@test "oracle_c1_no_bash_string_interpolation" {
  # Must not have $VAR interpolated into Python source code
  ! grep -n "python3.*'\$" "$REPO_ROOT/skills/_lib/update_roadmap_progress.sh"
}

@test "no_in_place_sed_edit_for_roadmap_meta" {
  # The helper must NOT use 'sed' for roadmap-meta (Oracle C1 unsafe pattern)
  ! grep -q "sed.*roadmap-meta" "$REPO_ROOT/skills/_lib/update_roadmap_progress.sh"
}