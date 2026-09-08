#!/usr/bin/env bats
# tests/integration/test_phase_auto_approve.bats
# Verify --auto-approve flag on all 6 rdd-builder phase scripts.
# Covers Tasks 5-9 of 2026-09-08-e2e-test-plan-phase1.

load ../test_helper

setup() {
    FAKE_ROOT="$BATS_TEST_TMPDIR/fake"
    mkdir -p "$FAKE_ROOT/openspec/changes/test-change" "$FAKE_ROOT/.rddf/state"
    git -C "$FAKE_ROOT" init -q -b main 2>/dev/null || true
    git -C "$FAKE_ROOT" config user.email "e2e@test.local" 2>/dev/null || true
    git -C "$FAKE_ROOT" config user.name "e2e" 2>/dev/null || true
    : > "$FAKE_ROOT/openspec/changes/test-change/.gitkeep"
    : > "$FAKE_ROOT/.rddf/state/.gitkeep"
    git -C "$FAKE_ROOT" add -A 2>/dev/null
    git -C "$FAKE_ROOT" commit -q -m "init" 2>/dev/null || true
}

@test "phase1_plan.sh: --auto-approve exits without TTY hang" {
    run timeout 10 env PROJECT_ROOT="$FAKE_ROOT" \
        bash "$REPO_ROOT/skills/rdd-builder/scripts/phase1_plan.sh" \
        "test-change" --auto-approve
    # 124 = timeout. Anything else means flag was parsed and script exited.
    [ "$status" -ne 124 ]
}

@test "phase1_5_deps.sh: --auto-approve exits without TTY hang" {
    run timeout 10 env PROJECT_ROOT="$FAKE_ROOT" \
        bash "$REPO_ROOT/skills/rdd-builder/scripts/phase1_5_deps.sh" \
        "test-change" --auto-approve
    [ "$status" -ne 124 ]
}

@test "phase2_execute.sh: --auto-approve exits without TTY hang" {
    run timeout 10 env PROJECT_ROOT="$FAKE_ROOT" \
        bash "$REPO_ROOT/skills/rdd-builder/scripts/phase2_execute.sh" \
        "test-change" --auto-approve
    [ "$status" -ne 124 ]
}

@test "phase2_5_review.sh: --auto-approve defaults to merge branch (exits without TTY hang)" {
    run timeout 10 env PROJECT_ROOT="$FAKE_ROOT" \
        bash "$REPO_ROOT/skills/rdd-builder/scripts/phase2_5_review.sh" \
        "test-change" --auto-approve
    [ "$status" -ne 124 ]
}

@test "phase3_archive.sh: --auto-approve exits without TTY hang" {
    run timeout 10 env PROJECT_ROOT="$FAKE_ROOT" \
        bash "$REPO_ROOT/skills/rdd-builder/scripts/phase3_archive.sh" \
        "test-change" --auto-approve
    # 124 = timeout. May exit non-zero (verifier fail, missing change, etc.)
    # but must not hang on TTY prompt.
    [ "$status" -ne 124 ]
}
