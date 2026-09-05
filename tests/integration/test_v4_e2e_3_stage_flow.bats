#!/usr/bin/env bats
# v4 architecture end-to-end test: rdd-arch → rdd-planner → rdd-builder chain.
#
# Per spec 2026-09-04-rdd-workflow-v4-architecture-stage-merge.md §3.3-§3.5.
# Validates the cross-stage handoff protocol by exercising the canonical
# Python API surface of each stage's handoff writers + router + retry logic.
# Integration with the bash phase scripts is covered by per-stage bats
# tests (test_rdd_arch_cli.bats, test_planner_cmd.bats, ...); this test
# focuses on the data-flow contract that ties the 3 stages together.
#
# Run: bats tests/integration/test_v4_e2e_3_stage_flow.bats

load test_helper

setup() {
    TEST_TMP=$(mktemp -d)
    cd "$TEST_TMP"
    git init -q .
    git config user.email "e2e@test.local"
    git config user.name "E2E Test"
    mkdir -p docs/adr
    cat > docs/adr/ADR-0001-test-arch.md <<'EOF'
# ADR-0001: Test Architecture

**Status**: 已采纳 (2026-01-01)

## Context
E2E test fixture.
EOF
    cat > docs/adr/ADR-0002-test-impl.md <<'EOF'
# ADR-0002: Test Implementation

**Status**: 已采纳 (2026-01-02)

## Context
E2E test fixture.
EOF
    cat > roadmap.md <<'EOF'
# Roadmap

**当前阶段**: phase-1

## Phase Skeleton
| Phase | Theme | Status |
|-------|-------|--------|
| phase-1 | foo | active |
EOF
    mkdir -p .rddf/state openspec/changes/v4-e2e-fixture
    cat > openspec/changes/v4-e2e-fixture/proposal.md <<'EOF'
# Proposal
**主题**: v4-e2e-fixture
EOF
    export PYTHONPATH="$REPO_ROOT:$PYTHONPATH"
}

teardown() {
    rm -rf "$TEST_TMP"
}

# -----------------------------------------------------------------------------
# Stage 1: rdd-arch → writes .arch-handoff.json (v3 schema per ADR-0016)
# -----------------------------------------------------------------------------

@test "v4 E2E 1/10: rdd-arch setup writes .arch-handoff.json v3 contract" {
    run python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
from skills.rdd_arch.scripts.write_arch_handoff import write_arch_handoff
result = write_arch_handoff(
    project_root='$TEST_TMP',
    discovered_adr_dir='docs/adr',
    discovered_roadmap_path='roadmap.md',
    discovered_adr_pattern='ADR-*.md',
    discovered_adr_dir_found='true',
    discovered_roadmap_found='true',
    discovered_arch_found='false',
    discovered_adr_dir_tried='3',
    discovered_roadmap_tried='2',
    discovered_arch_tried='3',
    roadmap_exists_bool='true',
)
print(f'version={result[\"version\"]}')
print(f'adr_count={result[\"adr_count\"]}')
print(f'completed={result[\"completed_adr_ids\"]}')
print(f'phase={result[\"current_phase\"]}')
"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "version=3" ]]
    [[ "$output" =~ "adr_count=2" ]]
    [[ "$output" =~ "phase=phase-1" ]]
    [ -f .rddf/state/.arch-handoff.json ]
}

# -----------------------------------------------------------------------------
# Stage 2: rdd-planner → writes .planner-handoff.json (v1 schema per spec §3.3)
# -----------------------------------------------------------------------------

@test "v4 E2E 2/10: rdd-planner stage entry writes .planner-handoff.json v1 contract" {
    PROJECT_ROOT="$TEST_TMP" \
    PROPOSALS_AUTHORED="add-foo-impl,add-bar-impl" \
    PROPOSALS_APPROVED_COUNT="2" \
    FEATURES_ACTIVE="feat-foo-bar" \
    CURRENT_SPRINT="sprint-2026-09" \
        run python3 -m _lib.planner_handoff
    [ "$status" -eq 0 ]
    [ -f .rddf/state/.planner-handoff.json ]
    run cat .rddf/state/.planner-handoff.json
    [[ "$output" =~ '"schema": "planner-handoff-v1"' ]]
    [[ "$output" =~ '"version": 1' ]]
    [[ "$output" =~ '"owner": "rdd-planner"' ]]
    [[ "$output" =~ '"current_sprint": "sprint-2026-09"' ]]
    [[ "$output" =~ "add-foo-impl" ]]
    [[ "$output" =~ "feat-foo-bar" ]]
}

