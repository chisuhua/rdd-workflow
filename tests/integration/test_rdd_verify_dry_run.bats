#!/usr/bin/env bats
# tests/integration/test_rdd_verify_dry_run.bats
#
# `--dry-run` must have NO side effects. The legacy-state migration used to run
# unconditionally (before the dry-run branch), so a dry-run really moved files.

load ../test_helper

setup() {
    TEST_TMP=$(mktemp -d)
    mkdir -p "$TEST_TMP/.rddf/state"
    printf '{"schema_version":2,"change":"probe","verdict":[]}\n' \
        > "$TEST_TMP/.rddf/state/.ac-verdict-probe.json"
}

teardown() {
    rm -rf "$TEST_TMP"
}

@test "rdd-verify --dry-run does not move legacy state files" {
    BEFORE=$(find "$TEST_TMP/.rddf/state" -type f | sort)
    run env RDDF_PROJECT_ROOT="$TEST_TMP" python3 "$REPO_ROOT/_lib/cli/rdd_verify_cmd.py" --dry-run
    AFTER=$(find "$TEST_TMP/.rddf/state" -type f | sort)
    [ "$BEFORE" = "$AFTER" ]
    [ -f "$TEST_TMP/.rddf/state/.ac-verdict-probe.json" ]
    [ ! -d "$TEST_TMP/.rddf/state/verifier" ]
}

@test "rdd-verify --dry-run still reports what it would migrate" {
    run env RDDF_PROJECT_ROOT="$TEST_TMP" python3 "$REPO_ROOT/_lib/cli/rdd_verify_cmd.py" --dry-run
    [[ "$output" == *"would migrate"* ]]
    [[ "$output" == *".ac-verdict-probe.json"* ]]
}

@test "rdd-verify --dry-run --stage is rejected (mutually exclusive)" {
    run env RDDF_PROJECT_ROOT="$TEST_TMP" python3 "$REPO_ROOT/_lib/cli/rdd_verify_cmd.py" --dry-run --stage probe
    [ "$status" -eq 2 ]
    [[ "$output" == *"mutually exclusive"* ]]
}

@test "rdd-verify --stage (non dry-run) still migrates legacy state and stages" {
    mkdir -p "$TEST_TMP/openspec/changes/probe"
    printf '# demo\n\n## Acceptance\n\n- [ ] a\n' > "$TEST_TMP/openspec/changes/probe/proposal.md"
    run env RDDF_PROJECT_ROOT="$TEST_TMP" python3 "$REPO_ROOT/_lib/cli/rdd_verify_cmd.py" --stage probe
    [ "$status" -eq 0 ]
    [ -f "$TEST_TMP/.rddf/state/verifier/.ac-verdict-probe.json" ]
    [ -f "$TEST_TMP/.rddf/state/verifier/rdd-verify-context-probe.json" ]
}
