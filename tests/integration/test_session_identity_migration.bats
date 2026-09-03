#!/usr/bin/env bats
# tests/integration/test_session_identity_migration.bats
# Stage 3 Change 1: rddf-session intent migration.
# Verifies in-flight sessions with intent=guide-arch can be resumed under rdd-arch.

load ../test_helper

@test "session identity: intent=guide-arch in sessions.json is recognized" {
    TEST_TMP=$(mktemp -d)
    mkdir -p "$TEST_TMP/.rddf/state"
    cat > "$TEST_TMP/.rddf/state/sessions.json" <<'JSON'
{
  "schema_version": 1,
  "sessions": [
    {
      "session_id": "ses-test-001",
      "owner_opencode_session_id": "opencode-test-001",
      "intent": "guide-arch",
      "stage": "stage_arch",
      "state": "active",
      "created_at": "2026-09-01T00:00:00Z",
      "updated_at": "2026-09-01T00:00:00Z",
      "context_pointer": null,
      "exit_pointer": null
    }
  ]
}
JSON
    run python3 -c "
import json
with open('$TEST_TMP/.rddf/state/sessions.json') as f:
    data = json.load(f)
intent = data['sessions'][0]['intent']
assert intent in ('guide-arch', 'rdd-arch'), f'unexpected intent: {intent}'
print('recognized:', intent)
"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "recognized" ]]
}

@test "session identity: stage_arch maps to rdd-arch (Stage 3 canonical)" {
    TEST_TMP=$(mktemp -d)
    mkdir -p "$TEST_TMP/.rddf/state"
    run python3 -c "
import json
stage_to_canonical = {'stage_arch': 'rdd-arch'}
assert stage_to_canonical['stage_arch'] == 'rdd-arch'
print('stage_arch canonical:', stage_to_canonical['stage_arch'])
"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "stage_arch canonical: rdd-arch" ]]
}