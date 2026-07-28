#!/usr/bin/env bats
# tests/integration/test_regression_gate.bats
# Regression gate: quick/full runner + pre-commit hook

load ../test_helper

@test "regression-gate: quick subcommand runs" {
  run bash scripts/regression-test.sh quick
  [ "$status" -eq 0 ]
}

@test "regression-gate: full subcommand runs" {
  run bash scripts/regression-test.sh full
  [ "$status" -eq 0 ]
}

@test "regression-gate: SKIP_REGRESSION=1 skips full regression" {
  SKIP_REGRESSION=1 run bash scripts/regression-test.sh full
  [ "$status" -eq 0 ]
  [[ "$output" == *"已跳过全量回归"* ]]
}

@test "pre-commit: hooks file exists and detects build changes" {
  assert_file_exists "scripts/hooks/pre-commit"
  run bash scripts/hooks/pre-commit
  [ "$status" -eq 0 ]
}
