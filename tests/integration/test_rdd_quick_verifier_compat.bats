#!/usr/bin/env bats
# tests/integration/test_rdd_quick_verifier_compat.bats
# Integration tests for skills/rdd-quick/scripts/sync_ac_to_proposal.py
# Per rdd-workflow v2.1 fix: rdd-quick mode a rdd-verifier compatibility.
#
# Coverage:
#  - script existence + executable
#  - appends ## Acceptance (from rdd-quick plan) segment with BEGIN/END markers
#  - AC items preserved verbatim from plan
#  - idempotent (second call replaces, not duplicates)
#  - exit codes (success / missing args)

load 'test_helper'

setup() {
    PROJECT_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
    SCRIPT="$PROJECT_ROOT/skills/rdd-quick/scripts/sync_ac_to_proposal.py"
    WORK_TMP="$(mktemp -d)"
    cat > "$WORK_TMP/proposal.md" <<'PROPOSAL'
# Test Proposal
## Why
Test
## What Changes
Test content here
PROPOSAL
    cat > "$WORK_TMP/plan.md" <<'PLAN'
# Test Plan
**Goal:** Test goal
## Acceptance
- [ ] **AC-1** First acceptance criterion with detail
- [ ] **AC-2** Second acceptance criterion with detail
PLAN
}

teardown() {
    rm -rf "$WORK_TMP"
}

@test "verifier_compat: sync_ac_to_proposal.py script exists and is executable" {
    [ -x "$SCRIPT" ]
}

@test "verifier_compat: appends ## Acceptance (from rdd-quick plan) segment with markers" {
    cd "$WORK_TMP"
    python3 "$SCRIPT" --plan plan.md --proposal proposal.md
    [ "$(grep -c '## Acceptance (from rdd-quick plan)' proposal.md)" = "1" ]
    [ "$(grep -c '<!-- BEGIN rdd-quick-ac -->' proposal.md)" = "1" ]
    [ "$(grep -c '<!-- END rdd-quick-ac -->' proposal.md)" = "1" ]
}

@test "verifier_compat: AC items preserved verbatim from plan" {
    cd "$WORK_TMP"
    python3 "$SCRIPT" --plan plan.md --proposal proposal.md
    grep -qE '\- \[ \] \*\*AC-1\*\* First acceptance criterion with detail' proposal.md
    grep -qE '\- \[ \] \*\*AC-2\*\* Second acceptance criterion with detail' proposal.md
}

@test "verifier_compat: idempotent — second call replaces AC segment, not duplicate" {
    cd "$WORK_TMP"
    python3 "$SCRIPT" --plan plan.md --proposal proposal.md
    python3 "$SCRIPT" --plan plan.md --proposal proposal.md
    # Only one BEGIN/END pair
    [ "$(grep -c '<!-- BEGIN rdd-quick-ac -->' proposal.md)" = "1" ]
    [ "$(grep -c '<!-- END rdd-quick-ac -->' proposal.md)" = "1" ]
    [ "$(grep -c '## Acceptance (from rdd-quick plan)' proposal.md)" = "1" ]
}

@test "verifier_compat: preserves existing proposal.md content before append" {
    cd "$WORK_TMP"
    python3 "$SCRIPT" --plan plan.md --proposal proposal.md
    grep -q "^## Why" proposal.md
    grep -q "^## What Changes" proposal.md
    grep -q "Test content here" proposal.md
}

@test "verifier_compat: exit code 0 on success, non-zero on missing args" {
    run python3 "$SCRIPT"
    [ "$status" != "0" ]
    cd "$WORK_TMP"
    python3 "$SCRIPT" --plan plan.md --proposal proposal.md
    [ "$?" = "0" ]
}