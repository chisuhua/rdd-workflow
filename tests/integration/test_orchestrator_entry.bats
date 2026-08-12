#!/usr/bin/env bats
# tests/integration/test_orchestrator_entry.bats
# Tests for skills/_lib/orchestrator_entry.sh bash wrapper.

setup() {
    load ../test_helper
    TRACE_DIR="$(mktemp -d)"
    export RDDF_TRACE_DIR="$TRACE_DIR"
    export RDDF_PHASE="guide-test"
    export RDDF_PROJECT_ROOT="$BATS_TMPDIR"
}

teardown() {
    rm -rf "$TRACE_DIR"
}

@test "orchestrator_entry.sh: source-able" {
    source "${PROJECT_ROOT}/skills/_lib/orchestrator_entry.sh"
    [ $? -eq 0 ]
}

@test "orchestrator_entry.sh: orchestrator_run records to trace" {
    source "${PROJECT_ROOT}/skills/_lib/orchestrator_entry.sh"
    orchestrator_run echo hello
    [ $? -eq 0 ]
    local traces
    traces=$(ls "$TRACE_DIR"/*.jsonl 2>/dev/null | wc -l)
    [ "$traces" -ge 1 ]
}

@test "orchestrator_entry.sh: orchestrator_finalize appends finalize event" {
    source "${PROJECT_ROOT}/skills/_lib/orchestrator_entry.sh"
    orchestrator_run echo hello
    orchestrator_finalize
    local last_line
    last_line=$(tail -n 1 "$TRACE_DIR"/*.jsonl)
    echo "$last_line" | grep -qE '"type": ?"finalize"'
}

@test "orchestrator_entry.sh: orchestrator_mark inserts checkpoint" {
    source "${PROJECT_ROOT}/skills/_lib/orchestrator_entry.sh"
    orchestrator_run echo hello
    orchestrator_mark "after-setup" "phase_started"
    local has_checkpoint
    has_checkpoint=$(grep -c '"type":"checkpoint"' "$TRACE_DIR"/*.jsonl)
    [ "$has_checkpoint" -ge 1 ]
}