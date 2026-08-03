#!/usr/bin/env bats
# tests/integration/test_rddf_session_status.bats
# Verify rddf-session status subcommand outputs table + binding + counts.

load ../test_helper

setup() {
    TEST_DIR=$(mktemp -d)
    export PROJECT_ROOT="$TEST_DIR"
    mkdir -p "$TEST_DIR/.rddf/state"
    export OPENCODE_SESSION_ID="test-status-$(date +%s%N)"
}

teardown() {
    rm -rf "$TEST_DIR"
}

@test "rddf-session status: outputs table header" {
    SESSIONS_FILE="$TEST_DIR/.rddf/state/sessions.json"
    python3 -c "
import json
data = {
    'version': 1,
    'sessions': [
        {
            'session_id': 'rds_a1b2c3d4e5f6',
            'kind': 'stage_ship',
            'state': 'active',
            'owner_opencode_session_id': '$OPENCODE_SESSION_ID',
            'parent_session_id': None,
            'started_at': '2026-08-02T15:00:00+00:00',
            'last_heartbeat': '2026-08-02T15:30:00+00:00',
            'attached_changes': ['add-foo'],
            'goal': {'intent': 'guide-ship'},
        }
    ]
}
with open('$SESSIONS_FILE', 'w') as f:
    json.dump(data, f)
"

    run bash -c "
        export PROJECT_ROOT='$TEST_DIR'
        export OPENCODE_SESSION_ID='$OPENCODE_SESSION_ID'
        source '$REPO_ROOT/skills/rddf-session/SKILL.md' 2>/dev/null || true
        # SKILL.md is documentation, not executable. Invoke the bash block from docs.
        # Implementation lives in SKILL.md 'Implementation (Bash)' section as inline bash.
        # Extract via sed range (avoid awk which matches start as end):
        sed -n '/^## Implementation/,/^## /p' '$REPO_ROOT/skills/rddf-session/SKILL.md' \
          | sed '1d;$d' \
          | sed '/^\`\`\`bash/d; /^\`\`\`$/d' \
          > /tmp/rddf_session_impl.sh
        bash /tmp/rddf_session_impl.sh status
    "

    # Verify table header
    [ "$status" -eq 0 ]
    [[ "$output" == *"session_id"* ]]
    [[ "$output" == *"kind"* ]]
    [[ "$output" == *"owner"* ]]
    [[ "$output" == *"state"* ]]
}

@test "rddf-session status: outputs binding line for active session" {
    SESSIONS_FILE="$TEST_DIR/.rddf/state/sessions.json"
    python3 -c "
import json
data = {
    'version': 1,
    'sessions': [
        {
            'session_id': 'rds_a1b2c3d4e5f6',
            'kind': 'stage_ship',
            'state': 'active',
            'owner_opencode_session_id': '$OPENCODE_SESSION_ID',
            'parent_session_id': 'rds_123456789abc',
            'started_at': '2026-08-02T15:00:00+00:00',
            'last_heartbeat': '2026-08-02T15:30:00+00:00',
            'attached_changes': ['add-foo'],
            'goal': {'intent': 'guide-ship'},
        }
    ]
}
with open('$SESSIONS_FILE', 'w') as f:
    json.dump(data, f)
"

    run bash -c "
        export PROJECT_ROOT='$TEST_DIR'
        export OPENCODE_SESSION_ID='$OPENCODE_SESSION_ID'
        sed -n '/^## Implementation/,/^## /p' '$REPO_ROOT/skills/rddf-session/SKILL.md' \
          | sed '1d;$d' \
          | sed '/^\`\`\`bash/d; /^\`\`\`$/d' \
          > /tmp/rddf_session_impl.sh
        bash /tmp/rddf_session_impl.sh status
    "

    [ "$status" -eq 0 ]
    [[ "$output" == *"📍"* ]]
    [[ "$output" == *"rds_a1b2c3d4e5f6"* ]]
    [[ "$output" == *"stage_ship"* ]]
}

