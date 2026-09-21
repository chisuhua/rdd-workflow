#!/usr/bin/env bats
# tests/integration/test_rddf_init_hint.bats
# Verify `rddf init` output includes the setup hint.

load ../test_helper

bats_require_minimum_version 1.5.0

setup() {
  export TMPDIR="/tmp/rddf-init-hint-$$"
  mkdir -p "$TMPDIR"
}

teardown() {
  rm -rf "$TMPDIR" 2>/dev/null || true
}

@test "rddf init: output includes setup ai-context hint" {
  run bash "$REPO_ROOT/skills/cli/rddf.sh" init "$TMPDIR"
  [ "$status" -eq 0 ]
  [[ "$output" == *"setup ai-context"* ]] || {
    echo "Expected hint not found in output"
    echo "Output: $output"
    false
  }
}

@test "rddf init --help: does not include setup hint" {
  run bash "$REPO_ROOT/skills/cli/rddf.sh" init --help
  [ "$status" -eq 0 ]
  # --help output should mention init usage, not setup hint
  [[ "$output" == *"usage"* ]]
}