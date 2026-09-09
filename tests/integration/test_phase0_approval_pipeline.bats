#!/usr/bin/env bats
# E2E: phase0_approval.sh --auto-approve produces a non-stub proposal.md
# from the linked .rddf/improvements/<name>.md 5-段 content.

setup() {
    BATS_TMPDIR="$(mktemp -d)"
    export BATS_TMPDIR
    mkdir -p "$BATS_TMPDIR/openspec/changes/fix-test-phase0"
    cat > "$BATS_TMPDIR/openspec/changes/fix-test-phase0/proposal.md" <<'EOF'
## Why

<skeleton motivation - 1-2 sentences>

## What Changes

- <file path or module affected>
EOF

    mkdir -p "$BATS_TMPDIR/.rddf/improvements"
    cat > "$BATS_TMPDIR/.rddf/improvements/fix-test-phase0.md" <<'EOF'
# fix-test-phase0

**优先级**: P1 | **来源**: e2e test

## Why

Real 5-段 motivation here.

## 范围

- Real item A
- Real item B

## Capabilities

- capability-test-e2e

## Impact

Real impact text.

## Acceptance

- AC-1: works
- AC-2: passes

## Reference

- ADR-9999
EOF

    cd "$BATS_TMPDIR"
}

teardown() {
    rm -rf "$BATS_TMPDIR"
}

@test "phase0_approval.sh --auto-approve populates proposal.md with full 5-段 content" {
    PROJECT_ROOT="$BATS_TMPDIR" \
    bash /workspace/project/rdd-workflow/skills/rdd-builder/scripts/phase0_approval.sh \
        fix-test-phase0 --auto-approve
    # Wait for completion
    [ "$?" -eq 0 ]
    # proposal.md should now have non-stub content
    run grep -c "<skeleton motivation>" "$BATS_TMPDIR/openspec/changes/fix-test-phase0/proposal.md"
    [ "$output" -eq 0 ]
    run grep -c "Real 5-段 motivation here" "$BATS_TMPDIR/openspec/changes/fix-test-phase0/proposal.md"
    [ "$output" -ge 1 ]
    run grep -c "## Acceptance" "$BATS_TMPDIR/openspec/changes/fix-test-phase0/proposal.md"
    [ "$output" -ge 1 ]
}
