#!/usr/bin/env bats
# tests/integration/test_rdd_builder_dispatch_quick.bats
# Integration tests for rdd-builder P0 5-option dispatch-quick (per ADR-0048 §Decision 3).
#
# Coverage:
#  - phase0_approval.sh: 5-option prompt (1 approve / 2 reject / 3 defer / 4 revise / 5 dispatch-quick)
#  - case 5 writes .rddf/state/rdd-quick-context.json (per ADR-0048 contract)
#  - case 5 writes builder-handoff v1.1 approval_status=dispatched_to_quick
#  - case 5 emits DISPATCH_TO_QUICK=1 marker for orchestrator
#  - case 5 warns but continues when planner-handoff::recommended_route != simple
#  - --dispatch-quick CLI flag auto-picks option 5 when recommended_route=simple

load test_helper

setup() {
    REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
    PHASE0="$REPO_ROOT/skills/rdd-builder/scripts/phase0_approval.sh"
    WORK_TMP="$(mktemp -d)"
    cd "$WORK_TMP"
    git init -q .
    mkdir -p openspec/changes/test-change
    echo "# proposal" > openspec/changes/test-change/proposal.md
    echo "- [ ] AC-1" >> openspec/changes/test-change/proposal.md
    mkdir -p .rddf/state
}

teardown() {
    rm -rf "$WORK_TMP"
}

# Helper: run phase0 with explicit cwd + stdin input.
# We must unset PROJECT_ROOT (inherited from test_helper.bash which exports
# PROJECT_ROOT=$REPO_ROOT), otherwise phase0_approval.sh's
# `PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"` will write artifacts to the repo
# root instead of WORK_TMP.
run_phase0() {
    local stdin_input="$1"
    shift
    run env -u PROJECT_ROOT bash -c "cd '$WORK_TMP' && bash '$PHASE0' test-change $*" <<< "$stdin_input"
}

# Helper: write a planner-handoff.json with given recommended_route.
write_handoff() {
    local route="$1"
    cat > "$WORK_TMP/.rddf/state/.planner-handoff.json" <<EOF
{
  "schema": "planner-handoff-v1",
  "version": 1,
  "owner": "rdd-planner",
  "planner_complete_at": "2026-09-09T10:00:00Z",
  "current_sprint": "sprint-2026-09",
  "proposals_ready": ["test-change"],
  "proposals_approved_count": 0,
  "features_active": [],
  "awaiting_builder": ["test-change"],
  "recommended_route": "$route"
}
EOF
}

# ---------------------------------------------------------------------------
# phase0_approval.sh structural: 5-option support
# ---------------------------------------------------------------------------

@test "phase0: SKILL.md documents 5-option (per ADR-0048 §Decision 3)" {
    [ -f "$REPO_ROOT/skills/rdd-builder/SKILL.md" ]
    run grep -c "dispatch-quick\|dispatch_quick\|dispatch to quick" "$REPO_ROOT/skills/rdd-builder/SKILL.md"
    [ "$status" -eq 0 ]
    [ "$output" -ge 3 ]
}

@test "phase0: phase0_approval.sh has case 5 branch" {
    [ -f "$PHASE0" ]
    run grep -E "^\s*5\)" "$PHASE0"
    [ "$status" -eq 0 ]
}

@test "phase0: phase0_approval.sh prompt shows 5 options" {
    run_phase0 "1"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "1) approve" ]]
    [[ "$output" =~ "2) reject" ]]
    [[ "$output" =~ "3) defer" ]]
    [[ "$output" =~ "4) revise" ]]
    [[ "$output" =~ "5) dispatch-quick" ]]
}

@test "phase0: shows planner advisory (recommended_route) before prompt" {
    write_handoff "simple"
    run_phase0 "1"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Planner advisory" ]]
    [[ "$output" =~ "recommended_route = simple" ]]
}

@test "phase0: shows 💡 hint when planner advisory=simple AND AC <= 2" {
    write_handoff "simple"
    run_phase0 "1"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "💡" ]]
    [[ "$output" =~ "option 5" ]]
}

