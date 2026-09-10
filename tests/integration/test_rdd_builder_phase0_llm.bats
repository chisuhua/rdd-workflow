#!/usr/bin/env bats
# tests/integration/test_rdd_builder_phase0_llm.bats
# Integration tests for rdd-builder Phase 0 LLM integration (per ADR-0049).
#
# Coverage:
#  - SKILL.md contains "LLM Pre-flight Reasoning" block (≥ 25 lines)
#  - SKILL.md contains "Case 2/3/4: LLM-generated feedback body" block (≥ 20 lines)
#  - SKILL.md contains "Case 5: dispatch-quick + LLM hidden complexity check" block (≥ 25 lines)
#  - SKILL.md references ADR-0049 (≥ 1 cite)
#  - phase0_approval.sh case 5 reads dispatch_quick_review from builder-handoff
#  - phase0_approval.sh case 5 emits warning (but does not block) when complexity_confirmed=complex
#  - --dispatch-quick CLI flag still hard-validates recommended_route=simple (per ADR-0048, unchanged)
#  - builder_handoff_schema.json approval_status enum includes dispatched_to_quick (bug fix)
#  - builder_handoff_schema.json dispatch_quick_review field defined (new per ADR-0049)
#  - phase0_approval.sh LLM signal is appended to rdd-quick-context.json

load test_helper

setup() {
    REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
    SKILL_FILE="$REPO_ROOT/skills/rdd-builder/SKILL.md"
    PHASE0="$REPO_ROOT/skills/rdd-builder/scripts/phase0_approval.sh"
    SCHEMA_FILE="$REPO_ROOT/_lib/schemas/builder_handoff_schema.json"
    BUILDER_HANDOFF_LIB="$REPO_ROOT/_lib/builder_handoff.py"
    WORK_TMP="$(mktemp -d)"
    cd "$WORK_TMP"
    git init -q .
    mkdir -p openspec/changes/test-change
    echo "# proposal" > openspec/changes/test-change/proposal.md
    echo "- [ ] AC-1" >> openspec/changes/test-change/proposal.md
    mkdir -p .rddf/state/builder
    mkdir -p .rddf/improvements
    cat > .rddf/improvements/test-change.md <<'IMPROVE_EOF'
---
name: test-change
priority: P3
---

## Why
fix typo

## What
docs/README.md

## How
edit

## Acceptance
- [ ] typo fixed

## Capabilities
MUST: fix typo
MUST NOT: change behavior
IMPROVE_EOF
}

teardown() {
    rm -rf "$WORK_TMP"
}

# Helper: run phase0_approval.sh with explicit cwd.
# test_helper.bash exports PROJECT_ROOT=$REPO_ROOT which would override
# phase0's `PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"` default. We unset it
# and pass PROJECT_ROOT explicitly to ensure artifacts go to WORK_TMP.
run_phase0() {
    run env -u PROJECT_ROOT PROJECT_ROOT="$WORK_TMP" bash "$PHASE0" "$@"
}

# Helper: write planner-handoff.json with given recommended_route.
write_planner_handoff() {
    local route="$1"
    cat > .rddf/state/.planner-handoff.json <<EOF
{
  "schema": "planner-handoff-v1",
  "version": 1,
  "owner": "rdd-planner",
  "recommended_route": "$route"
}
EOF
}

# Helper: write builder-handoff.json with optional LLM dispatch_quick_review.
write_builder_handoff() {
    local complexity="${1:-}"
    local suggested="${2:-proceed}"
    local concerns_json="${3:-[]}"
    if [ -n "$complexity" ]; then
        cat > .rddf/state/builder/test-change.json <<EOF
{
  "schema": "builder-handoff-v1",
  "version": 1,
  "owner": "rdd-builder",
  "change_name": "test-change",
  "current_phase": "phase-0",
  "approval_status": "pending",
  "retry_count": 0,
  "max_retries": 3,
  "dispatch_quick_review": {
    "complexity_confirmed": "$complexity",
    "concerns": $concerns_json,
    "suggested_action": "$suggested",
    "reviewed_at": "2026-09-10T10:00:00Z"
  }
}
EOF
    else
        cat > .rddf/state/builder/test-change.json <<'EOF'
{
  "schema": "builder-handoff-v1",
  "version": 1,
  "owner": "rdd-builder",
  "change_name": "test-change",
  "current_phase": "phase-0",
  "approval_status": "pending",
  "retry_count": 0,
  "max_retries": 3
}
EOF
    fi
}


