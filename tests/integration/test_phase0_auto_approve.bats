#!/usr/bin/env bats
# tests/integration/test_phase0_auto_approve.bats
# Verify --auto-approve flag on phase0_approval.sh skips interactive prompt.

load ../test_helper

setup() {
    FAKE_ROOT="$BATS_TEST_TMPDIR/fake-p0"
    mkdir -p "$FAKE_ROOT/openspec/changes"
    git -C "$FAKE_ROOT" init -q -b main
    git -C "$FAKE_ROOT" config user.email "e2e@test.local"
    git -C "$FAKE_ROOT" config user.name "e2e"
}

@test "phase0_approval.sh: --auto-approve exits without TTY hang" {
    run timeout 10 env PROJECT_ROOT="$FAKE_ROOT" \
        bash "$REPO_ROOT/skills/rdd-builder/scripts/phase0_approval.sh" \
        "test-change" --auto-approve
    # 124 = timeout (TTY hang). Anything else means prompt was bypassed.
    [ "$status" -ne 124 ]
}

@test "phase0_approval.sh: --auto-approve chooses approve branch and writes D3 spec-delta" {
    run timeout 10 env PROJECT_ROOT="$FAKE_ROOT" \
        bash "$REPO_ROOT/skills/rdd-builder/scripts/phase0_approval.sh" \
        "test-change" --auto-approve
    [ "$status" -eq 0 ]
    [ -f "$FAKE_ROOT/openspec/specs/test-change/spec.md" ]
    grep -q "## ADDED Requirements" "$FAKE_ROOT/openspec/specs/test-change/spec.md"
}
