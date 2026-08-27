load ../test_helper

setup() {
    TEST_REPO="$BATS_TMPDIR/test-design-approve-batch"
    rm -rf "$TEST_REPO"
    mkdir -p "$TEST_REPO/.rddf/improvements"
    cd "$TEST_REPO"
    git init -q
    git config user.email "t@t"
    git config user.name "t"
    git checkout -q -b main
    mkdir -p openspec/changes

    write_improvement() {
        local name="$1"
        cat > ".rddf/improvements/$name.md" <<EOF
# $name

**优先级**: P1 | test | 2026-08-27 | test

## 架构依据

test.

## 范围

- test

## Capabilities

- MUST: test

## Impact

- test

## 验收

- [ ] test
EOF
    }
    write_improvement "alpha"
    write_improvement "beta"
    write_improvement "gamma"
    SCRIPT="$PROJECT_ROOT/skills/guide-design/scripts/design_approve_batch.sh"
}

teardown() {
    rm -rf "$TEST_REPO"
    rm -rf /tmp/proposal-drafts
}

@test "design_approve_batch: dry-run generates drafts without approving" {
    PROJECT_ROOT="$TEST_REPO" run bash "$SCRIPT" alpha --dry-run
    [ "$status" -eq 0 ]
    [[ "$output" =~ "[DRY-RUN]" ]]
    [[ "$output" =~ "alpha" ]]
    [ -f /tmp/proposal-drafts/alpha.md ]
    [ ! -d "$TEST_REPO/openspec/changes/alpha" ]
}

@test "design_approve_batch: skips already-created changes (idempotent)" {
    mkdir -p "$TEST_REPO/openspec/changes/alpha"
    PROJECT_ROOT="$TEST_REPO" run bash "$SCRIPT" alpha beta --dry-run
    [ "$status" -eq 0 ]
    [[ "$output" =~ "skipped (already created)" ]]
    [[ "$output" =~ "alpha" ]]
}

@test "design_approve_batch: missing improvement file errors" {
    PROJECT_ROOT="$TEST_REPO" run bash "$SCRIPT" nonexistent --dry-run
    [ "$status" -ne 0 ]
    [[ "$output" =~ "failed to generate" ]]
}

@test "design_approve_batch: no changes specified errors" {
    PROJECT_ROOT="$TEST_REPO" run bash "$SCRIPT"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "no changes specified" ]]
}

@test "design_approve_batch: --changes flag accepts comma-separated list" {
    PROJECT_ROOT="$TEST_REPO" run bash "$SCRIPT" --changes alpha,beta --dry-run
    [ "$status" -eq 0 ]
    [[ "$output" =~ "alpha" ]]
    [[ "$output" =~ "beta" ]]
    [ -f /tmp/proposal-drafts/alpha.md ]
    [ -f /tmp/proposal-drafts/beta.md ]
}

@test "design_approve_batch: positional args also work" {
    PROJECT_ROOT="$TEST_REPO" run bash "$SCRIPT" alpha beta --dry-run
    [ "$status" -eq 0 ]
    [[ "$output" =~ "alpha" ]]
    [[ "$output" =~ "beta" ]]
}