@test "phase0: does NOT show 💡 hint when planner advisory=complex" {
    write_handoff "complex"
    run_phase0 "1"
    [ "$status" -eq 0 ]
    [[ ! "$output" =~ "💡 Planner advisory=simple" ]]
}

@test "phase0: falls back to unknown when planner-handoff missing" {
    run_phase0 "1"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "recommended_route = unknown" ]]
}

# ---------------------------------------------------------------------------
# case 5 (dispatch-quick) behavior
# ---------------------------------------------------------------------------

@test "phase0 case 5: writes .rddf/state/rdd-quick-context.json (per ADR-0048)" {
    write_handoff "simple"
    run_phase0 "5"
    [ "$status" -eq 0 ]
    [ -f .rddf/state/rdd-quick-context.json ]
}

@test "phase0 case 5: rdd-quick-context.json contains required fields (per ADR-0048 schema)" {
    write_handoff "simple"
    run_phase0 "5"
    [ "$status" -eq 0 ]
    run python3 -c "
import json
ctx = json.load(open('.rddf/state/rdd-quick-context.json'))
assert ctx['change_name'] == 'test-change'
assert ctx['proposal_path'] == 'openspec/changes/test-change/proposal.md'
assert ctx['from_builder'] is True
assert 'dispatched_at' in ctx
assert ctx['planner_advisory']['recommended_route'] == 'simple'
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

@test "phase0 case 5: writes builder-handoff with approval_status=dispatched_to_quick" {
    write_handoff "simple"
    run_phase0 "5"
    [ "$status" -eq 0 ]
    [ -f .rddf/state/builder/test-change.json ]
    run python3 -c "
import json
h = json.load(open('.rddf/state/builder/test-change.json'))
assert h['approval_status'] == 'dispatched_to_quick', h
assert 'dispatch_quick_at' in h, h
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

@test "phase0 case 5: emits DISPATCH_TO_QUICK=1 marker for orchestrator" {
    write_handoff "simple"
    run_phase0 "5"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "DISPATCH_TO_QUICK=1" ]]
    [[ "$output" =~ "CHANGE_NAME=test-change" ]]
}

@test "phase0 case 5: explicit message about rdd-quick follow-up actions" {
    write_handoff "simple"
    run_phase0 "5"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "completed" ]]
    [[ "$output" =~ "escalated" ]]
    [[ "$output" =~ "openspec archive" ]]
}

@test "phase0 case 5: warns but continues when recommended_route != simple" {
    write_handoff "complex"
    run_phase0 "5"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "explicitly bypassed" ]]
    [ -f .rddf/state/rdd-quick-context.json ]
}

# ---------------------------------------------------------------------------
# --dispatch-quick CLI flag (auto-select case 5)
# ---------------------------------------------------------------------------

@test "phase0 --dispatch-quick: auto-picks case 5 when recommended_route=simple" {
    write_handoff "simple"
    run env -u PROJECT_ROOT bash -c "cd '$WORK_TMP' && bash '$PHASE0' test-change --dispatch-quick"
    [ "$status" -eq 0 ]
    [ -f .rddf/state/rdd-quick-context.json ]
}

@test "phase0 --dispatch-quick: refuses when recommended_route != simple" {
    write_handoff "complex"
    run env -u PROJECT_ROOT bash -c "cd '$WORK_TMP' && bash '$PHASE0' test-change --dispatch-quick"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "recommended_route=simple" ]]
}

# ---------------------------------------------------------------------------
# case 1 (approve) still works — backward compat
# ---------------------------------------------------------------------------

@test "phase0 case 1: approve still works (backward compat)" {
    mkdir -p .rddf/improvements
    cat > .rddf/improvements/test-change.md <<'EOF'
---
name: test-change
priority: P3
---

# test-change

## Why
typo fix

## Acceptance
- [ ] AC-1

## Capabilities
- (none)
EOF

    write_handoff "complex"

    run_phase0 "1"
    [ "$status" -eq 0 ]
    grep -q "AC-1" openspec/changes/test-change/proposal.md
    [ -f .rddf/state/builder/test-change.json ]
    run python3 -c "
import json
h = json.load(open('.rddf/state/builder/test-change.json'))
assert h['approval_status'] == 'approved', h
print('OK')
"
    [ "$status" -eq 0 ]
}
