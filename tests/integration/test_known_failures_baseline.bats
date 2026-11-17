#!/usr/bin/env bats
# Regression contract tests for the known-failure baseline workflow.

load ../test_helper

REPORT="$REPO_ROOT/tests/scripts/report_regression.sh"
REFRESH="$REPO_ROOT/tests/scripts/refresh_known_failures.sh"

setup() {
  cd "$REPO_ROOT"
  TEST_BIN="$BATS_TEST_TMPDIR/bin"
  mkdir -p "$TEST_BIN"
  # Isolation: drive report_regression.sh / refresh_known_failures.sh against a
  # TEMP baseline via KNOWN_FAILURES_BASELINE. Writing the repo's real
  # tests/KNOWN_FAILURES.txt from a test is a data-loss path — a per-file
  # timeout (collect_bats_failures.sh uses 30s) kills the run before teardown,
  # leaving the real baseline truncated to whatever the in-flight test wrote.
  ISOLATED_BASELINE="$BATS_TEST_TMPDIR/known-failures-baseline.txt"
  : > "$ISOLATED_BASELINE"
  REPO_BASELINE_SNAPSHOT="$BATS_TEST_TMPDIR/repo-baseline.snapshot"
  if [ -f "$BASELINE" ]; then
    cp "$BASELINE" "$REPO_BASELINE_SNAPSHOT"
  fi
}

teardown() {
  # Defence in depth: fail loudly if the test ever writes the repo's real
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
  local exit_status="${2:-1}"
  cat > "$TEST_BIN/bats" <<EOF
#!/usr/bin/env bash
printf '%s\\n' "$output"
exit $exit_status
EOF
  chmod +x "$TEST_BIN/bats"
}

@test "report: known failures are visible but do not fail the gate" {
  printf '%s\n' 'known failure: environment dependency # existing reason' > "$ISOLATED_BASELINE"
  write_fake_bats 'not ok 1 known failure: environment dependency'

  run env PATH="$TEST_BIN:$PATH" KNOWN_FAILURES_BASELINE="$ISOLATED_BASELINE" bash "$REPORT"

  [ "$status" -eq 0 ]
  [[ "$output" == *"已知失败"* ]]
  [[ "$output" == *"新增失败: 0"* ]]
}

@test "report: unlisted failures are reported and fail the gate" {
  printf '%s\n' 'known failure # existing reason' > "$ISOLATED_BASELINE"
  write_fake_bats $'not ok 1 known failure\nnot ok 2 newly introduced failure'

  run env PATH="$TEST_BIN:$PATH" KNOWN_FAILURES_BASELINE="$ISOLATED_BASELINE" bash "$REPORT"

  [ "$status" -ne 0 ]
  [[ "$output" == *"newly introduced failure"* ]]
  [[ "$output" == *"新增失败"* ]]
}

@test "report: no failed TAP cases returns zero" {
  : > "$ISOLATED_BASELINE"
  write_fake_bats '1..0' 0

  run env PATH="$TEST_BIN:$PATH" KNOWN_FAILURES_BASELINE="$ISOLATED_BASELINE" bash "$REPORT"

  [ "$status" -eq 0 ]
  [[ "$output" == *"0"* ]]
}

@test "refresh: preserves comments for unchanged failures" {
  printf '%s\n' 'known failure # preserve this reason' > "$ISOLATED_BASELINE"
  write_fake_bats $'not ok 1 known failure\nnot ok 2 newly observed failure'

  run env PATH="$TEST_BIN:$PATH" KNOWN_FAILURES_BASELINE="$ISOLATED_BASELINE" bash "$REFRESH"

  [ "$status" -eq 0 ]
  grep -Fq 'known failure # preserve this reason' "$ISOLATED_BASELINE"
  grep -Fq 'newly observed failure' "$ISOLATED_BASELINE"
}

@test "refresh: output is normalized for report comparison" {
  printf '%s\n' 'known failure # reason' > "$ISOLATED_BASELINE"
  write_fake_bats $'not ok 2 known failure\nnot ok 1 another failure'

  run env PATH="$TEST_BIN:$PATH" KNOWN_FAILURES_BASELINE="$ISOLATED_BASELINE" bash "$REFRESH"

  [ "$status" -eq 0 ]
  [ "$(grep -v '^#' "$ISOLATED_BASELINE" | sed '/^[[:space:]]*$/d' | sort | wc -l | tr -d ' ')" -eq 2 ]
}

@test "documentation: CI and README describe the shared regression gate" {
  run grep -n 'tests/scripts/report_regression.sh' "$REPO_ROOT/.github/workflows/test.yml"
  [ "$status" -eq 0 ]
  run grep -n 'KNOWN_FAILURES' "$REPO_ROOT/tests/README.md"
  [ "$status" -eq 0 ]
  run grep -Ein 'known.*failure' "$REPO_ROOT/CHANGELOG.md"
  [ "$status" -eq 0 ]
}
