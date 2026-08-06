#!/usr/bin/env bats
#
# Wave 8 / fix-debt-audit-2026-07-14 / Wave 2.3: archive.sh smoke tests.
# Tests the public surface of _lib/archive.sh:
#   - archive_change() validates input (rejects empty name)
#   - archive_change() integrates with worktree.sh helpers
#   - missing worktree is a graceful failure
# Full archive flow is integration-tested in test_guide_ship_skill.bats
# and the CI worktree subset.

load ../test_helper

setup() {
  cd "$REPO_ROOT"
}

@test "archive.sh: sourceable" {
  run bash -c "source '$REPO_ROOT/_lib/archive.sh' && echo 'loaded'"
  [ "$status" -eq 0 ]
  [[ "$output" == *"loaded"* ]]
}

@test "archive.sh: defines archive_change function" {
  run bash -c "source '$REPO_ROOT/_lib/archive.sh' && declare -F archive_change"
  [ "$status" -eq 0 ]
  [[ "$output" == *"archive_change"* ]]
}

@test "archive_change: empty name exits non-zero" {
  run bash -c "
    source '$REPO_ROOT/_lib/worktree.sh'
    source '$REPO_ROOT/_lib/archive.sh'
    archive_change ''
  "
  [ "$status" -ne 0 ]
}

@test "archive_change: nonexistent worktree fails gracefully" {
  # Create a temp repo and try to archive a non-existent change
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  git init -q
  git config user.email "test@test"
  git config user.name "test"
  echo "x" > a && git add a && git commit -q -m init

  run bash -c "
    source '$REPO_ROOT/_lib/worktree.sh'
    source '$REPO_ROOT/_lib/archive.sh'
    archive_change 'nonexistent-change-xyz'
  "
  cd /
  rm -rf "$TEST_REPO"
  [ "$status" -ne 0 ]
}

@test "archive.sh: file exists and is readable" {
  [ -f "$REPO_ROOT/_lib/archive.sh" ]
  [ -r "$REPO_ROOT/_lib/archive.sh" ]
}
