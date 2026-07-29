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

# ── Task 2: Archive-then-recheck scenarios ──

@test "plan_done_gate_zero: archive 2 of 3 changes -> Gate 0 shows 1" {
    for n in test-a test-b test-c; do
        mkdir -p "openspec/changes/$n"
        echo "test" > "openspec/changes/$n/proposal.md"
    done

    # Archive 2 of them (move to archive/ subdirectory)
    mkdir -p openspec/changes/archive/2026-07-29-test-a
    mkdir -p openspec/changes/archive/2026-07-29-test-b
    mv openspec/changes/test-a openspec/changes/archive/2026-07-29-test-a/test-a
    mv openspec/changes/test-b openspec/changes/archive/2026-07-29-test-b/test-b

    run bash -c "
        source '$REPO_ROOT/skills/guide-plan/scripts/plan_done_gate.sh'
        run_plan_done_gate 2>&1 | grep 'ready-for-ship' || true
    "
    [[ "$output" == *"cleared): 1"* ]]
}

@test "plan_done_gate_zero: all archived -> Gate 0 returns 0" {
    # Create one change, then archive it
    mkdir -p openspec/changes/test-only
    echo "test" > "openspec/changes/test-only/proposal.md"
    mkdir -p openspec/changes/archive/2026-07-29-test-only
    mv openspec/changes/test-only openspec/changes/archive/2026-07-29-test-only/test-only

    run bash -c "
        source '$REPO_ROOT/skills/guide-plan/scripts/plan_done_gate.sh'
        run_plan_done_gate 2>&1 | grep 'ready-for-ship' || true
    "
    [[ "$output" == *"cleared): 0"* ]]
}

# ── Task 3: Full create->archive->recheck integration test ──

@test "plan_done_gate_zero: integration - full create->archive->recheck" {
    # Create 2 changes
    for n in change-a change-b; do
        mkdir -p "openspec/changes/$n"
        echo "x" > "openspec/changes/$n/proposal.md"
    done

    # First check: count is 2
    out1=$(bash -c "
        source '$REPO_ROOT/skills/guide-plan/scripts/plan_done_gate.sh'
        run_plan_done_gate 2>&1 | grep 'ready-for-ship' || true
    ")
    [[ "$out1" == *"cleared): 2"* ]]

    # Archive one
    mkdir -p openspec/changes/archive/2026-07-29-change-a
    mv openspec/changes/change-a openspec/changes/archive/2026-07-29-change-a/change-a

    # Second check: count should be 1
    out2=$(bash -c "
        source '$REPO_ROOT/skills/guide-plan/scripts/plan_done_gate.sh'
        run_plan_done_gate 2>&1 | grep 'ready-for-ship' || true
    ")
    [[ "$out2" == *"cleared): 1"* ]]
}
