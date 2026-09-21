#!/usr/bin/env bats
# tests/integration/test_doctor_ai_context_bootstrap.bats
# Integration tests for `rddf doctor --category ai-context-bootstrap`

load ../test_helper

bats_require_minimum_version 1.5.0

setup() {
  export TMPDIR="/tmp/rddf-doctor-ai-$$"
  mkdir -p "$TMPDIR"
}

teardown() {
  rm -rf "$TMPDIR" 2>/dev/null || true
}

@test "doctor ai-context-bootstrap: warns when no AI config files exist" {
  cd "$TMPDIR"
  run python3 -m _lib.cli doctor --category ai-context-bootstrap
  [ "$status" -eq 0 ]
  echo "$output" | grep -qi "未找到\|WARNING\|ai-context"
}

@test "doctor ai-context-bootstrap: reports healthy when AGENTS.md has block" {
  cd "$TMPDIR"
  python3 -m _lib.cli setup ai-context --yes --target "$TMPDIR"
  run python3 -m _lib.cli doctor --category ai-context-bootstrap
  [ "$status" -eq 0 ]
}

@test "doctor ai-context-bootstrap: warns when config files exist but no block" {
  echo "some content" > "$TMPDIR/AGENTS.md"
  cd "$TMPDIR"
  run python3 -m _lib.cli doctor --category ai-context-bootstrap
  [ "$status" -eq 0 ]
}

@test "doctor ai-context-bootstrap: runs from rddf CLI path" {
  cd "$TMPDIR"
  run bash "$REPO_ROOT/skills/cli/rddf.sh" doctor --category ai-context-bootstrap
  [ "$status" -eq 0 ]
}