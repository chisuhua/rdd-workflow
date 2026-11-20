#!/usr/bin/env bats
# Regression contract tests for the known-failure baseline workflow.

load ../test_helper

REPORT="$REPO_ROOT/tests/scripts/report_regression.sh"
REFRESH="$REPO_ROOT/tests/scripts/refresh_known_failures.sh"
# The repo's REAL baseline. Used only as the snapshot/guard subject below —
# never written by these tests (they drive the scripts against
# $ISOLATED_BASELINE via RDDF_KNOWN_FAILURES_FILE). Keep this definition: the
# teardown guard and the shrink guard both reference it, and an empty value
# turns those guards into always-passing assertions.
BASELINE="$REPO_ROOT/tests/KNOWN_FAILURES.txt"

setup() {
  cd "$REPO_ROOT"
  TEST_BIN="$BATS_TEST_TMPDIR/bin"
  mkdir -p "$TEST_BIN"
  # Fail loudly rather than silently degrade: an empty $BASELINE makes the
  # snapshot/teardown guard and the shrink guard below always pass.
  [ -n "$BASELINE" ] || {
    echo "BASELINE is unset — baseline guards cannot judge" >&2
    return 1
  }
  [ -f "$BASELINE" ] || {
    echo "missing repo baseline: $BASELINE" >&2
    return 1
  }
  # Isolation: drive report_regression.sh / refresh_known_failures.sh against a
  # TEMP baseline via RDDF_KNOWN_FAILURES_FILE. Writing the repo's real
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
# collect_bats_failures.sh probes 'bats --version' to decide whether the
# per-test timeout (BATS_TEST_TIMEOUT, bats >= 1.5.0) is available.
if [ "\${1:-}" = "--version" ]; then echo "Bats 1.13.0"; exit 0; fi
printf '%s\\n' "$output"
exit $exit_status
EOF
  chmod +x "$TEST_BIN/bats"
}

@test "report: known failures are visible but do not fail the gate" {
  printf '%s\n' 'known failure: environment dependency # existing reason' > "$ISOLATED_BASELINE"
  write_fake_bats 'not ok 1 known failure: environment dependency'

  run env PATH="$TEST_BIN:$PATH" RDDF_BATS_COLLECT_ACTIVE=0 RDDF_KNOWN_FAILURES_FILE="$ISOLATED_BASELINE" bash "$REPORT"

  [ "$status" -eq 0 ]
  [[ "$output" == *"已知失败"* ]]
  [[ "$output" == *"新增失败: 0"* ]]
}

@test "report: unlisted failures are reported and fail the gate" {
  printf '%s\n' 'known failure # existing reason' > "$ISOLATED_BASELINE"
  write_fake_bats $'not ok 1 known failure\nnot ok 2 newly introduced failure'

  run env PATH="$TEST_BIN:$PATH" RDDF_BATS_COLLECT_ACTIVE=0 RDDF_KNOWN_FAILURES_FILE="$ISOLATED_BASELINE" bash "$REPORT"

  [ "$status" -ne 0 ]
  [[ "$output" == *"newly introduced failure"* ]]
  [[ "$output" == *"新增失败"* ]]
}

@test "report: no failed TAP cases returns zero" {
  : > "$ISOLATED_BASELINE"
  write_fake_bats '1..0' 0

  run env PATH="$TEST_BIN:$PATH" RDDF_BATS_COLLECT_ACTIVE=0 RDDF_KNOWN_FAILURES_FILE="$ISOLATED_BASELINE" bash "$REPORT"

  [ "$status" -eq 0 ]
  [[ "$output" == *"0"* ]]
}

@test "refresh: preserves comments for unchanged failures" {
  printf '%s\n' 'known failure # preserve this reason' > "$ISOLATED_BASELINE"
  write_fake_bats $'not ok 1 known failure\nnot ok 2 newly observed failure'

  run env PATH="$TEST_BIN:$PATH" RDDF_KNOWN_FAILURES_FILE="$ISOLATED_BASELINE" bash "$REFRESH"

  [ "$status" -eq 0 ]
  grep -Fq 'known failure # preserve this reason' "$ISOLATED_BASELINE"
  grep -Fq 'newly observed failure' "$ISOLATED_BASELINE"
}