# -----------------------------------------------------------------------------
# Stage 3: rdd-builder — 6-phase state machine + verifier retry + cross-stage feedback
# -----------------------------------------------------------------------------

@test "v4 E2E 3/10: rdd-builder writes per-change handoff at .rddf/state/builder/<change>.json" {
    CHANGE=v4-e2e-fixture
    run python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
from _lib.builder_handoff import write_builder_handoff, read_builder_handoff
result = write_builder_handoff(
    project_root='$TEST_TMP',
    change_name='$CHANGE',
    current_phase='phase-0',
    approval_status='approved',
    execution_mode_decision={'mode': 'lightweight', 'reason': 'files=2<=2 AND tasks=3<=3'},
    worktree_path='',
    branch='openspec/$CHANGE',
)
assert result['change_name'] == '$CHANGE'
assert result['current_phase'] == 'phase-0'
assert result['approval_status'] == 'approved'
assert result['execution_mode_decision']['mode'] == 'lightweight'
data = read_builder_handoff('$TEST_TMP', '$CHANGE')
assert data['change_name'] == '$CHANGE'
print('handoff round-trip OK')
"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "handoff round-trip OK" ]]
    [ -f ".rddf/state/builder/$CHANGE.json" ]
}

@test "v4 E2E 4/10: rdd-builder retries increment on verifier back-route" {
    CHANGE=v4-e2e-fixture
    run python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
from _lib.builder_handoff import write_builder_handoff, increment_retry
write_builder_handoff('$TEST_TMP', '$CHANGE', current_phase='phase-0', approval_status='approved')
data = increment_retry('$TEST_TMP', '$CHANGE', to_phase='phase-2', verifier_kind='implementation_gap', verifier_exit_code=1)
assert data['retry_count'] == 1
assert data['current_phase'] == 'phase-2'
assert data['retry_history'][0]['verifier_exit_code'] == 1
data = increment_retry('$TEST_TMP', '$CHANGE', to_phase='phase-1', verifier_kind='ac_fail', verifier_exit_code=2)
assert data['retry_count'] == 2
assert data['retry_history'][1]['verifier_kind'] == 'ac_fail'
print(f'retry_count={data[\"retry_count\"]}, history_len={len(data[\"retry_history\"])}')
"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "retry_count=2" ]]
    [[ "$output" =~ "history_len=2" ]]
}

@test "v4 E2E 5/10: rdd-builder retry loop halts at max_retries=3" {
    CHANGE=v4-e2e-fixture
    run python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
from _lib.builder_handoff import write_builder_handoff, increment_retry
from _lib.builder_retry import route_verifier_verdict, should_halt_for_retry_exceeded

write_builder_handoff('$TEST_TMP', '$CHANGE', current_phase='phase-3', retry_count=0, max_retries=3)

# exit_code=1 → back-route to phase-2
for i in range(4):
    data = increment_retry('$TEST_TMP', '$CHANGE', to_phase='phase-2', verifier_kind='implementation_gap', verifier_exit_code=1)

# After 4 retries (>max_retries=3), should halt
assert should_halt_for_retry_exceeded(data['retry_count'], data['max_retries']) is True, f'retry_count={data[\"retry_count\"]}, max={data[\"max_retries\"]}'

# Exit code 4 → halted_max_loops
verdict = route_verifier_verdict(4)
assert verdict['halted'] is True
assert verdict['verifier_kind'] == 'halted_max_loops'

print(f'halted at retry_count={data[\"retry_count\"]}, kind={verdict[\"verifier_kind\"]}')
"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "halted at retry_count=4" ]]
    [[ "$output" =~ "halted_max_loops" ]]
}

