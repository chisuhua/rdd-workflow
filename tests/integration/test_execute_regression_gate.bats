#!/usr/bin/env bats
# tests/integration/test_execute_regression_gate.bats
# Regression contract for the execute phase unified regression gate.

load ../test_helper

GATE="$REPO_ROOT/skills/execute/scripts/run_regression_gate.sh"
BASELINE="$REPO_ROOT/tests/KNOWN_FAILURES.txt"

setup() {
  cd "$REPO_ROOT"
  TEST_BIN="$BATS_TEST_TMPDIR/bin"
  mkdir -p "$TEST_BIN"
  ORIGINAL_BASELINE="$BATS_TEST_TMPDIR/original-known-failures"
  if [ -f "$BASELINE" ]; then
    cp "$BASELINE" "$ORIGINAL_BASELINE"
  else
    : > "$ORIGINAL_BASELINE"
  fi
}

teardown() {
  if [ -s "$ORIGINAL_BASELINE" ]; then
    cp "$ORIGINAL_BASELINE" "$BASELINE"
  else
    rm -f "$BASELINE"
  fi
}

write_fake_bats() {
  local output="$1"
  local exit_status="${2:-0}"
  cat > "$TEST_BIN/bats" <<EOF
#!/usr/bin/env bash
printf '%s\n' "$output"
printf 'ARGS: %s\n' "\$*"
exit $exit_status
EOF
  chmod +x "$TEST_BIN/bats"
}

@test "run_regression_gate: baseline present runs report_regression.sh" {
  printf '%s\n' 'known failure: baseline fixture # existing reason' > "$BASELINE"
  write_fake_bats 'not ok 1 known failure: baseline fixture'

  run env PATH="$TEST_BIN:$PATH" bash "$GATE"

  [ "$status" -eq 0 ]
  [[ "$output" == *"baseline 对比"* ]]
  [[ "$output" == *"已知失败"* ]]
  [[ "$output" == *"新增失败: 0"* ]]
}

@test "run_regression_gate: baseline absent falls back to recursive bats" {
  rm -f "$BASELINE"
  write_fake_bats '1..0' 0

  run env PATH="$TEST_BIN:$PATH" bash "$GATE"

  [ "$status" -eq 0 ]
  [[ "$output" == *"bats tests/ --recursive"* ]]
  [[ "$output" == *"ARGS: tests/ --recursive"* ]]
}

@test "run_regression_gate: SKIP_REGRESSION=1 skips both paths" {
  rm -f "$BASELINE"
  write_fake_bats 'this should not run' 1

  run env PATH="$TEST_BIN:$PATH" SKIP_REGRESSION=1 bash "$GATE"

  [ "$status" -eq 0 ]
  [[ "$output" == *"跳过全量回归门"* ]]
  [[ "$output" != *"this should not run"* ]]
}