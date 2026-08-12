#!/usr/bin/env bats
# tests/integration/test_env_var_toggle.bats
# Verifies that RDDF_USE_ORCHESTRATOR=yes toggles behavior end-to-end.

setup() {
    load ../test_helper
    TRACE_DIR="$(mktemp -d)"
    export RDDF_TRACE_DIR="$TRACE_DIR"
    unset RDDF_USE_ORCHESTRATOR
}

teardown() {
    rm -rf "$TRACE_DIR"
}

@test "env toggle: unset → trap path active, no orchestrator trace" {
    unset RDDF_USE_ORCHESTRATOR
    rm -f "$TRACE_DIR"/*.jsonl 2>/dev/null
    bash -c "
        source '${PROJECT_ROOT}/skills/_lib/post_flow_wrap.sh'
        source '${PROJECT_ROOT}/skills/_lib/orchestrator_entry.sh'
        trap 'post_flow_on_err' ERR
        ( exit 1 ) || true
    " 2>/dev/null
    ! ls "$TRACE_DIR"/*.jsonl 2>/dev/null
}

@test "env toggle: yes → orchestrator trace exists, finalize event present" {
    export RDDF_USE_ORCHESTRATOR=yes
    export RDDF_PHASE="guide-test"
    bash -c "
        source '${PROJECT_ROOT}/skills/_lib/orchestrator_entry.sh'
        orchestrator_run echo hello
        orchestrator_finalize
    " 2>/dev/null
    ls "$TRACE_DIR"/*.jsonl 2>/dev/null
    last_line=$(tail -n 1 "$TRACE_DIR"/*.jsonl)
    echo "$last_line" | grep -qE '"type": ?"finalize"'
}