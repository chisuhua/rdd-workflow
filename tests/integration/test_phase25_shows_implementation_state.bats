#!/usr/bin/env bats
# test_phase25_shows_implementation_state.bats
#
# The P2.5 review is the ONLY place in the flow that reads the builder handoff
# before the merge decision (per fix-builder-handoff-p2-lifecycle-truth D-1).
# It therefore has to show the implementation's REAL state — the task counter
# on disk — and to flag a handoff that claims "completed" while tasks are
# unchecked (the legacy setup-time value).

load ../test_helper

setup() {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  mkdir -p .rddf/state/builder openspec/changes/c1
  write_handoff "completed"
  printf -- '- [ ] a\n- [ ] b\n' > openspec/changes/c1/tasks.md
}

teardown() {
  cd /
  rm -rf "$TEST_REPO"
}

write_handoff() {
  cat > .rddf/state/builder/c1.json <<JSON
{
  "schema": "builder-handoff-v1",
  "version": 1,
  "owner": "rdd-builder",
  "change_name": "c1",
  "current_phase": "phase-2",
  "execution_status": "$1"
}
JSON
}

_run_review() {
  PROJECT_ROOT="$TEST_REPO" bash "$REPO_ROOT/skills/rdd-builder/scripts/phase2_5_review.sh" c1 < /dev/null
}

@test "phase2.5: shows the real task progress before the decision" {
  run _run_review
  [[ "$output" == *"实现状态：tasks 0/2"* ]]
  [[ "$output" == *"未完成"* ]]
}

@test "phase2.5: flags a handoff that claims completion too early" {
  run _run_review
  [[ "$output" == *"不一致"* ]]
  [[ "$output" == *"以 tasks 为准"* ]]
}

@test "phase2.5: no inconsistency warning when the handoff matches the truth" {
  write_handoff "running"
  printf -- '- [x] a\n- [x] b\n' > openspec/changes/c1/tasks.md
  run _run_review
  [[ "$output" == *"实现状态：tasks 2/2"* ]]
  [[ "$output" == *"已完成"* ]]
  [[ "$output" != *"不一致"* ]]
}