@test "rddf-session status: shows counts (active/completed/orphaned/abandoned)" {
    SESSIONS_FILE="$TEST_DIR/.rddf/state/sessions.json"
    python3 -c "
import json
sessions = []
for i, state in enumerate(['active', 'completed', 'orphaned', 'abandoned', 'completed']):
    sessions.append({
        'session_id': f'rds_{i:012x}',
        'kind': 'stage_ship',
        'state': state,
        'owner_opencode_session_id': f'owner_{i}',
        'parent_session_id': None,
        'started_at': '2026-08-02T15:00:00+00:00',
        'last_heartbeat': '2026-08-02T15:30:00+00:00',
        'attached_changes': [],
        'goal': {},
    })
with open('$SESSIONS_FILE', 'w') as f:
    json.dump({'version': 1, 'sessions': sessions}, f)
"

    run bash -c "
        export PROJECT_ROOT='$TEST_DIR'
        export OPENCODE_SESSION_ID='$OPENCODE_SESSION_ID'
        sed -n '/^## Implementation/,/^## /p' '$REPO_ROOT/skills/rddf-session/SKILL.md' \
          | sed '1d;$d' \
          | sed '/^\`\`\`bash/d; /^\`\`\`$/d' \
          > /tmp/rddf_session_impl.sh
        bash /tmp/rddf_session_impl.sh status
    "

    [ "$status" -eq 0 ]
    # Counts section header
    [[ "$output" == *"Counts"* ]] || [[ "$output" == *"📊"* ]] || [[ "$output" == *"active"* ]]
    # 1 active, 2 completed, 1 orphaned, 1 abandoned
    [[ "$output" == *"1"* ]]
}

@test "rddf-session status: handles no sessions gracefully" {
    SESSIONS_FILE="$TEST_DIR/.rddf/state/sessions.json"
    mkdir -p "$(dirname "$SESSIONS_FILE")"
    echo '{"version": 1, "sessions": []}' > "$SESSIONS_FILE"

    run bash -c "
        export PROJECT_ROOT='$TEST_DIR'
        export OPENCODE_SESSION_ID='$OPENCODE_SESSION_ID'
        sed -n '/^## Implementation/,/^## /p' '$REPO_ROOT/skills/rddf-session/SKILL.md' \
          | sed '1d;$d' \
          | sed '/^\`\`\`bash/d; /^\`\`\`$/d' \
          > /tmp/rddf_session_impl.sh
        bash /tmp/rddf_session_impl.sh status
    "

    [ "$status" -eq 0 ]
    [[ "$output" == *"no active"* ]] || [[ "$output" == *"No rddf-sessions"* ]]
}

@test "rddf-session status: read-only (does not modify sessions.json)" {
    SESSIONS_FILE="$TEST_DIR/.rddf/state/sessions.json"
    python3 -c "
import json
data = {'version': 1, 'sessions': [{
    'session_id': 'rds_001122334455',
    'kind': 'stage_ship',
    'state': 'active',
    'owner_opencode_session_id': '$OPENCODE_SESSION_ID',
    'parent_session_id': None,
    'started_at': '2026-08-02T15:00:00+00:00',
    'last_heartbeat': '2026-08-02T15:30:00+00:00',
    'attached_changes': [],
    'goal': {},
}]}
with open('$SESSIONS_FILE', 'w') as f:
    json.dump(data, f)
"
    # Snapshot mtime + content
    BEFORE_HASH=$(sha256sum "$SESSIONS_FILE" | awk '{print $1}')

    bash -c "
        export PROJECT_ROOT='$TEST_DIR'
        export OPENCODE_SESSION_ID='$OPENCODE_SESSION_ID'
        sed -n '/^## Implementation/,/^## /p' '$REPO_ROOT/skills/rddf-session/SKILL.md' \
          | sed '1d;$d' \
          | sed '/^\`\`\`bash/d; /^\`\`\`$/d' \
          > /tmp/rddf_session_impl.sh
        bash /tmp/rddf_session_impl.sh status
    " > /dev/null

    AFTER_HASH=$(sha256sum "$SESSIONS_FILE" | awk '{print $1}')
    [ "$BEFORE_HASH" = "$AFTER_HASH" ] || {
        echo "FAIL: status modified sessions.json (hash changed)"
        return 1
    }
}