@test "v4 E2E 6/10: rdd-builder retry routing covers all 5 ADR-0034 exit codes" {
    run python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
from _lib.builder_retry import route_verifier_verdict

# exit_code=0 → phase-3 archive (success)
v = route_verifier_verdict(0)
assert v['next_phase'] == 'phase-3-archive'
assert v['should_back_route'] is False
assert v['halted'] is False

# exit_code=1 → phase-2 (implementation_gap)
v = route_verifier_verdict(1)
assert v['next_phase'] == 'phase-2'
assert v['should_back_route'] is True

# exit_code=2 → phase-1 (ac_fail)
v = route_verifier_verdict(2)
assert v['next_phase'] == 'phase-1'
assert v['should_back_route'] is True

# exit_code=3 → halt (needs_human)
v = route_verifier_verdict(3)
assert v['next_phase'] == 'halt'
assert v['halted'] is True
assert v['verifier_kind'] == 'needs_human'

# exit_code=4 → halt (halted_max_loops)
v = route_verifier_verdict(4)
assert v['next_phase'] == 'halt'
assert v['verifier_kind'] == 'halted_max_loops'

# unknown exit code → halt with unknown kind
v = route_verifier_verdict(99)
assert v['halted'] is True
assert 'unknown' in v['verifier_kind']

print('all 5 exit codes + unknown covered')
"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "all 5 exit codes + unknown covered" ]]
}

@test "v4 E2E 7/10: rdd-builder deps absorbs ADR-0024 execution_mode matrix" {
    run python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
from _lib.builder_deps import decide_execution_mode

# Small change → lightweight
m = decide_execution_mode(file_count=2, task_count=3, risk_keywords=[])
assert m['mode'] == 'lightweight', m

# Large files → worktree
m = decide_execution_mode(file_count=5, task_count=2, risk_keywords=[])
assert m['mode'] == 'worktree'
assert 'files=5>2' in m['reason']

# Many tasks → worktree
m = decide_execution_mode(file_count=2, task_count=10, risk_keywords=[])
assert m['mode'] == 'worktree'
assert 'tasks=10>3' in m['reason']

# Risk keywords → worktree
m = decide_execution_mode(file_count=1, task_count=1, risk_keywords=['refactor'])
assert m['mode'] == 'worktree'
assert 'refactor' in m['reason']

# Migration risk → worktree
m = decide_execution_mode(file_count=1, task_count=1, risk_keywords=['migration'])
assert m['mode'] == 'worktree'

# No risk, small → lightweight
m = decide_execution_mode(file_count=1, task_count=1, risk_keywords=[])
assert m['mode'] == 'lightweight'

print('ADR-0024 execution_mode matrix preserved')
"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "ADR-0024 execution_mode matrix preserved" ]]
}

@test "v4 E2E 8/10: rdd-builder cross-stage feedback routes ac-fail to planner-feedback" {
    CHANGE=v4-e2e-fixture
    run python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
from _lib.builder_feedback_router import route_feedback

# ac-fail routed to planner
result = route_feedback(
    feedback_entry={
        'feedback_id': 'fb-e2e-001',
        'kind': 'ac-fail',
        'ref_change': '$CHANGE',
        'body': 'AC-3 verification failed: missing edge case',
        'severity': 'warning',
    },
    project_root='$TEST_TMP',
    accept_builder_source=True,
    current_change='$CHANGE',
)
assert result['feedback_id'] == 'fb-e2e-001'
assert result['routed_to_planner_feedback'] is True
print(f'routed={result[\"routed_to_planner_feedback\"]}')
"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "routed=True" ]]
    [ -f .rddf/state/.planner-feedback.json ]
    run cat .rddf/state/.planner-feedback.json
    [[ "$output" =~ '"from_builder": true' ]]
    [[ "$output" =~ "fb-e2e-001" ]]
    [[ "$output" =~ "AC-3 verification failed" ]]
}

