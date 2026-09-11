#!/usr/bin/env bats
#
# Integration tests for bypass-audit mechanism (per improvement #bypass-audit-mechanism).
#
# Verifies:
# - audit_bypass_log CLI integration
# - rdd-doctor --category bypass-audit aggregation
# - Threshold WARNING vs CRITICAL escalation

load ../test_helper

setup() {
    TEST_TMP=$(mktemp -d)
    mkdir -p "$TEST_TMP/.rddf/state"
}

teardown() {
    rm -rf "$TEST_TMP"
}

@test "bypass-audit: --category runs without error on empty audit file" {
    RDDF_PROJECT_ROOT="$TEST_TMP" \
        run bash "$REPO_ROOT/skills/rdd-doctor/scripts/doctor.sh" --category bypass-audit --quiet
    [ "$status" -eq 0 ]
    [[ "$output" == *"OK"* ]] || [[ "$output" == *"✅"* ]]
}

@test "bypass-audit: emits WARNING when ARCHIVE_ON_MAIN count > 3 but <= 6" {
    for i in $(seq 1 6); do
        RDDF_PROJECT_ROOT="$TEST_TMP" bash -c "source '$REPO_ROOT/_lib/bypass_audit.sh' && audit_bypass_log ARCHIVE_ON_MAIN 'reason $i' test-change archive" >/dev/null 2>&1
    done

    RDDF_PROJECT_ROOT="$TEST_TMP" \
        run bash "$REPO_ROOT/skills/rdd-doctor/scripts/doctor.sh" --category bypass-audit
    [ "$status" -eq 1 ]  # WARNING → exit 1
    [[ "$output" == *"WARNING"* ]]
    [[ "$output" == *"ARCHIVE_ON_MAIN"* ]]
    [[ "$output" == *"limit=3"* ]]
}

@test "bypass-audit: emits CRITICAL when count > 2x threshold" {
    for i in $(seq 1 11); do
        RDDF_PROJECT_ROOT="$TEST_TMP" bash -c "source '$REPO_ROOT/_lib/bypass_audit.sh' && audit_bypass_log ARCHIVE_ON_MAIN 'reason $i' test-change" >/dev/null 2>&1
    done

    RDDF_PROJECT_ROOT="$TEST_TMP" \
        run bash "$REPO_ROOT/skills/rdd-doctor/scripts/doctor.sh" --category bypass-audit
    [ "$status" -eq 2 ]  # CRITICAL → exit 2
    [[ "$output" == *"CRITICAL"* ]]
}

@test "bypass-audit: --category bypass-audit is listed in --help" {
    run bash "$REPO_ROOT/skills/rdd-doctor/scripts/doctor.sh" --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"bypass-audit"* ]]
}

@test "bypass-audit: audit_bypass_log creates .rddf/state/.bypass-audit.jsonl" {
    RDDF_PROJECT_ROOT="$TEST_TMP" \
        bash -c "source '$REPO_ROOT/_lib/bypass_audit.sh' && audit_bypass_log TEST_VAR 'test reason' my-change test-scope"
    [ -f "$TEST_TMP/.rddf/state/.bypass-audit.jsonl" ]
    line_count=$(wc -l < "$TEST_TMP/.rddf/state/.bypass-audit.jsonl")
    [ "$line_count" -eq 1 ]
}

@test "bypass-audit: appends (not overwrites) on multiple invocations" {
    RDDF_PROJECT_ROOT="$TEST_TMP"
    export RDDF_PROJECT_ROOT
    for i in $(seq 1 5); do
        bash -c "source '$REPO_ROOT/_lib/bypass_audit.sh' && audit_bypass_log VAR$i 'reason $i'" >/dev/null 2>&1
    done
    unset RDDF_PROJECT_ROOT

    line_count=$(wc -l < "$TEST_TMP/.rddf/state/.bypass-audit.jsonl")
    [ "$line_count" -eq 5 ]
}

@test "bypass-audit: records required fields (ts, env_var, reason, change, scope, actor, codebase_commit)" {
    RDDF_PROJECT_ROOT="$TEST_TMP" \
        bash -c "source '$REPO_ROOT/_lib/bypass_audit.sh' && audit_bypass_log MY_VAR 'reason text' my-change my-scope"
    line=$(cat "$TEST_TMP/.rddf/state/.bypass-audit.jsonl")
    [[ "$line" == *'"env_var": "MY_VAR"'* ]]
    [[ "$line" == *'"reason": "reason text"'* ]]
    [[ "$line" == *'"change": "my-change"'* ]]
    [[ "$line" == *'"scope": "my-scope"'* ]]
    [[ "$line" == *'"ts":'* ]]
    [[ "$line" == *'"actor":'* ]]
    [[ "$line" == *'"codebase_commit":'* ]]
}