#!/usr/bin/env bats
# tests/_lib/test_worktree.bats
# Unit tests for _lib/worktree.sh helpers:
#   - wt_path_for_branch
#   - find_default_branch
#   - main_repo_root
#
# Run: bats tests/_lib/test_worktree.bats

load ../test_helper
load_lib worktree

setup() {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  export PROJECT_ROOT="$TEST_REPO"
  git init -q -b master
  git config user.email "test@test"
  git config user.name "test"
  echo "initial" > README.md
  git add README.md
  git commit -q -m "initial"
  # Create 2 worktrees
  git worktree add -b openspec/test-1 .rddf/wt/test-1 HEAD
  git worktree add -b openspec/test-2 .rddf/wt/test-2 HEAD
}

teardown() {
  cd /
  rm -rf "$TEST_REPO"
}

@test "wt_path_for_branch returns correct path" {
  result=$(wt_path_for_branch "test-1")
  [[ "$result" == *"rddf/wt/test-1"* ]]
}

@test "wt_path_for_branch returns empty for nonexistent" {
  result=$(wt_path_for_branch "nonexistent")
  [[ -z "$result" ]]
}

@test "find_default_branch returns 'master' or 'main'" {
  result=$(find_default_branch)
  [[ "$result" == "master" ]] || [[ "$result" == "main" ]]
}

@test "find_default_branch does not return openspec branch from worktree" {
  cd "$TEST_REPO/.rddf/wt/test-1"
  result=$(find_default_branch)
  [[ "$result" != openspec/* ]]
}

@test "main_repo_root returns main repo path from worktree" {
  cd "$TEST_REPO/.rddf/wt/test-1"
  result=$(main_repo_root)
  [ "$result" = "$TEST_REPO" ]
}

@test "main_repo_root returns main repo path from main repo" {
  cd "$TEST_REPO"
  result=$(main_repo_root)
  [ "$result" = "$TEST_REPO" ]
}

@test "main_repo_root returns main repo from external worktree" {
  ext_wt=$(mktemp -d)
  git -C "$TEST_REPO" worktree add -b openspec/external "$ext_wt" HEAD >/dev/null 2>&1
  cd "$ext_wt"
  result=$(main_repo_root)
  [ "$result" = "$TEST_REPO" ]
  rm -rf "$ext_wt"
}
