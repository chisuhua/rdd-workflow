#!/usr/bin/env bats
#
# Wave 4 Change 2: planner sync --apply triggers auto-feedback recompute.
# Verifies the hook added to _lib/cli/planner_cmd.py fires when
# `rdrdfl planner sync --apply` runs and SKIP_AUTO_PLANNER_FEEDBACK is unset.

load test_helper

setup() {
    REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
    PROJECT_ROOT="$BATS_TMPDIR/hook_test"
    mkdir -p "$PROJECT_ROOT/.rddf/state"
    mkdir -p "$PROJECT_ROOT/.rddf/improvements"
    cat > "$PROJECT_ROOT/.rddf/improvements/feat-x.md" <<EOF
---
name: feat-x
priority: P1
---
# feat-x
EOF
    cat > "$PROJECT_ROOT/.rddf/state/.planner-state.json" <<EOF
{
  "version": 1,
  "state_revision": 0,
  "current_sprint": "sprint-2026-09",
  "last_sync_at": "2026-09-04T00:00:00+00:00",
  "active_projects": [],
  "unmapped_proposals": [],
  "synced_proposals": []
}
EOF
    export PROJECT_ROOT
    unset SKIP_AUTO_PLANNER_FEEDBACK
}

teardown() {
    unset SKIP_AUTO_PLANNER_FEEDBACK
    rm -rf "$PROJECT_ROOT"
}

@test "planner sync --apply triggers feedback recompute (default ON)" {
    run python3 -m _lib.cli planner sync --apply --project-root "$PROJECT_ROOT"
    [ "$status" -eq 0 ]

    feedback="$PROJECT_ROOT/.rddf/state/.planner-feedback.json"
    [ -f "$feedback" ]

    python3 -c "
import json
data = json.load(open('$feedback'))
assert len(data['feedbacks']) == 1, data
assert data['feedbacks'][0]['proposal'] == 'feat-x', data
assert data['feedbacks'][0]['kind'] == 'unmapped_proposal', data
print('ok')
"
}

@test "SKIP_AUTO_PLANNER_FEEDBACK=yes opt-out suppresses recompute" {
    export SKIP_AUTO_PLANNER_FEEDBACK=yes
    run python3 -m _lib.cli planner sync --apply --project-root "$PROJECT_ROOT"
    [ "$status" -eq 0 ]

    feedback="$PROJECT_ROOT/.rddf/state/.planner-feedback.json"
    [ ! -f "$feedback" ]
}

@test "two consecutive sync --apply → feedback file idempotent (R15 true idempotency)" {
    python3 -m _lib.cli planner sync --apply --project-root "$PROJECT_ROOT" >/dev/null
    first_id=$(python3 -c "import json; d=json.load(open('$PROJECT_ROOT/.rddf/state/.planner-feedback.json')); print(d['feedbacks'][0]['feedback_id'])")
    first_lsa=$(python3 -c "import json; d=json.load(open('$PROJECT_ROOT/.rddf/state/.planner-feedback.json')); print(d['feedbacks'][0]['last_seen_at'])")

    python3 -m _lib.cli planner sync --apply --project-root "$PROJECT_ROOT" >/dev/null
    second_id=$(python3 -c "import json; d=json.load(open('$PROJECT_ROOT/.rddf/state/.planner-feedback.json')); print(d['feedbacks'][0]['feedback_id'])")
    second_lsa=$(python3 -c "import json; d=json.load(open('$PROJECT_ROOT/.rddf/state/.planner-feedback.json')); print(d['feedbacks'][0]['last_seen_at'])")

    [ "$first_id" = "$second_id" ]
    [ "$first_lsa" = "$second_lsa" ]
}