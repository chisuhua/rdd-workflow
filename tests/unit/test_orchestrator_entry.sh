#!/usr/bin/env bats
# Spec 2026-08-13 §3 / C2: orchestrate_phase aggregate helper.

setup() {
    ENTRY="${BATS_TEST_DIRNAME}/../../skills/_lib/orchestrator_entry.sh"
    TEST_TRACE_DIR="$(mktemp -d)"
    export RDDF_TRACE_DIR="$TEST_TRACE_DIR"
    export RDDF_PHASE="int-test"
    # shellcheck disable=SC1090
    source "$ENTRY" 2>/dev/null
}

teardown() {
    rm -rf "$TEST_TRACE_DIR"
    unset RDDF_TRACE_DIR RDDF_PHASE
}

@test "C2: orchestrate_phase function is defined" {
    declare -F orchestrate_phase >/dev/null
}

@test "C2: orchestrate_phase propagates exit code on failure" {
    run orchestrate_phase int-test bash -c 'exit 7'
    [ "$status" -eq 7 ]
}

@test "C2: orchestrate_phase emits finalize event on success" {
    orchestrate_phase int-test true
    trace_file=$(ls "$TEST_TRACE_DIR"/int-test-*.jsonl 2>/dev/null | head -1)
    [ -n "$trace_file" ]
    last_event=$(tail -1 "$trace_file")
    [[ "$last_event" == *'"finalize"'* ]]
}
