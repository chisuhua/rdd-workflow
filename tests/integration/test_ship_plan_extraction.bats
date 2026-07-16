#!/usr/bin/env bats
# tests/integration/test_ship_plan_extraction.bats
# P3-2 regression: Phase 1 of guide-ship.md (COMMIT GATE + parallel conflict
# detection + execution mode selection + worktree/lightweight setup + plan
# generation + iteration.json hook) was a 123-line inline bash block. Extracted
# to skills/_lib/ship_plan.sh.
#
# These tests lock the refactor in place:
#   1. ship_plan.sh exists with the expected function exports.
#   2. guide-ship.md sources ship_plan.sh and calls detect_execution_mode +
#      setup_execution_workspace + generate_implementation_plan + record_iteration.
#   3. guide-ship.md no longer inlines COMMIT GATE / parallel conflict / worktree
#      setup / plan generation logic.
#   4. Runtime: detect_execution_mode returns the correct mode on a scratch repo.

load ../test_helper

# Replaced Phase 1 inline block spans lines 144-348 (the COMMIT GATE +
# conflict detection + mode setup + plan generation block). Other Phase 1
# blocks (rddf-session setup, ACTIVE_CHANGES table) were intentionally
# left in markdown because they're small (<30 lines) and don't fit
# the ship_plan.sh helper scope.
REPLACED_RANGE="144,348p"

@test "skills/_lib/ship_plan.sh exists with expected function exports" {
  [ -f "$REPO_ROOT/skills/_lib/ship_plan.sh" ]
  grep -q "^check_artifacts_committed()" "$REPO_ROOT/skills/_lib/ship_plan.sh"
  grep -q "^detect_execution_mode()" "$REPO_ROOT/skills/_lib/ship_plan.sh"
  grep -q "^setup_execution_workspace()" "$REPO_ROOT/skills/_lib/ship_plan.sh"
  grep -q "^generate_implementation_plan()" "$REPO_ROOT/skills/_lib/ship_plan.sh"
  grep -q "^record_iteration_status()" "$REPO_ROOT/skills/_lib/ship_plan.sh"
}

@test "ship_plan.sh sources worktree.sh for wt_path_for_branch + find_default_branch" {
  [ -f "$REPO_ROOT/skills/_lib/ship_plan.sh" ]
  grep -q "worktree.sh" "$REPO_ROOT/skills/_lib/ship_plan.sh"
}

@test "guide-ship.md Phase 1 sources and uses ship_plan.sh helpers" {
  [ -f "$REPO_ROOT/skills/guide-ship.md" ]
  grep -nE 'source .*_lib/ship_plan.sh' "$REPO_ROOT/skills/guide-ship.md"
  grep -nE 'detect_execution_mode|setup_execution_workspace|generate_implementation_plan|record_iteration_status' "$REPO_ROOT/skills/guide-ship.md"
}

@test "guide-ship.md Phase 1 no longer inlines COMMIT GATE logic" {
  [ -f "$REPO_ROOT/skills/guide-ship.md" ]
  ! sed -n "$REPLACED_RANGE" "$REPO_ROOT/skills/guide-ship.md" | grep -qE 'git status --porcelain .*openspec/changes/'
  ! sed -n "$REPLACED_RANGE" "$REPO_ROOT/skills/guide-ship.md" | grep -qE 'git show HEAD:.*openspec.yaml'
}

@test "guide-ship.md Phase 1 no longer inlines parallel conflict detection" {
  [ -f "$REPO_ROOT/skills/guide-ship.md" ]
  ! sed -n "$REPLACED_RANGE" "$REPO_ROOT/skills/guide-ship.md" | grep -qE 'openspec\\/'
  ! sed -n "$REPLACED_RANGE" "$REPO_ROOT/skills/guide-ship.md" | grep -qE 'grep -v archive/'
}

@test "guide-ship.md Phase 1 no longer inlines worktree creation in markdown bash block" {
  [ -f "$REPO_ROOT/skills/guide-ship.md" ]
  ! sed -n "$REPLACED_RANGE" "$REPO_ROOT/skills/guide-ship.md" | grep -qE 'git worktree add .*\\.rddf/wt/'
}

@test "detect_execution_mode returns lightweight when no parallel conflict" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  git init -q -b master
  git config user.email "test@test"
  git config user.name "test"
  echo "x" > README.md
  git add README.md && git commit -q -m "initial"
  mkdir -p openspec/changes/single-change
  source "$REPO_ROOT/skills/_lib/worktree.sh"
  source "$REPO_ROOT/skills/_lib/ship_plan.sh"
  result=$(detect_execution_mode "$TEST_REPO" "single-change")
  [ "$result" = "lightweight" ]
  rm -rf "$TEST_REPO"
}

@test "detect_execution_mode returns worktree when active worktree exists" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  git init -q -b master
  git config user.email "test@test"
  git config user.name "test"
  echo "x" > README.md
  git add README.md && git commit -q -m "initial"
  mkdir -p openspec/changes/c1 openspec/changes/c2
  git worktree add -b openspec/c1 .rddf/wt/c1 HEAD >/dev/null 2>&1
  source "$REPO_ROOT/skills/_lib/worktree.sh"
  source "$REPO_ROOT/skills/_lib/ship_plan.sh"
  result=$(detect_execution_mode "$TEST_REPO" "c2")
  [ "$result" = "worktree" ]
  rm -rf "$TEST_REPO"
}

@test "guide-ship.md Phase 1 source block is now ≤ 30 lines (was 200+)" {
  [ -f "$REPO_ROOT/skills/guide-ship.md" ]
  # Count lines in the FIRST bash block under Phase 1 (lines 32-417 range).
  # After extraction, this should be a thin orchestrator ≤ 30 lines.
  local block_lines
  block_lines=$(awk 'NR>=32 && NR<=417 && /^```bash$/{n++; next} NR>=32 && NR<=417 && /^```$/{if(n>0){exit}} NR>=32 && NR<=417 && n{print}' "$REPO_ROOT/skills/guide-ship.md" | wc -l)
  [ "$block_lines" -le 30 ]
}