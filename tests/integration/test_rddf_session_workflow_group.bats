#!/usr/bin/env bats
# tests/integration/test_rddf_session_workflow_group.bats

load ../test_helper

setup() {
    TEST_DIR=$(mktemp -d)
    export PROJECT_ROOT="$TEST_DIR"
    mkdir -p "$TEST_DIR/.rddf/state"
    export OPENCODE_SESSION_ID="test-wg-$(date +%s%N)"
}

teardown() {
    rm -rf "$TEST_DIR"
}

@test "workflow-group: explicit env var recorded on entry" {
    SESSIONS_FILE="$TEST_DIR/.rddf/state/sessions.json"
    echo '{"version": 2, "sessions": []}' > "$SESSIONS_FILE"

    bash -c "
        export PROJECT_ROOT='$TEST_DIR'
        export OPENCODE_SESSION_ID='owner-a'
        export RDDF_WORKFLOW_GROUP='batch-2026-08-02'
        source '$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh'
        rddf_session_hook_entry stage_ship guide-ship ship-phase archive-all
    " 2>/dev/null

    wg=$(python3 -c "
import json
with open('$SESSIONS_FILE') as f:
    data = json.load(f)
print(data['sessions'][0].get('workflow_group', ''))
")
    [ "$wg" = "batch-2026-08-02" ] || {
        echo "FAIL: Expected workflow_group='batch-2026-08-02', got '$wg'"
        return 1
    }
}

@test "workflow-group: two sessions share workflow_group when RDDF_ALLOW_CROSS_STAGE_PARALLEL=yes" {
    SESSIONS_FILE="$TEST_DIR/.rddf/state/sessions.json"
    echo '{"version": 2, "sessions": []}' > "$SESSIONS_FILE"

    bash -c "
        export PROJECT_ROOT='$TEST_DIR'
        export OPENCODE_SESSION_ID='owner-a'
        export RDDF_WORKFLOW_GROUP='batch-2026-08-02'
        export RDDF_ALLOW_CROSS_STAGE_PARALLEL=yes
        source '$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh'
        rddf_session_hook_entry stage_ship guide-ship ship-phase archive-all
    " 2>/dev/null

    bash -c "
        export PROJECT_ROOT='$TEST_DIR'
        export OPENCODE_SESSION_ID='owner-b'
        export RDDF_WORKFLOW_GROUP='batch-2026-08-02'
        export RDDF_ALLOW_CROSS_STAGE_PARALLEL=yes
        source '$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh'
        rddf_session_hook_entry stage_plan guide-plan plan-phase plan-done
    " 2>/dev/null

    count=$(python3 -c "
import json
with open('$SESSIONS_FILE') as f:
    data = json.load(f)
matching = [s for s in data['sessions'] if s.get('workflow_group') == 'batch-2026-08-02']
print(len(matching))
")
    [ "$count" -eq 2 ] || {
        echo "FAIL: Expected 2 sessions with workflow_group='batch-2026-08-02', got $count"
        return 1
    }
}

@test "workflow-group: auto-generates UUID when env var unset" {
    SESSIONS_FILE="$TEST_DIR/.rddf/state/sessions.json"
    echo '{"version": 2, "sessions": []}' > "$SESSIONS_FILE"

    bash -c "
        export PROJECT_ROOT='$TEST_DIR'
        export OPENCODE_SESSION_ID='$OPENCODE_SESSION_ID'
        unset RDDF_WORKFLOW_GROUP
        source '$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh'
        rddf_session_hook_entry stage_ship guide-ship ship-phase archive-all
    " 2>/dev/null

    wg=$(python3 -c "
import json
with open('$SESSIONS_FILE') as f:
    data = json.load(f)
print(data['sessions'][0].get('workflow_group', ''))
")
    if [[ ! "$wg" =~ ^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[a-f0-9]{4}-[a-f0-9]{12}$ ]]; then
        echo "FAIL: Expected UUID v4, got '$wg'"
        return 1
    fi
}