# --- SKILL.md structural assertions ---

@test "rdd-builder SKILL.md: contains 'LLM Pre-flight Reasoning' block (≥ 25 lines)" {
    run grep -c "LLM Pre-flight Reasoning" "$SKILL_FILE"
    [ "$status" -eq 0 ]
    [ "$output" -ge 1 ]

    # Block spans multiple lines: from "阶段 0.0" header to next "阶段 0.x" header
    run bash -c "
        awk '/## 阶段 0\\.0 — LLM Pre-flight Reasoning/,/^---$/' '$SKILL_FILE' | wc -l
    "
    [ "$status" -eq 0 ]
    [ "$output" -ge 25 ]
}

@test "rdd-builder SKILL.md: contains Case 2/3/4 LLM feedback body block (≥ 20 lines)" {
    run grep -c "Case 2/3/4: LLM-generated feedback body" "$SKILL_FILE"
    [ "$status" -eq 0 ]
    [ "$output" -ge 1 ]

    run bash -c "
        awk '/## 阶段 0\\.2 — Case 2\\/3\\/4: LLM-generated feedback body/,/^---$/' '$SKILL_FILE' | wc -l
    "
    [ "$status" -eq 0 ]
    [ "$output" -ge 20 ]
}

@test "rdd-builder SKILL.md: contains Case 5 LLM hidden complexity check block (≥ 25 lines)" {
    run grep -c "Case 5: dispatch-quick + LLM hidden complexity check" "$SKILL_FILE"
    [ "$status" -eq 0 ]
    [ "$output" -ge 1 ]

    run bash -c "
        awk '/## 阶段 0\\.3 — Case 5: dispatch-quick/,/^---$/' '$SKILL_FILE' | wc -l
    "
    [ "$status" -eq 0 ]
    [ "$output" -ge 25 ]
}

@test "rdd-builder SKILL.md: references ADR-0049 (≥ 1 cite)" {
    run grep -c "ADR-0049" "$SKILL_FILE"
    [ "$status" -eq 0 ]
    [ "$output" -ge 1 ]
}

@test "rdd-builder SKILL.md: data source is .rddf/improvements (not proposal.md)" {
    # Per user key correction: LLM reads improvement 5 段 primary, proposal.md fallback
    run grep -c "PRIMARY（必读）.*\\.rddf/improvements/<change>\\.md" "$SKILL_FILE"
    [ "$status" -eq 0 ]
    [ "$output" -ge 1 ]
}

@test "rdd-builder SKILL.md: FALLBACK only when PRIMARY missing" {
    # proposal.md is fallback, not primary
    run grep -c "FALLBACK（仅当 1 缺失时）" "$SKILL_FILE"
    [ "$status" -eq 0 ]
    [ "$output" -ge 1 ]
}

@test "rdd-builder SKILL.md: documents advisor priority decision (advisory > LLM)" {
    # Decision 3: planner advisory > LLM assessment
    run grep -c "planner advisory 优先\|Decision 3.*Conflict 兜底" "$SKILL_FILE"
    [ "$status" -eq 0 ]
    [ "$output" -ge 1 ]
}

@test "rdd-builder SKILL.md: documents case 1 approve does NOT call LLM" {
    # Decision 1: case 1 不调 LLM (user explicit, no info gain)
    # Per ADR-0049: case 1 approve 不调 LLM is documented in 阶段 0.2 段 (case 2/3/4)
    run grep -c "case 1.*不调\|Case 1.*不调 LLM\|不调 LLM" "$SKILL_FILE"
    [ "$status" -eq 0 ]
    [ "$output" -ge 1 ]
}


# --- schema assertions ---

@test "builder_handoff_schema.json: approval_status enum includes dispatched_to_quick (bug fix per ADR-0049)" {
    run python3 -c "
import json
with open('$SCHEMA_FILE') as f:
    s = json.load(f)
enum = s['properties']['approval_status']['enum']
assert 'dispatched_to_quick' in enum, f'dispatched_to_quick missing from {enum}'
print('OK:', enum)
"
    [ "$status" -eq 0 ]
    echo "$output"
}

