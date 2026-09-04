#!/usr/bin/env bats
#
# Wave 4 Change 2: rdd-arch arch-done triggers auto-feedback recompute
# via the bash hook in skills/rdd-arch/scripts/write_arch_handoff.sh.

load test_helper

setup() {
    PROJECT_ROOT="$BATS_TMPDIR/arch_hook_test"
    mkdir -p "$PROJECT_ROOT/.rddf/state"
    mkdir -p "$PROJECT_ROOT/.rddf/improvements"
    mkdir -p "$PROJECT_ROOT/docs/adr"
    cat > "$PROJECT_ROOT/docs/adr/ADR-0001-test.md" <<EOF
# ADR-0001: test

Status: Accepted
EOF
    cat > "$PROJECT_ROOT/.rddf/improvements/feat-y.md" <<EOF
---
name: feat-y
priority: P1
---
# feat-y
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

@test "rdd-arch arch-done triggers feedback recompute (default ON)" {
    bash -c "source '$REPO_ROOT/skills/rdd-arch/scripts/write_arch_handoff.sh' && write_arch_handoff"

    feedback="$PROJECT_ROOT/.rddf/state/.planner-feedback.json"
    [ -f "$feedback" ]

    python3 -c "
import json
data = json.load(open('$feedback'))
assert len(data['feedbacks']) == 1, data
assert data['feedbacks'][0]['proposal'] == 'feat-y', data
print('ok')
"
}

@test "arch-done SKIP_AUTO_PLANNER_FEEDBACK=yes opt-out suppresses recompute" {
    export SKIP_AUTO_PLANNER_FEEDBACK=yes
    bash -c "source '$REPO_ROOT/skills/rdd-arch/scripts/write_arch_handoff.sh' && write_arch_handoff"

    feedback="$PROJECT_ROOT/.rddf/state/.planner-feedback.json"
    [ ! -f "$feedback" ]
}

@test "arch-done twice → feedback idempotent (R15 true idempotency)" {
    bash -c "source '$REPO_ROOT/skills/rdd-arch/scripts/write_arch_handoff.sh' && write_arch_handoff"
    first_id=$(python3 -c "import json; d=json.load(open('$PROJECT_ROOT/.rddf/state/.planner-feedback.json')); print(d['feedbacks'][0]['feedback_id'])")
    first_lsa=$(python3 -c "import json; d=json.load(open('$PROJECT_ROOT/.rddf/state/.planner-feedback.json')); print(d['feedbacks'][0]['last_seen_at'])")

    bash -c "source '$REPO_ROOT/skills/rdd-arch/scripts/write_arch_handoff.sh' && write_arch_handoff"
    second_id=$(python3 -c "import json; d=json.load(open('$PROJECT_ROOT/.rddf/state/.planner-feedback.json')); print(d['feedbacks'][0]['feedback_id'])")
    second_lsa=$(python3 -c "import json; d=json.load(open('$PROJECT_ROOT/.rddf/state/.planner-feedback.json')); print(d['feedbacks'][0]['last_seen_at'])")

    [ "$first_id" = "$second_id" ]
    [ "$first_lsa" = "$second_lsa" ]
}