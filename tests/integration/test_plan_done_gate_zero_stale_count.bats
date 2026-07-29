#!/usr/bin/env bats
# tests/integration/test_plan_done_gate_zero_stale_count.bats
# Regression: Gate 0 must read filesystem (openspec/changes/*/) not iteration.json
# to avoid stale count after archive operations.
#
# Task 1: Gate 0 reads filesystem not iteration.json
# Task 2: Archive-then-recheck scenarios
# Task 3: Full create->archive->recheck integration test

load ../test_helper

setup() {
    TEST_DIR=$(mktemp -d)
    cd "$TEST_DIR"
    git init -q
    git config user.email "t@t.com"
    git config user.name "T"
    touch README.md
    git add README.md
    git commit -q -m "init"
}

teardown() {
    [ -n "$TEST_DIR" ] && rm -rf "$TEST_DIR"
}

# ── Task 1: Gate 0 reads filesystem not iteration.json ──

@test "plan_done_gate_zero: Gate 0 reads filesystem not iteration.json" {
    # Create 3 active changes (no iteration.json exists)
    for n in test-a test-b test-c; do
        mkdir -p "openspec/changes/$n"
        echo "test" > "openspec/changes/$n/proposal.md"
    done

    # Run the gate - should count 3 from filesystem truth
    run bash -c "
        source '$REPO_ROOT/skills/guide-plan/scripts/plan_done_gate.sh'
        run_plan_done_gate 2>&1 | grep 'ready-for-ship' || true
    "
    [[ "$output" == *"cleared): 3"* ]]
}

@test "plan_done_gate_zero: empty openspec/changes/ returns 0" {
    mkdir -p openspec/changes/archive

    run bash -c "
        source '$REPO_ROOT/skills/guide-plan/scripts/plan_done_gate.sh'
        run_plan_done_gate 2>&1 | grep 'ready-for-ship' || true
    "
    [[ "$output" == *"cleared): 0"* ]]
}
