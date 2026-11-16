#!/usr/bin/env bats
# tests/integration/test_phase0_auto_approve.bats
# Verify --auto-approve flag on phase0_approval.sh skips interactive prompt.

load ../test_helper

setup() {
    FAKE_ROOT="$BATS_TEST_TMPDIR/fake-p0"
    mkdir -p "$FAKE_ROOT/openspec/changes" "$FAKE_ROOT/.rddf/improvements"
    git -C "$FAKE_ROOT" init -q -b main
    git -C "$FAKE_ROOT" config user.email "e2e@test.local"
    git -C "$FAKE_ROOT" config user.name "e2e"
    # The D3 delta is generated FROM the improvement's 5 sections; without one
    # there is nothing to derive, and approving writes no delta (it must not
    # write a placeholder — see test below).
    cat > "$FAKE_ROOT/.rddf/improvements/test-change.md" <<'IMP'
# test-change

**优先级**: P2 | **阶段**: phase-4 | **分类**: governance | **类型**: improvement

## Capabilities

- MUST: the change does the thing

## Acceptance

- [ ] the thing is done
IMP
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
    # D3 delta is change-local: openspec/changes/<name>/specs/<name>/spec.md.
    # The main spec under openspec/specs/ is created at ARCHIVE time — writing a
    # placeholder at approve time adds one more spec whose "## Purpose" is a TBD
    # marker, and `openspec validate --strict` fails those.
    [ -f "$FAKE_ROOT/openspec/changes/test-change/specs/test-change/spec.md" ]
    grep -q "## ADDED Requirements" \
        "$FAKE_ROOT/openspec/changes/test-change/specs/test-change/spec.md"
    [ ! -e "$FAKE_ROOT/openspec/specs/test-change/spec.md" ]
}
