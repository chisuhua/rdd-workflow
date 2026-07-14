#!/usr/bin/env bats
#
# Wave 8 / fix-debt-audit-2026-07-14 / Wave 2.3: rddf CLI smoke tests.
# Closes the "rddf 1505 lines, 0 tests" gap from the debt audit.
# Tests only check that subcommands parse and exit cleanly with
# well-known flags; behavior tests for individual rddf_* functions
# live in their respective subcommand test files (test_status.bats, etc).

load ../test_helper

setup() {
  cd "$REPO_ROOT"
}

@test "rddf: --help exits 0" {
  run ./rddf --help
  [ "$status" -eq 0 ]
}

@test "rddf: help exits 0" {
  run ./rddf help
  [ "$status" -eq 0 ]
}

@test "rddf: status exits 0" {
  run ./rddf status
  [ "$status" -eq 0 ]
}

@test "rddf: feature exits 0" {
  run ./rddf feature
  [ "$status" -eq 0 ]
}

@test "rddf: deps exits 0" {
  run ./rddf deps
  [ "$status" -eq 0 ]
}

@test "rddf: session exits 0" {
  run ./rddf session
  [ "$status" -eq 0 ]
}

@test "rddf: session --help exits 0" {
  run ./rddf session --help
  [ "$status" -eq 0 ]
}

@test "rddf: session list exits 0" {
  run ./rddf session list
  [ "$status" -eq 0 ]
}

@test "rddf: archive (no args) exits non-zero with usage" {
  run ./rddf archive
  [ "$status" -ne 0 ]
  [[ "$output" == *"用法"* || "$output" == *"usage"* ]]
}

@test "rddf: cleanup --help exits 0" {
  run ./rddf cleanup --help
  [ "$status" -eq 0 ]
}

@test "rddf: validate exits 0" {
  run ./rddf validate
  [ "$status" -eq 0 ]
}

@test "rddf: unknown subcommand exits non-zero" {
  run ./rddf nonexistent-subcommand-xyz
  [ "$status" -ne 0 ]
}

@test "rddf: defines at least 20 rddf_* subcommand functions" {
  count=$(grep -cE "^rddf_[a-z_]+\(\)" "$REPO_ROOT/rddf")
  [ "$count" -ge 20 ]
}