@test "builder_handoff_schema.json: dispatch_quick_review field defined (new per ADR-0049)" {
    run python3 -c "
import json
with open('$SCHEMA_FILE') as f:
    s = json.load(f)
review = s['properties'].get('dispatch_quick_review')
assert review is not None, 'dispatch_quick_review missing'
fields = list(review['properties'].keys())
assert 'complexity_confirmed' in fields
assert 'concerns' in fields
assert 'suggested_action' in fields
assert 'reviewed_at' in fields
print('OK:', fields)
"
    [ "$status" -eq 0 ]
    echo "$output"
}


# --- _lib/builder_handoff.py assertions ---

@test "_lib/builder_handoff.py: write_builder_handoff accepts dispatch_quick_review kwarg" {
    run grep -c "def write_builder_handoff" "$BUILDER_HANDOFF_LIB"
    [ "$status" -eq 0 ]
    [ "$output" -ge 1 ]

    run grep -c "dispatch_quick_review=None" "$BUILDER_HANDOFF_LIB"
    [ "$status" -eq 0 ]
    [ "$output" -ge 1 ]

    run grep -c "_validate_dispatch_quick_review" "$BUILDER_HANDOFF_LIB"
    [ "$status" -eq 0 ]
    [ "$output" -ge 1 ]
}


# --- phase0_approval.sh behavioral assertions ---

@test "phase0_approval.sh case 5: reads dispatch_quick_review from builder-handoff" {
    write_builder_handoff "complex" "escalate" '["touches _lib/core/"]'
    write_planner_handoff "simple"

    run_phase0 test-change --dispatch-quick
    [ "$status" -eq 0 ]
    [[ "$output" == *"LLM hidden complexity check detected 'complex'"* ]]
    [[ "$output" == *"DISPATCH_TO_QUICK=1"* ]]
}

@test "phase0_approval.sh case 5: emits LLM signal in rdd-quick-context.json" {
    write_builder_handoff "complex" "escalate" '["data migration"]'
    write_planner_handoff "simple"

    run_phase0 test-change --dispatch-quick
    [ "$status" -eq 0 ]
    [ -f .rddf/state/rdd-quick-context.json ]

    run python3 -c "
import json
with open('.rddf/state/rdd-quick-context.json') as f:
    ctx = json.load(f)
llm = ctx.get('llm_advisory', {})
assert llm.get('complexity_confirmed') == 'complex', f'got {llm}'
assert 'data migration' in llm.get('concerns', ''), f'concerns missing: {llm}'
print('OK: llm_advisory =', llm)
"
    [ "$status" -eq 0 ]
    echo "$output"
}

@test "phase0_approval.sh case 5: HARD pause unchanged (--dispatch-quick still hard-validates recommended_route=simple)" {
    write_planner_handoff "complex"

    run_phase0 test-change --dispatch-quick
    # Exit 2: pre-condition fail (per ADR-0048, unchanged)
    [ "$status" -eq 2 ]
    [[ "$output" == *"requires recommended_route=simple"* ]]
}

@test "phase0_approval.sh case 5: simple LLM review (no warning emitted)" {
    write_builder_handoff "simple" "proceed" '[]'
    write_planner_handoff "simple"

    run_phase0 test-change --dispatch-quick
    [ "$status" -eq 0 ]
    [[ "$output" != *"LLM hidden complexity check"* ]]
    [[ "$output" == *"DISPATCH_TO_QUICK=1"* ]]
}

@test "phase0_approval.sh case 5: backward compat when dispatch_quick_review absent" {
    write_builder_handoff  # no complexity arg → no review field
    write_planner_handoff "simple"

    run_phase0 test-change --dispatch-quick
    [ "$status" -eq 0 ]
    [[ "$output" == *"DISPATCH_TO_QUICK=1"* ]]

    run python3 -c "
import json
with open('.rddf/state/rdd-quick-context.json') as f:
    ctx = json.load(f)
llm = ctx.get('llm_advisory', {})
assert llm.get('complexity_confirmed') == 'unset', f'got {llm}'
print('OK: backward compat llm_advisory =', llm)
"
    [ "$status" -eq 0 ]
    echo "$output"
}
