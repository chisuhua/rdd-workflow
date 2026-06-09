#!/usr/bin/env bats
# tests/integration/test_find_default_branch_in_worktree.bats
# Regression lock for the worktree-context fallback bug
# (see general-harden-doc-consistency spec.md, scenario:
#  "find_default_branch works in worktree context").
#
# Lock: find_default_branch must return master/main/develop (the
# project default branch) when called from inside a worktree,
# never the worktree's own openspec/<name> branch.

load ../test_helper
load_lib worktree

setup() {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  git init -q -b master
  git config user.email "test@test"
  git config user.name "test"
  echo "initial" > README.md
  git add README.md
  git commit -q -m "initial"
  export PROJECT_ROOT="$TEST_REPO"
  git worktree add -b openspec/test-wt .zcf/test-wt HEAD
}

teardown() {
  cd /
  rm -rf "$TEST_REPO"
}

@test "find_default_branch returns default branch from inside worktree" {
  cd "$TEST_REPO/.zcf/test-wt"
  result=$(find_default_branch)
  [[ "$result" == "master" ]] || [[ "$result" == "main" ]] || [[ "$result" == "develop" ]]
}

@test "find_default_branch does not return openspec branch" {
  cd "$TEST_REPO/.zcf/test-wt"
  result=$(find_default_branch)
  [[ "$result" != openspec/* ]]
}

@test "find_default_branch returns same value from main repo and worktree" {
  from_main=$(cd "$TEST_REPO" && find_default_branch)
  from_wt=$(cd "$TEST_REPO/.zcf/test-wt" && find_default_branch)
  [ "$from_main" = "$from_wt" ]
}
