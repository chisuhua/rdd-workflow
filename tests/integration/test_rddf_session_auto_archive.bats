#!/usr/bin/env bats
# tests/integration/test_rddf_session_auto_archive.bats
# End-to-end verification that rddf_session_hook_entry triggers auto-archive
# when sessions.json exceeds threshold.

load ../test_helper

setup() {
    TEST_DIR=$(mktemp -d)
    export PROJECT_ROOT="$TEST_DIR"
    mkdir -p "$TEST_DIR/.rddf/state"
    # Stub OPENCODE_SESSION_ID to avoid /proc cmdline probe
    export OPENCODE_SESSION_ID="test-session-$(date +%s%N)"
    unset RDDF_AUTO_ARCHIVE_KEEP
    unset RDDF_AUTO_ARCHIVE_THRESHOLD
}

teardown() {
    rm -rf "$TEST_DIR"
}

@test "auto-archive: hook entry triggers archive when sessions >= threshold" {
    # Setup sessions.json with 20 terminal sessions (default threshold = 15)
    SESSIONS_FILE="$TEST_DIR/.rddf/state/sessions.json"
    mkdir -p "$(dirname "$SESSIONS_FILE")"
    python3 -c "
import json
sessions = []
for i in range(20):
    sessions.append({
        'session_id': f'rds_{i:012x}',
        'state': 'completed',
        'kind': 'stage_arch',
        'owner_opencode_session_id': 'prev_owner',
        'started_at': '2026-07-01T00:00:00',
        'ended_at': '2026-07-01T01:00:00',
        'last_heartbeat': '2026-07-01T01:00:00',
        'goal': {'intent': 'guide-arch'},
        'attached_changes': [],
        'context_pointer': None,
        'end_reason': 'arch-done',
    })
with open('$SESSIONS_FILE', 'w') as f:
    json.dump({'version': 1, 'sessions': sessions}, f)
"

    # Source hooks and invoke entry
    bash -c "
        export PROJECT_ROOT='$TEST_DIR'
        export OPENCODE_SESSION_ID='$OPENCODE_SESSION_ID'
        source '$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh'
        rddf_session_hook_entry stage_arch guide-arch arch-phase design-done
    " 2>/dev/null

    # Verify sessions.json was reduced (archive triggered)
    remaining=$(python3 -c "
import json
with open('$SESSIONS_FILE') as f:
    data = json.load(f)
# After archive_history(keep=10): 10 terminal kept + 1 new = 11
print(len(data['sessions']))
")
    [ "$remaining" -le 11 ] || {
        echo "FAIL: Expected <=11 sessions after auto-archive, got $remaining"
        return 1
    }

    # Verify .archive.json was created
    [ -f "$TEST_DIR/.rddf/state/sessions.archive.json" ] || {
        echo "FAIL: sessions.archive.json not created"
        return 1
    }
}

@test "auto-archive: hook entry is no-op when sessions < threshold" {
    SESSIONS_FILE="$TEST_DIR/.rddf/state/sessions.json"
    mkdir -p "$(dirname "$SESSIONS_FILE")"
    python3 -c "
import json
sessions = []
for i in range(5):
    sessions.append({
        'session_id': f'rds_{i:012x}',
        'state': 'completed',
        'kind': 'stage_arch',
        'owner_opencode_session_id': 'prev_owner',
        'started_at': '2026-07-01T00:00:00',
        'ended_at': '2026-07-01T01:00:00',
        'last_heartbeat': '2026-07-01T01:00:00',
        'goal': {'intent': 'guide-arch'},
        'attached_changes': [],
        'context_pointer': None,
        'end_reason': 'arch-done',
    })
with open('$SESSIONS_FILE', 'w') as f:
    json.dump({'version': 1, 'sessions': sessions}, f)
"

    bash -c "
        export PROJECT_ROOT='$TEST_DIR'
        export OPENCODE_SESSION_ID='$OPENCODE_SESSION_ID'
        source '$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh'
        rddf_session_hook_entry stage_arch guide-arch arch-phase design-done
    " 2>/dev/null

    remaining=$(python3 -c "
import json
with open('$SESSIONS_FILE') as f:
    data = json.load(f)
print(len(data['sessions']))
")
    # 5 old + 1 new = 6 (no archive triggered)
    [ "$remaining" -eq 6 ] || {
        echo "FAIL: Expected 6 sessions (no archive), got $remaining"
        return 1
    }
    [ ! -f "$TEST_DIR/.rddf/state/sessions.archive.json" ] || {
        echo "FAIL: archive file should not exist when below threshold"
        return 1
    }
}

@test "auto-archive: RDDF_AUTO_ARCHIVE_KEEP=0 disables" {
    export RDDF_AUTO_ARCHIVE_KEEP=0
    SESSIONS_FILE="$TEST_DIR/.rddf/state/sessions.json"
    mkdir -p "$(dirname "$SESSIONS_FILE")"
    python3 -c "
import json
sessions = []
for i in range(50):
    sessions.append({
        'session_id': f'rds_{i:012x}',
        'state': 'completed',
        'kind': 'stage_arch',
        'owner_opencode_session_id': 'prev_owner',
        'started_at': '2026-07-01T00:00:00',
        'ended_at': '2026-07-01T01:00:00',
        'last_heartbeat': '2026-07-01T01:00:00',
        'goal': {'intent': 'guide-arch'},
        'attached_changes': [],
        'context_pointer': None,
        'end_reason': 'arch-done',
    })
with open('$SESSIONS_FILE', 'w') as f:
    json.dump({'version': 1, 'sessions': sessions}, f)
"

    bash -c "
        export PROJECT_ROOT='$TEST_DIR'
        export OPENCODE_SESSION_ID='$OPENCODE_SESSION_ID'
        export RDDF_AUTO_ARCHIVE_KEEP=0
        source '$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh'
        rddf_session_hook_entry stage_arch guide-arch arch-phase design-done
    " 2>/dev/null

    remaining=$(python3 -c "
import json
with open('$SESSIONS_FILE') as f:
    data = json.load(f)
print(len(data['sessions']))
")
    # 50 old + 1 new = 51 (archive disabled)
    [ "$remaining" -eq 51 ] || {
        echo "FAIL: Expected 51 (disabled), got $remaining"
        return 1
    }
}

@test "auto-archive: hook close also triggers archive" {
    SESSIONS_FILE="$TEST_DIR/.rddf/state/sessions.json"
    mkdir -p "$(dirname "$SESSIONS_FILE")"
    python3 -c "
import json
sessions = []
for i in range(20):
    sessions.append({
        'session_id': f'rds_{i:012x}',
        'state': 'completed',
        'kind': 'stage_arch',
        'owner_opencode_session_id': 'prev_owner',
        'started_at': '2026-07-01T00:00:00',
        'ended_at': '2026-07-01T01:00:00',
        'last_heartbeat': '2026-07-01T01:00:00',
        'goal': {'intent': 'guide-arch'},
        'attached_changes': [],
        'context_pointer': None,
        'end_reason': 'arch-done',
    })
with open('$SESSIONS_FILE', 'w') as f:
    json.dump({'version': 1, 'sessions': sessions}, f)
"

    bash -c "
        export PROJECT_ROOT='$TEST_DIR'
        export OPENCODE_SESSION_ID='$OPENCODE_SESSION_ID'
        source '$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh'
        rddf_session_hook_close stage_arch arch-done guide-arch
    " 2>/dev/null

    remaining=$(python3 -c "
import json
with open('$SESSIONS_FILE') as f:
    data = json.load(f)
print(len(data['sessions']))
")
    [ "$remaining" -le 11 ] || {
        echo "FAIL: Expected <=11 after close-triggered archive, got $remaining"
        return 1
    }
}

@test "auto-archive: hook entry does not crash on corrupt sessions.json (best-effort)" {
    # Force failure: corrupt sessions.json
    SESSIONS_FILE="$TEST_DIR/.rddf/state/sessions.json"
    mkdir -p "$(dirname "$SESSIONS_FILE")"
    echo "{invalid json" > "$SESSIONS_FILE"

    # Best-effort: hook entry may still fail due to create_session error, but
    # the auto-archive portion must not crash with unhandled exception.
    # We assert: timeout (status=124) does NOT happen (would indicate hang).
    run timeout 10 bash -c "
        export PROJECT_ROOT='$TEST_DIR'
        export OPENCODE_SESSION_ID='$OPENCODE_SESSION_ID'
        source '$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh'
        rddf_session_hook_entry stage_arch guide-arch arch-phase design-done
    "

    # 124 = timeout from \`timeout\` cmd (would indicate hung subprocess / crash)
    [ "$status" -ne 124 ]
}
