#!/usr/bin/env bats
# tests/integration/test_fix_scan_state_binding.bats
# Regression for scan-state.sh line 231-233 syntax bug, heartbeat helper flow,
# and owner-based session binding output.

load ../test_helper

setup() {
    cd "$BATS_TEST_TMPDIR"
    rm -rf repo 2>/dev/null
    mkdir repo && cd repo
    git init -q
    git config user.email "t@t.t"
    git config user.name "t"
    mkdir -p .rddf/state
}

_write_sessions() {
    cat > .rddf/state/sessions.json <<JSON
{
  "version": 1,
  "sessions": [
    {
      "session_id": "rds_abc123",
      "kind": "stage_plan",
      "owner_opencode_session_id": "omo_ses_owner_001",
      "state": "active",
      "goal": {"intent": "plan", "subject": "dashboard"},
      "attached_changes": ["fix-scan-state-binding"],
      "started_at": "2026-07-21T12:00:00+00:00",
      "last_heartbeat": "2026-07-21T12:00:00+00:00"
    }
  ]
}
JSON
}

@test "scan_session_binding: returns current binding when owner matches" {
    _write_sessions

    run bash -c "
        export OPENCODE_SESSION_ID='omo_ses_owner_001'
        source '$REPO_ROOT/skills/guide/scripts/scan-state.sh'
        scan_session_binding '$PWD'
        printf '%s\n' \"\${BINDING_LINES[@]}\"
    "

    [ "$status" -eq 0 ]
    [[ "$output" == *"Current:"* ]]
    [[ "$output" == *"rds_abc123"* ]]
}

@test "scan_session_binding: reports no binding when owner does not match" {
    _write_sessions

    run bash -c "
        unset OPENCODE_SESSION_ID
        source '$REPO_ROOT/skills/guide/scripts/scan-state.sh'
        scan_session_binding '$PWD'
        printf '%s\n' \"\${BINDING_LINES[@]}\"
    "

    [ "$status" -eq 0 ]
    [[ "$output" == *"No current binding"* ]]
}

@test "scan_session_binding: owner variable is single line without OPENCODE_SESSION_ID" {
    _write_sessions

    run bash -c "
        unset OPENCODE_SESSION_ID
        source '$REPO_ROOT/skills/guide/scripts/scan-state.sh'
        scan_session_binding '$PWD'
        [[ ! \"\${BINDING_LINES[*]}\" =~ check_stale_workflow_state ]]
    "

    [ "$status" -eq 0 ]
}

@test "scan_session_binding: no binding lines when sessions.json is missing" {
    run bash -c "
        export OPENCODE_SESSION_ID='omo_ses_owner_001'
        source '$REPO_ROOT/skills/guide/scripts/scan-state.sh'
        scan_session_binding '$PWD'
        echo \"count:\" \${#BINDING_LINES[@]}
    "

    [ "$status" -eq 0 ]
    [[ "$output" == *"count: 0"* ]]
}
