load ../test_helper

@test "rddf-sessions-gc: gc script exists" {
    PROJECT_ROOT=$(git rev-parse --show-toplevel)
    run test -f "$PROJECT_ROOT/skills/rddf-session/scripts/rddf_sessions_gc.py"
    [ "$status" -eq 0 ]
}

@test "rddf-sessions-gc: gc_sessions function exists" {
    PROJECT_ROOT=$(git rev-parse --show-toplevel)
    run grep -c "def gc_sessions" "$PROJECT_ROOT/skills/rddf-session/scripts/rddf_sessions_gc.py"
    [ "$status" -eq 0 ]
    [ "$output" -ge 1 ]
}

@test "rddf-sessions-gc: dry-run does not modify file" {
    TEST_DIR=$(mktemp -d)
    mkdir -p "$TEST_DIR/.rddf/state"
    old_date=$(python3 -c "import datetime; print((datetime.datetime.utcnow() - datetime.timedelta(days=10)).strftime('%Y-%m-%dT%H:%M:%SZ'))")
    python3 -c "
import json
data = {'sessions': [{'id': 'rds_stale', 'owner_opencode_session_id': 'current', 'status': 'abandoned', 'started_at': '$old_date'}]}
with open('$TEST_DIR/.rddf/state/sessions.json', 'w') as f:
    json.dump(data, f)
"
    PROJECT_ROOT=$(git rev-parse --show-toplevel)
    run python3 "$PROJECT_ROOT/skills/rddf-session/scripts/rddf_sessions_gc.py" --dry-run "$TEST_DIR"
    [ "$status" -eq 0 ]
    count=$(python3 -c "import json; d=json.load(open('$TEST_DIR/.rddf/state/sessions.json')); print(len(d['sessions']))")
    [ "$count" -eq 1 ]
    rm -rf "$TEST_DIR"
}

@test "rddf-sessions-gc: actual gc removes stale session" {
    TEST_DIR=$(mktemp -d)
    mkdir -p "$TEST_DIR/.rddf/state"
    old_date=$(python3 -c "import datetime; print((datetime.datetime.utcnow() - datetime.timedelta(days=10)).strftime('%Y-%m-%dT%H:%M:%SZ'))")
    python3 -c "
import json
data = {'sessions': [
    {'id': 'rds_stale', 'owner_opencode_session_id': 'current', 'status': 'abandoned', 'started_at': '$old_date'},
    {'id': 'rds_valid', 'owner_opencode_session_id': 'ses_real', 'status': 'active', 'started_at': '$old_date'}
]}
with open('$TEST_DIR/.rddf/state/sessions.json', 'w') as f:
    json.dump(data, f)
"
    PROJECT_ROOT=$(git rev-parse --show-toplevel)
    run python3 "$PROJECT_ROOT/skills/rddf-session/scripts/rddf_sessions_gc.py" "$TEST_DIR"
    [ "$status" -eq 0 ]
    count=$(python3 -c "import json; d=json.load(open('$TEST_DIR/.rddf/state/sessions.json')); print(len(d['sessions']))")
    [ "$count" -eq 1 ]
    rm -rf "$TEST_DIR"
}