@test "refresh: output is normalized for report comparison" {
  printf '%s\n' 'known failure # reason' > "$ISOLATED_BASELINE"
  write_fake_bats $'not ok 2 known failure\nnot ok 1 another failure'

  run env PATH="$TEST_BIN:$PATH" RDDF_KNOWN_FAILURES_FILE="$ISOLATED_BASELINE" bash "$REFRESH"

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

@test "repro: temp-baseline content is what the report reads, repo file untouched" {
  # Deterministic reproduction of the 2026-11-17 data-loss incident.
  #
  # Incident: test_known_failures_baseline.bats and
  # test_execute_regression_gate.bats (该测试已于 2026-11-20 随 execute 技能归档而删除)
  # wrote the REAL baseline directly, relying on teardown() to restore it.
  # collect_bats_failures.sh kills a file at 30s; both files run a full
  # integration collection internally, so they blew the timeout, teardown never
  # ran, and the real baseline was left holding one fixture line. Every run
  # destroyed its own baseline => 已知失败: 0 / 新增失败: 11.
  #
  # This test pins the fix: the temp baseline holds an entry that the repo
  # baseline does NOT, so
  #   - if the report read the repo baseline  => 新增失败: 1
  #   - if it read the temp baseline          => 新增失败: 0  (and 已知失败: 1)
  # and the repo baseline must be byte-identical afterwards.
  printf '%s\n' 'known failure: temp-only entry # temp' > "$ISOLATED_BASELINE"
  write_fake_bats 'not ok 1 known failure: temp-only entry'

  run env PATH="$TEST_BIN:$PATH" RDDF_BATS_COLLECT_ACTIVE=0 RDDF_KNOWN_FAILURES_FILE="$ISOLATED_BASELINE" bash "$REPORT"

  [ "$status" -eq 0 ]
  [[ "$output" == *"已知失败: 1"* ]]
  [[ "$output" == *"新增失败: 0"* ]]
  cmp -s "$REPO_BASELINE_SNAPSHOT" "$BASELINE"
}

@test "repro: fixture written to a temp baseline never reaches the repo file" {
  # The exact byte sequence that corrupted the real baseline.
  local fixture='known failure: environment dependency # existing reason'
  printf '%s\n' "$fixture" > "$ISOLATED_BASELINE"
  write_fake_bats 'not ok 1 known failure: environment dependency'

  run env PATH="$TEST_BIN:$PATH" RDDF_BATS_COLLECT_ACTIVE=0 RDDF_KNOWN_FAILURES_FILE="$ISOLATED_BASELINE" bash "$REPORT"

  [ "$status" -eq 0 ]
  # Repo baseline unchanged byte-for-byte, and still carries no fixture line.
  cmp -s "$REPO_BASELINE_SNAPSHOT" "$BASELINE"
  ! grep -qF "$fixture" "$BASELINE"
}

@test "guard: repo baseline carries no in-flight test fixture entries" {
  # Minimal shrink guard (per fix-regression-baseline-integrity AC).
  # The 2026-11-17 incident left tests/KNOWN_FAILURES.txt holding exactly one
  # line: `known failure: environment dependency # existing reason` — a fixture
  # written by an in-flight test whose teardown never ran (30s per-file
  # timeout). That state is indistinguishable from "one known failure here",
  # so the gate reported 已知失败 0 / 新增失败 11 with no signal about the cause.
  #
  # The judgement is shape-based, not count-based: a real bats test name never
  # begins with `known failure` (real entries look like
  # `AGENTS.md: <case name> # <reason>`), so any such line is leaked fixture.
  [ -n "$BASELINE" ] && [ -f "$BASELINE" ] || {
    echo "guard cannot judge: BASELINE='$BASELINE'" >&2
    return 1
  }
  local leaked
  leaked=$(grep -E '^known failure' "$BASELINE" || true)
  if [ -n "$leaked" ]; then
    echo "in-flight test fixture leaked into the repo baseline:" >&2
    printf '%s\n' "$leaked" >&2
    return 1
  fi
}
