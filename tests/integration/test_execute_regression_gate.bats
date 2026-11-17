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
  # Isolation: drive the gate against a TEMP baseline via
  # RDDF_KNOWN_FAILURES_FILE. This file used to `printf >` the repo's real
  # baseline and `rm -f` it three times, restoring it from teardown. A
  # per-file timeout (collect_bats_failures.sh kills at 30s) skips teardown,
  # so those writes survived as real baseline corruption — the gate destroyed
  # its own baseline (see .rddf/improvements/fix-regression-baseline-integrity.md).
  ISOLATED_BASELINE="$BATS_TEST_TMPDIR/known-failures-baseline.txt"
  : > "$ISOLATED_BASELINE"
  ABSENT_BASELINE="$BATS_TEST_TMPDIR/no-such-baseline.txt"
  rm -f "$ABSENT_BASELINE"
  REPO_BASELINE_SNAPSHOT="$BATS_TEST_TMPDIR/repo-baseline.snapshot"
  if [ -f "$BASELINE" ]; then
    cp "$BASELINE" "$REPO_BASELINE_SNAPSHOT"
  fi
}

teardown() {
  # Defence in depth: fail loudly if a test ever writes the repo's real
  # baseline again. Under a timeout this teardown does not run, which is
  # exactly why the tests must not touch $BASELINE in the first place.
  if [ -f "$REPO_BASELINE_SNAPSHOT" ]; then
    diff -q "$REPO_BASELINE_SNAPSHOT" "$BASELINE" >/dev/null || {
      echo "REPO BASELINE WAS MUTATED: $BASELINE" >&2
      return 1
    }
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
  printf '%s\n' 'known failure: baseline fixture # existing reason' > "$ISOLATED_BASELINE"
  write_fake_bats 'not ok 1 known failure: baseline fixture'

  run env PATH="$TEST_BIN:$PATH" RDDF_KNOWN_FAILURES_FILE="$ISOLATED_BASELINE" bash "$GATE"

  [ "$status" -eq 0 ]
  [[ "$output" == *"baseline 对比"* ]]
  [[ "$output" == *"已知失败"* ]]
  [[ "$output" == *"新增失败: 0"* ]]
}

@test "run_regression_gate: baseline absent falls back to recursive bats" {
  write_fake_bats '1..0' 0

  run env PATH="$TEST_BIN:$PATH" RDDF_KNOWN_FAILURES_FILE="$ABSENT_BASELINE" bash "$GATE"

  [ "$status" -eq 0 ]
  [[ "$output" == *"bats tests/ --recursive"* ]]
  [[ "$output" == *"ARGS: tests/ --recursive"* ]]
}

@test "run_regression_gate: RDDF_KNOWN_FAILURES_FILE is honoured (not the hardcoded default)" {
  # The existence test must use the RESOLVED path. When it read the hardcoded
  # default instead, a caller pointing at a temp baseline silently fell back to
  # recursive bats — the override was invisible on this code path.
  printf '%s\n' 'known failure: isolated fixture # existing reason' > "$ISOLATED_BASELINE"
  write_fake_bats 'not ok 1 known failure: isolated fixture'

  run env PATH="$TEST_BIN:$PATH" RDDF_KNOWN_FAILURES_FILE="$ISOLATED_BASELINE" bash "$GATE"

  [ "$status" -eq 0 ]
  [[ "$output" == *"baseline 对比"* ]]
  [[ "$output" != *"bats tests/ --recursive"* ]]
  # Decisive assertion — content, not wording. The isolated fixture name exists
  # ONLY in $ISOLATED_BASELINE. If any link in the chain ignored the override
  # and read the repo's real baseline instead, that name would be reported as a
  # NEW failure (新增失败: 1) rather than a known one ⇒ this turns red.
  [[ "$output" == *"新增失败: 0"* ]]
}

@test "run_regression_gate: SKIP_REGRESSION=1 skips both paths" {
  write_fake_bats 'this should not run' 1

  run env PATH="$TEST_BIN:$PATH" SKIP_REGRESSION=1 bash "$GATE"

  [ "$status" -eq 0 ]
  [[ "$output" == *"跳过全量回归门"* ]]
  [[ "$output" != *"this should not run"* ]]
}
