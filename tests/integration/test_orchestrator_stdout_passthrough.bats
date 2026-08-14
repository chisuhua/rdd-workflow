#!/usr/bin/env bats
# Integration tests for orchestrator stdout passthrough (tee mode).
# Per openspec/changes/preserve-orchestrator-command-stdout.

setup() {
    REPO_ROOT="$(cd "${BATS_TEST_DIRNAME}/../.." && pwd)"
    WORK="$(mktemp -d)"
    export RDDF_TRACE_DIR="$WORK/.rddf/state/trace"
    export RDDF_PHASE="int-tee"
    mkdir -p "$RDDF_TRACE_DIR"
}

teardown() {
    rm -rf "$WORK"
    unset RDDF_TRACE_DIR RDDF_PHASE
}

@test "T1: tee mode 100KB output does not block subprocess" {
    RDDF_ORCHESTRATOR_CAPTURE=tee bash -c '
        source "$1/skills/_lib/orchestrator_entry.sh" 2>/dev/null
        orchestrator_run bash -c "
            for i in $(seq 1000); do echo \"line \$i\"; done
        "
        orchestrator_finalize
    ' _ "$REPO_ROOT"
    trace_files=$(ls "$RDDF_TRACE_DIR"/*.jsonl 2>/dev/null | wc -l)
    [ "$trace_files" -ge 1 ]
}

@test "T2: passthrough mode produces no trace file" {
    RDDF_ORCHESTRATOR_CAPTURE=passthrough bash -c '
        source "$1/skills/_lib/orchestrator_entry.sh" 2>/dev/null
        orchestrator_run bash -c "echo hi"
        orchestrator_finalize
    ' _ "$REPO_ROOT"
    count=$(ls "$RDDF_TRACE_DIR"/*.jsonl 2>/dev/null | wc -l)
    [ "$count" -eq 0 ]
}

@test "T3: capture mode preserves stdout_tail in trace" {
    RDDF_ORCHESTRATOR_CAPTURE=capture bash -c '
        source "$1/skills/_lib/orchestrator_entry.sh" 2>/dev/null
        orchestrator_run bash -c "echo preserved-capture-line"
        orchestrator_finalize
    ' _ "$REPO_ROOT"
    trace=$(ls "$RDDF_TRACE_DIR"/*.jsonl 2>/dev/null | head -1)
    [ -n "$trace" ]
    grep -q "preserved-capture-line" "$trace"
}

@test "T4: stdout_capture_mode field present in subprocess event" {
    RDDF_ORCHESTRATOR_CAPTURE=tee bash -c '
        source "$1/skills/_lib/orchestrator_entry.sh" 2>/dev/null
        orchestrator_run bash -c "echo mode-check"
        orchestrator_finalize
    ' _ "$REPO_ROOT"
    trace=$(ls "$RDDF_TRACE_DIR"/*.jsonl 2>/dev/null | head -1)
    [ -n "$trace" ]
    grep -q '"stdout_capture_mode":"tee"' "$trace"
}

@test "T5: capture mode marks stdout_capture_mode=capture" {
    RDDF_ORCHESTRATOR_CAPTURE=capture bash -c '
        source "$1/skills/_lib/orchestrator_entry.sh" 2>/dev/null
        orchestrator_run bash -c "echo capture-mode-test"
        orchestrator_finalize
    ' _ "$REPO_ROOT"
    trace=$(ls "$RDDF_TRACE_DIR"/*.jsonl 2>/dev/null | head -1)
    [ -n "$trace" ]
    grep -q '"stdout_capture_mode":"capture"' "$trace"
}