@test "v4 E2E 9/10: rdd-builder cross-stage feedback does NOT route non-ac-fail kinds" {
    CHANGE=v4-e2e-fixture
    run python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
from _lib.builder_feedback_router import route_feedback

# rejected/needs-revision kind → NOT routed (planner doesn't act on these)
result = route_feedback(
    feedback_entry={
        'feedback_id': 'fb-e2e-002',
        'kind': 'rejected',
        'ref_change': '$CHANGE',
        'body': 'User rejected in Phase 0',
    },
    project_root='$TEST_TMP',
    accept_builder_source=True,
    current_change='$CHANGE',
)
assert result['routed_to_planner_feedback'] is False
print(f'rejected→planner: {result[\"routed_to_planner_feedback\"]}')
"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "rejected" ]]
    [[ "$output" =~ "False" ]]
}

@test "v4 E2E 10/10: 3-stage handoff file chain is consistent (arch→planner→builder)" {
    CHANGE=v4-e2e-fixture
    # Write all 3 stage handoffs in sequence
    PROJECT_ROOT="$TEST_TMP" \
    PROPOSALS_AUTHORED="$CHANGE" \
    PROPOSALS_APPROVED_COUNT="1" \
    FEATURES_ACTIVE="feat-e2e" \
    CURRENT_SPRINT="sprint-2026-09" \
        run python3 -m _lib.planner_handoff
    [ "$status" -eq 0 ]

    run python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
from skills.rdd_arch.scripts.write_arch_handoff import write_arch_handoff
from _lib.planner_handoff import read_planner_handoff
from _lib.builder_handoff import write_builder_handoff

# Stage 1
write_arch_handoff(
    project_root='$TEST_TMP',
    discovered_adr_dir='docs/adr',
    discovered_roadmap_path='roadmap.md',
    discovered_adr_pattern='ADR-*.md',
    discovered_adr_dir_found='true',
    discovered_roadmap_found='true',
    discovered_arch_found='false',
    discovered_adr_dir_tried='3',
    discovered_roadmap_tried='2',
    discovered_arch_tried='3',
    roadmap_exists_bool='true',
)

# Stage 3 (builder)
write_builder_handoff('$TEST_TMP', '$CHANGE', current_phase='phase-0', approval_status='approved')

# Read all 3
import json, os
arch = json.load(open('$TEST_TMP/.rddf/state/.arch-handoff.json'))
planner = read_planner_handoff('$TEST_TMP')
builder_path = '$TEST_TMP/.rddf/state/builder/$CHANGE.json'
builder = json.load(open(builder_path))

# Consistency checks
assert arch['version'] == 3, f'arch version={arch[\"version\"]}'
assert arch['adr_count'] == 2, f'arch adr_count={arch[\"adr_count\"]}'
assert arch['current_phase'] == 'phase-1', f'arch current_phase={arch[\"current_phase\"]}'

assert planner['schema'] == 'planner-handoff-v1'
assert planner['version'] == 1
assert planner['owner'] == 'rdd-planner'
assert planner['current_sprint'] == 'sprint-2026-09'
assert '$CHANGE' in planner['proposals_authored']

assert builder['schema'] == 'builder-handoff-v1'
assert builder['change_name'] == '$CHANGE'
assert builder['approval_status'] == 'approved'

# Phase 0 handoff owns retry_count=0
assert builder['retry_count'] == 0
assert builder['max_retries'] == 3

# All 3 files co-exist
files = sorted(os.listdir('$TEST_TMP/.rddf/state'))
print(f'state files: {files}')

# Per-change builder subdir present
builder_files = sorted(f for f in os.listdir('$TEST_TMP/.rddf/state/builder') if not f.endswith('.lock'))
print(f'builder files: {builder_files}')
assert builder_files == ['$CHANGE.json']
"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "state files:" ]]
    [[ "$output" =~ ".arch-handoff.json" ]]
    [[ "$output" =~ ".planner-handoff.json" ]]
    [[ "$output" =~ "builder" ]]
    [[ "$output" =~ "$CHANGE.json" ]]
}
