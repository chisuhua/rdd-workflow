#!/usr/bin/env bats

load ../test_helper

setup() {
    export TEST_TMPDIR="$(mktemp -d)"
    export PROJECT_ROOT="$TEST_TMPDIR"
    mkdir -p "$PROJECT_ROOT/.rddf/state"
}

teardown() {
    rm -rf "$TEST_TMPDIR"
}

@test "PR4: rdd-doctor detects malformed events.jsonl (AC-12)" {
    cat > "$TEST_TMPDIR/.rddf/state/events.jsonl" <<'EOF'
{"event_id":"evt_001","ts":"2026-09-23T00:00:00+00:00","event_type":"phase_started","severity":"info","message":"valid","context":{}}
not_valid_json_here
{"event_id":"evt_002","ts":"2026-09-23T00:00:01+00:00","event_type":"phase_completed","severity":"info","message":"valid2","context":{}}
EOF

    run env RDDF_PROJECT_ROOT="$TEST_TMPDIR" python3 -c "
import sys
sys.path.insert(0, '/workspace/project/rdd-workflow/skills/rdd-doctor/scripts')
from checks.state_schema_check import run
findings = run()
malformed = [f for f in findings if 'events.jsonl' in (f.file or '') and 'invalid JSON' in f.snippet]
assert len(malformed) >= 1, f'expected ≥1 malformed-events finding, got {len(findings)} findings: {[(f.severity.value, f.file, f.snippet) for f in findings]}'
"
    [ "$status" -eq 0 ]
}

@test "PR4: rdd-doctor accepts well-formed events.jsonl (AC-12)" {
    cat > "$TEST_TMPDIR/.rddf/state/events.jsonl" <<'EOF'
{"event_id":"evt_001","ts":"2026-09-23T00:00:00+00:00","event_type":"phase_started","severity":"info","message":"valid","context":{"session_id":"r1","kind":"stage_arch","parent_session_id":null,"owner_opencode_session_id":"s"}}
EOF
    echo '{"version": 1, "sessions": []}' > "$TEST_TMPDIR/.rddf/state/sessions.json"

    run env RDDF_PROJECT_ROOT="$TEST_TMPDIR" python3 -c "
import sys
sys.path.insert(0, '/workspace/project/rdd-workflow/skills/rdd-doctor/scripts')
from checks.state_schema_check import run
findings = run()
malformed = [f for f in findings if 'events.jsonl' in (f.file or '') and 'invalid JSON' in f.snippet]
assert len(malformed) == 0, f'expected 0 malformed-events findings, got {len(findings)}: {[(f.severity.value, f.file, f.snippet) for f in findings]}'
"
    [ "$status" -eq 0 ]
}

@test "PR4: rdd-doctor reports last_seen_offset out of range (AC-12)" {
    cat > "$TEST_TMPDIR/.rddf/state/sessions.json" <<'EOF'
{
  "version": 3,
  "sessions": [
    {
      "session_id": "rds_guide",
      "kind": "stage_guide",
      "owner_opencode_session_id": "ses_A",
      "goal": {"intent": "guide-orchestrator", "last_seen_offset": 9999},
      "state": "active",
      "started_at": "2026-09-23T00:00:00+00:00",
      "last_heartbeat": "2026-09-23T00:00:00+00:00"
    }
  ]
}
EOF
    cat > "$TEST_TMPDIR/.rddf/state/events.jsonl" <<'EOF'
{"event_id":"e1","ts":"2026-09-23T00:00:00+00:00","event_type":"phase_started","severity":"info","message":"e1","context":{}}
{"event_id":"e2","ts":"2026-09-23T00:00:01+00:00","event_type":"phase_completed","severity":"info","message":"e2","context":{}}
EOF

    run env RDDF_PROJECT_ROOT="$TEST_TMPDIR" python3 -c "
import sys
sys.path.insert(0, '/workspace/project/rdd-workflow/skills/rdd-doctor/scripts')
from checks.state_schema_check import run
findings = run()
offset_findings = [f for f in findings if 'last_seen_offset' in (f.snippet or '')]
assert len(offset_findings) >= 1, f'expected ≥1 offset finding, got {len(findings)} findings: {[(f.severity.value, f.file, f.snippet) for f in findings]}'
"
    [ "$status" -eq 0 ]
}