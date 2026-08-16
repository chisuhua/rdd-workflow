#!/usr/bin/env bats

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  export REPO_ROOT
  cd "$REPO_ROOT"
  TMP_REPO="$(mktemp -d)"
  cd "$TMP_REPO"
  git init -q
}

teardown() {
  rm -rf "$TMP_REPO"
}

@test "spoke-init copies cursorrules to valid git repo" {
  cd "$TMP_REPO"
  run bash "$REPO_ROOT/install.sh" --spoke-init "$TMP_REPO"
  [ "$status" -eq 0 ]
  [ -f "$TMP_REPO/.cursorrules" ]
}

@test "spoke-init warns on non-git target" {
  NON_GIT_DIR="$(mktemp -d)"
  run bash "$REPO_ROOT/install.sh" --spoke-init "$NON_GIT_DIR"
  [ "$status" -eq 0 ]
  [[ "$output" =~ "not a git repository" ]]
  rm -rf "$NON_GIT_DIR"
}
