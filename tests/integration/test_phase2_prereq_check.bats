#!/usr/bin/env bats
# test_phase2_prereq_check.bats
#
# P2 前置检查（per fix-builder-handoff-p2-lifecycle-truth）：worktree 从 HEAD 建 ⇒
# 主仓里「未提交」或「基线之后才提交」的产物在 worktree 里不可见。P2 必须在建
# worktree 之前把这种差异**报出来**（commit sha + 文件清单），否则续接者会在
# worktree 里看不到授权台账等产物（2026-11-26 实测）。

load ../test_helper

setup() {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  git init -q -b master
  git config user.email "test@test"
  git config user.name "test"
  echo x > a && git add a && git commit -q -m init
  mkdir -p .rddf/plans .rddf/state/builder openspec/changes/add-x
  echo "# plan" > .rddf/plans/add-x.md
  echo "# tasks" > openspec/changes/add-x/tasks.md
  git add -A && git commit -q -m artifacts
  # The recorded baseline = the commit the worktree would be built from.
  BASE_SHA="$(git rev-parse HEAD)"
  write_handoff "$BASE_SHA"
}

teardown() {
  cd /
  rm -rf "$TEST_REPO"
}

write_handoff() {
  local base="${1:-}"
  cat > .rddf/state/builder/add-x.json <<JSON
{
  "schema": "builder-handoff-v1",
  "version": 1,
  "owner": "rdd-builder",
  "change_name": "add-x",
  "current_phase": "phase-2",
  "execution_mode_decision": {"mode": "worktree", "branch_base_sha": "$base"}
}
JSON
}

_run_phase2() {
  PROJECT_ROOT="$TEST_REPO" bash "$REPO_ROOT/skills/rdd-builder/scripts/phase2_execute.sh" add-x
}

@test "phase2: reports the main-repo commits made after the recorded baseline" {
  echo "ledger" > ledger.md
  git add ledger.md && git commit -q -m "ledger entry"
  run _run_phase2
  [ "$status" -eq 0 ]
  [[ "$output" == *"领先上次 P2 基线"* ]]
  [[ "$output" == *"$BASE_SHA"* ]]
  [[ "$output" == *"ledger.md"* ]]
}

@test "phase2: reports uncommitted tracked changes in the main repo" {
  echo "dirty" >> a
  run _run_phase2
  [ "$status" -eq 0 ]
  [[ "$output" == *"未提交的 tracked 改动"* ]]
}

@test "phase2: stays quiet when the main repo is clean and at the baseline" {
  run _run_phase2
  [ "$status" -eq 0 ]
  [[ "$output" != *"领先上次 P2 基线"* ]]
  [[ "$output" != *"未提交的 tracked 改动"* ]]
}

@test "phase2: the check never commits or merges on its own" {
  echo "dirty" >> a
  echo "later" > later.md
  git add later.md && git commit -q -m later
  run _run_phase2
  [ "$status" -eq 0 ]
  # The dirty file is still dirty (nobody committed it for us) and the branch
  # is untouched by the check.
  run git status --porcelain
  [[ "$output" == *"a"* ]]
}
