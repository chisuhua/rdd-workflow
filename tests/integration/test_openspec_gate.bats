#!/usr/bin/env bats
# tests/integration/test_openspec_gate.bats
# OpenSpec gate: detects staged files not linked to an openspec change.

load ../test_helper

setup() {
  TMP_REPO=$(mktemp -d)
  cd "$TMP_REPO"
  git init >/dev/null 2>&1
  git config user.email "test@example.com"
  git config user.name "Test"
  mkdir -p openspec/changes/active-change
  mkdir -p src include plugins drivers
  export TMP_REPO
}

teardown() {
  rm -rf "$TMP_REPO"
  cd "$REPO_ROOT" || true
}

@test "openspec-gate: script exists" {
  [ -f "$REPO_ROOT/skills/openspec-gate/scripts/openspec-gate.sh" ]
}

@test "openspec-gate: block mode fails when staged file is not linked to any change" {
  echo "x" > src/foo.py
  git add src/foo.py
  run env OPENSPEC_GATE_MODE=block bash "$REPO_ROOT/skills/openspec-gate/scripts/openspec-gate.sh"
  [ "$status" -eq 1 ]
  [[ "$output" == *"未关联"* ]]
}

@test "openspec-gate: warn mode succeeds when staged file is not linked" {
  echo "x" > src/foo.py
  git add src/foo.py
  run bash "$REPO_ROOT/skills/openspec-gate/scripts/openspec-gate.sh"
  [ "$status" -eq 0 ]
  [[ "$output" == *"未关联"* ]]
}

@test "openspec-gate: ignores files under openspec" {
  echo "x" > openspec/changes/active-change/spec.md
  git add openspec/changes/active-change/spec.md
  run env OPENSPEC_GATE_MODE=block bash "$REPO_ROOT/skills/openspec-gate/scripts/openspec-gate.sh"
  [ "$status" -eq 0 ]
  [[ "$output" != *"未关联"* ]]
}

@test "openspec-gate: ignores files outside default paths" {
  mkdir -p docs
  echo "x" > docs/readme.md
  git add docs/readme.md
  run env OPENSPEC_GATE_MODE=block bash "$REPO_ROOT/skills/openspec-gate/scripts/openspec-gate.sh"
  [ "$status" -eq 0 ]
}

@test "openspec-gate: ignores files with non-default extensions" {
  echo "x" > src/foo.md
  git add src/foo.md
  run env OPENSPEC_GATE_MODE=block bash "$REPO_ROOT/skills/openspec-gate/scripts/openspec-gate.sh"
  [ "$status" -eq 0 ]
}

@test "openspec-gate: linked change matches staged file path" {
  mkdir -p src/active-change
  echo "x" > src/active-change/foo.py
  git add src/active-change/foo.py
  run env OPENSPEC_GATE_MODE=block bash "$REPO_ROOT/skills/openspec-gate/scripts/openspec-gate.sh"
  [ "$status" -eq 0 ]
}
