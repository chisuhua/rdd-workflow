#!/usr/bin/env bats
#
# Phase 2 no longer gates on the git working tree.
#
# The former gate ran `git status --porcelain` over the WHOLE repository and
# exited 3 whenever anything was dirty — including files unrelated to the
# change (e.g. the agent's own .rddf/state/role.json). It was also inert for
# `openspec/` in projects where that directory is gitignored
# (git.openspec_tracked=false), so it never actually protected the artifacts
# it claimed to protect.
#
# Commit semantics are enforced upstream instead: _lib/archive.sh's
# check_worktree_commits refuses to merge a branch with no new commits.
# These cases lock both halves of that contract.

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
  # lightweight execution mode: no worktree is created
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
}

teardown() {
  cd /
  rm -rf "$TEST_REPO"
}

_run_phase2() {
  PROJECT_ROOT="$TEST_REPO" bash "$REPO_ROOT/skills/rdd-builder/scripts/phase2_execute.sh" add-x
}

@test "phase2: unrelated dirty file does not block Phase 2" {
  echo "dirty" > .rddf/state/role.json
  run _run_phase2
  [ "$status" -eq 0 ]
  [[ "$output" == *"Phase 2 worktree setup complete"* ]]
}

@test "phase2: uncommitted change artifacts do not block Phase 2" {
  echo "more tasks" >> openspec/changes/add-x/tasks.md
  run _run_phase2
  [ "$status" -eq 0 ]
  [[ "$output" == *"Phase 2 worktree setup complete"* ]]
}

@test "phase2: script no longer mentions COMMIT GATE" {
  run grep -c "COMMIT GATE" "$REPO_ROOT/skills/rdd-builder/scripts/phase2_execute.sh"
  [ "$output" = "0" ]
}

@test "phase2: worktree mode carries uncommitted artifacts into the worktree" {
  # `git worktree add` builds from HEAD — uncommitted files are absent there.
  # Without the carry-over, P2 would fail with "plan file missing" for
  # exactly the changes that are not committed yet.
  cat > .rddf/state/builder/add-x.json <<'JSON'
{
  "schema": "builder-handoff-v1",
  "version": 1,
  "owner": "rdd-builder",
  "change_name": "add-x",
  "current_phase": "phase-2"
}
JSON
  echo "more tasks" >> openspec/changes/add-x/tasks.md
  run _run_phase2
  [ "$status" -eq 0 ]
  [[ "$output" == *"mode=worktree"* ]]
  [ -f ".rddf/wt/add-x/.rddf/plans/add-x.md" ]
  [ -f ".rddf/wt/add-x/openspec/changes/add-x/tasks.md" ]
}

@test "phase2: carry-over does not create a nested directory when artifacts are already committed" {
  # `cp -R src dst` with an existing dst copies src INTO dst →
  # openspec/changes/add-x/add-x/. The carry-over must copy CONTENTS.
  cat > .rddf/state/builder/add-x.json <<'JSON'
{
  "schema": "builder-handoff-v1",
  "version": 1,
  "owner": "rdd-builder",
  "change_name": "add-x",
  "current_phase": "phase-2"
}
JSON
  git add -A && git commit -q -m "artifacts"
  run _run_phase2
  [ "$status" -eq 0 ]
  [ -f ".rddf/wt/add-x/openspec/changes/add-x/tasks.md" ]
  [ ! -d ".rddf/wt/add-x/openspec/changes/add-x/add-x" ]
}

@test "phase2: carry-over is skipped when worktree creation falls back to the main repo" {
  # When `git worktree add` fails (branch already exists) the script falls
  # back to the main repo, so source == target. `cp -R a a` fails with
  # "cannot copy a directory into itself" and `set -e` would abort P2.
  cat > .rddf/state/builder/add-x.json <<'JSON'
{
  "schema": "builder-handoff-v1",
  "version": 1,
  "owner": "rdd-builder",
  "change_name": "add-x",
  "current_phase": "phase-2"
}
JSON
  git branch openspec/add-x
  run _run_phase2
  [ "$status" -eq 0 ]
  [[ "$output" == *"Phase 2 worktree setup complete"* ]]
  # The fallback ran (execution dir == main repo), and the carry-over was
  # skipped instead of aborting P2 on "cannot copy a directory into itself".
  [[ "$output" == *"dir=$TEST_REPO"* ]]
  [ ! -d "openspec/changes/add-x/add-x" ]
}

@test "archive: check_worktree_commits still refuses a branch with no new commits" {
  # The commit gate moved upstream — this is the safety net that replaced it.
  git branch openspec/add-x
  run bash -c "
    cd '$TEST_REPO'
    source '$REPO_ROOT/_lib/archive.sh'
    check_worktree_commits add-x
  "
  [ "$status" -ne 0 ]
  [[ "$output" == *"无新提交"* ]]
}

@test "archive: check_worktree_commits accepts a branch with new commits" {
  git checkout -q -b openspec/add-x
  echo change >> a && git add a && git commit -q -m "work"
  git checkout -q master
  run bash -c "
    cd '$TEST_REPO'
    source '$REPO_ROOT/_lib/archive.sh'
    check_worktree_commits add-x
  "
  [ "$status" -eq 0 ]
  [[ "$output" == *"1"* ]]
}
