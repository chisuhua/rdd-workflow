#!/usr/bin/env bats
# tests/integration/test_rddf_session_sub_phase.bats

load ../test_helper

setup() {
    TEST_DIR=$(mktemp -d)
    export PROJECT_ROOT="$TEST_DIR"
    mkdir -p "$TEST_DIR/.rddf/state"
    export OPENCODE_SESSION_ID="test-sp-$(date +%s%N)"
}

teardown() {
    rm -rf "$TEST_DIR"
}

@test "sub-phase: heartbeat records RDDF_SUB_PHASE" {
    SESSIONS_FILE="$TEST_DIR/.rddf/state/sessions.json"
    echo '{"version": 2, "sessions": []}' > "$SESSIONS_FILE"

    run bash -c "
        export PROJECT_ROOT='$TEST_DIR'
        export OPENCODE_SESSION_ID='$OPENCODE_SESSION_ID'
        export RDDF_SUB_PHASE='phase_3_archive_demo'
        source '$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh'
        rddf_session_hook_heartbeat stage_ship demo
    "

    [ "$status" -eq 0 ]

    sub_phase=$(python3 -c "
import json
with open('$SESSIONS_FILE') as f:
    data = json.load(f)
s = data['sessions'][0]
print(s.get('sub_phase', ''))
")
    [ "$sub_phase" = "phase_3_archive_demo" ] || {
        echo "FAIL: Expected 'phase_3_archive_demo', got '$sub_phase'"
        return 1
    }
}

@test "sub-phase: heartbeat without env var leaves sub_phase empty" {
    SESSIONS_FILE="$TEST_DIR/.rddf/state/sessions.json"
    echo '{"version": 2, "sessions": []}' > "$SESSIONS_FILE"

    run bash -c "
        export PROJECT_ROOT='$TEST_DIR'
        export OPENCODE_SESSION_ID='$OPENCODE_SESSION_ID'
        unset RDDF_SUB_PHASE
        source '$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh'
        rddf_session_hook_heartbeat stage_ship demo
    "

    [ "$status" -eq 0 ]

    sub_phase=$(python3 -c "
import json
with open('$SESSIONS_FILE') as f:
    data = json.load(f)
s = data['sessions'][0]
print(s.get('sub_phase', 'NOT_SET'))
")
    [ "$sub_phase" = "NOT_SET" ] || [ -z "$sub_phase" ]
}