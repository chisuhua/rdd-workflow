#!/usr/bin/env bats

load ../test_helper

setup() {
    export TEST_TMPDIR="$(mktemp -d)"
    export PROJECT_ROOT="$TEST_TMPDIR"
    mkdir -p "$PROJECT_ROOT/.rddf/state"
    mkdir -p "$PROJECT_ROOT/openspec/changes"
    echo '{"version": 1, "sessions": []}' > "$PROJECT_ROOT/.rddf/state/sessions.json"
    cd /workspace/project/rdd-workflow
}

teardown() {
    rm -rf "$TEST_TMPDIR"
}

@test "PR2: rddf monitor reads events.jsonl when present (AC-10 preferred path, Oracle B5)" {
    events_file="$TEST_TMPDIR/.rddf/state/events.jsonl"
    cat > "$events_file" <<'EOF'
{"event_id":"evt_001","ts":"2026-09-23T00:00:00+00:00","event_type":"phase_started","severity":"info","message":"test event 1","context":{"session_id":"rds_a","kind":"stage_arch","parent_session_id":null,"owner_opencode_session_id":"ses_A"}}
{"event_id":"evt_002","ts":"2026-09-23T00:00:01+00:00","event_type":"phase_completed","severity":"info","message":"test event 2","context":{"session_id":"rds_a","kind":"stage_arch","parent_session_id":null,"owner_opencode_session_id":"ses_A"}}
EOF

    RDDF_PROJECT_ROOT="$TEST_TMPDIR" run python3 -m skills._lib.cli monitor
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "test event 1"
}

@test "PR2: rddf monitor falls back to event-log.jsonl when events.jsonl missing (Oracle B5 backward compat)" {
    legacy_file="$TEST_TMPDIR/.rddf/state/event-log.jsonl"
    cat > "$legacy_file" <<'EOF'
{"event_id":"evt_legacy","timestamp":"2026-09-23T00:00:00+00:00","event_type":"loop_started","severity":"info","message":"legacy event"}
EOF

    RDDF_PROJECT_ROOT="$TEST_TMPDIR" run python3 -m skills._lib.cli monitor
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "legacy event"
}