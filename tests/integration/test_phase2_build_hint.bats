#!/usr/bin/env bats
# test_phase2_build_hint.bats
#
# Phase 2 must announce a missing build directory in the fresh worktree
# (per improve-worktree-build-hint): the first full build in a worktree can
# take many minutes (measured 2026-11-26: 19 minutes on a CMake project with
# large TUs), and the session burned 7 `sleep` polls waiting for it.
#
# The hint is ONE fixed-text line on stderr. It must not appear when a
# `build/` directory exists (noise) and it must not change any behaviour.

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
  # worktree mode (the handoff drives the mode; no mode ⇒ worktree)
  cat > .rddf/state/builder/add-x.json <<'JSON'
{
  "schema": "builder-handoff-v1",
  "version": 1,
  "owner": "rdd-builder",
  "change_name": "add-x",
  "current_phase": "phase-2"
}
JSON
}

teardown() {
  cd /
  rm -rf "$TEST_REPO"
}

_run_phase2() {
  PROJECT_ROOT="$TEST_REPO" bash "$REPO_ROOT/skills/rdd-builder/scripts/phase2_execute.sh" add-x
}

@test "phase2: a worktree without build/ gets the hint on stderr" {
  run _run_phase2
  [ "$status" -eq 0 ]
  [[ "$output" == *"build/"* ]]
  [[ "$output" == *"后台任务"* ]]
  [[ "$output" == *"勿 sleep 轮询"* ]]
}

@test "phase2: the hint does not pollute stdout" {
  run _run_phase2
  [ "$status" -eq 0 ]
  # bats merges stderr into $output — re-run capturing stdout only.
  stdout_only="$(PROJECT_ROOT="$TEST_REPO" bash "$REPO_ROOT/skills/rdd-builder/scripts/phase2_execute.sh" add-x 2>/dev/null)"
  [[ "$stdout_only" != *"勿 sleep 轮询"* ]]
}

@test "phase2: an existing build/ directory means no hint (no noise)" {
  mkdir -p .rddf/wt/add-x/build
  run _run_phase2
  [ "$status" -eq 0 ]
  [[ "$output" != *"勿 sleep 轮询"* ]]
}

@test "phase2: lightweight mode never hints (the main repo is the workspace)" {
  cat > .rddf/state/builder/add-x.json <<'JSON'
{
  "schema": "builder-handoff-v1",
  "version": 1,
  "owner": "rdd-builder",
  "change_name": "add-x",
  "current_phase": "phase-2",
  "execution_mode_decision": {"mode": "lightweight"}
}
JSON
  run _run_phase2
  [ "$status" -eq 0 ]
  [[ "$output" != *"勿 sleep 轮询"* ]]
}
