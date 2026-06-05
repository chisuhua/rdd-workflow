#!/usr/bin/env bats
# tests/_lib/test_worktree.bats
# Unit tests for skills/_lib/worktree.sh helpers:
#   - wt_path_for_branch
#   - is_change_committed
#   - find_default_branch
#
# Run: bats tests/_lib/test_worktree.bats

load ../test_helper
load_lib worktree

setup() {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  # Override PROJECT_ROOT so is_change_committed resolves to this scratch repo
  # (the function takes PROJECT_ROOT over the current directory's git toplevel)
  export PROJECT_ROOT="$TEST_REPO"
  git init -q
  git config user.email "test@test"
  git config user.name "test"
  echo "initial" > README.md
  git add README.md
  git commit -q -m "initial"
  # Create 2 worktrees
  git worktree add -b openspec/test-1 .zcf/test-1-wt HEAD
  git worktree add -b openspec/test-2 .zcf/test-2-wt HEAD
}

teardown() {
  cd /
  rm -rf "$TEST_REPO"
}

@test "wt_path_for_branch returns correct path" {
  result=$(wt_path_for_branch "test-1")
  [[ "$result" == *"test-1-wt"* ]]
}

@test "wt_path_for_branch returns empty for nonexistent" {
  result=$(wt_path_for_branch "nonexistent")
  [[ -z "$result" ]]
}

@test "is_change_committed returns 0 for committed file" {
  mkdir -p openspec/changes/real
  touch openspec/changes/real/.openspec.yaml
  git add openspec/changes/real/.openspec.yaml
  git commit -q -m "add change"
  run is_change_committed "real"
  [ "$status" -eq 0 ]
}

@test "is_change_committed returns 1 for uncommitted" {
  mkdir -p openspec/changes/fake
  touch openspec/changes/fake/.openspec.yaml
  # NOT committing
  run is_change_committed "fake"
  [ "$status" -eq 1 ]
}

@test "find_default_branch returns 'main' or current" {
  result=$(find_default_branch)
  [[ "$result" == "main" ]] || [[ "$result" == "master" ]]
}
