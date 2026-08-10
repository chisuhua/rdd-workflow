#!/usr/bin/env bats
# tests/integration/test_wire_design_content_review_gate.bats
#
# Integration test for wire-design-content-review-gate (Group 4 / 6).
# Verifies the single-item and batch approve paths route through the
# shared content-review helper (run_content_review.sh), honoring
# STRICT_DESIGN_GATE and SKIP_CONTENT_REVIEW escape hatch.
#
# Per design decision 1 of the change:
#   "Both single-item approve and batch approve funnel through the same
#    internal helper that invokes design_content_review.sh. We do not
#    maintain two parallel review-call code paths."

setup() {
    REPO_ROOT="$(git rev-parse --show-toplevel)"
    cd "$REPO_ROOT"
    BATS_TMPDIR="$(mktemp -d)"
    export BATS_TMPDIR
}

teardown() {
    [ -n "$BATS_TMPDIR" ] && rm -rf "$BATS_TMPDIR"
}

# --- Helpers ---

write_clean_improvement() {
    local f="$1"
    cat > "$f" <<'EOF'
**阶段**: design
**分类**: core
**类型**: feature

## 架构依据
ADR-0003 establishes the three-phase architecture.

## 范围
Wire existing review into approve flow.

## 关键场景
Single and batch approve routes through the same helper.

## 技术约束
Bash 4.0+.

## 验收标准
- [ ] Helper invoked on single approve
- [ ] Helper invoked per-item in batch
- [ ] STRICT_DESIGN_GATE honors blocking
- [ ] SKIP_CONTENT_REVIEW escapes cleanly
EOF
}

write_broken_improvement() {
    local f="$1"
    cat > "$f" <<'EOF'
Some free-form content with no ADR reference and no required sections.
EOF
}

# --- 6.1: Single approve invokes review.sh when SKIP unset ---

@test "single approve invokes design_content_review.sh when SKIP_CONTENT_REVIEW is unset" {
    local imp="$BATS_TMPDIR/single-clean.md"
    write_clean_improvement "$imp"
    export IMPROVEMENTS_PATH="$imp"
    unset SKIP_CONTENT_REVIEW
    unset STRICT_DESIGN_GATE

    run bash "$REPO_ROOT/skills/guide-design/scripts/run_content_review.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"improvements content review: OK"* ]]
    unset IMPROVEMENTS_PATH
}

# --- 6.2: Default-mode review warning allows approve to complete ---

@test "default-mode review with structural errors prints warning but exits 0 (warn-allow)" {
    local imp="$BATS_TMPDIR/single-broken.md"
    write_broken_improvement "$imp"
    export IMPROVEMENTS_PATH="$imp"
    unset STRICT_DESIGN_GATE
    unset SKIP_CONTENT_REVIEW

    run bash "$REPO_ROOT/skills/guide-design/scripts/run_content_review.sh"
    # Default mode: review emits warnings to stderr but exits 0 (warn-allow).
    [ "$status" -eq 0 ]
    [[ "$output" == *"WARNING"* ]] || [[ "$output" == *"missing"* ]]
    unset IMPROVEMENTS_PATH
}

# --- 6.3: STRICT_DESIGN_GATE=yes upgrades warnings to blocking ---

@test "STRICT_DESIGN_GATE=yes upgrades review warnings to blocking exit 1" {
    local imp="$BATS_TMPDIR/single-broken-strict.md"
    write_broken_improvement "$imp"
    export IMPROVEMENTS_PATH="$imp"
    export STRICT_DESIGN_GATE="yes"
    unset SKIP_CONTENT_REVIEW

    run bash "$REPO_ROOT/skills/guide-design/scripts/run_content_review.sh"
    [ "$status" -eq 1 ]
    [[ "$output" == *"STRICT_DESIGN_GATE"* ]] || [[ "$output" == *"blocking"* ]]
    unset IMPROVEMENTS_PATH STRICT_DESIGN_GATE
}

# --- 6.4: SKIP_CONTENT_REVIEW=yes skips review without affecting other approve semantics ---

@test "SKIP_CONTENT_REVIEW=yes short-circuits the helper without invoking design_content_review.sh" {
    local imp="$BATS_TMPDIR/single-skip.md"
    write_clean_improvement "$imp"
    export IMPROVEMENTS_PATH="$imp"
    export SKIP_CONTENT_REVIEW="yes"

    run bash "$REPO_ROOT/skills/guide-design/scripts/run_content_review.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"review skipped"* ]]
    # The natural review output should NOT appear (script never ran).
    [[ "$output" != *"improvements content review: OK"* ]]
    unset IMPROVEMENTS_PATH SKIP_CONTENT_REVIEW
}

# --- 6.5: Batch approve invokes review per-item (mock-level check) ---

@test "batch approve invokes the helper once per improvement" {
    # This test exercises the helper, not the full approve flow, because
    # the full approve flow requires interactive input. The helper is
    # the single shared review-call path that batch and single approve
    # both funnel through (per design decision 1).
    local imp_a="$BATS_TMPDIR/batch-a.md"
    local imp_b="$BATS_TMPDIR/batch-b.md"
    write_clean_improvement "$imp_a"
    write_clean_improvement "$imp_b"

    # Helper invocation 1
    export IMPROVEMENTS_PATH="$imp_a"
    unset SKIP_CONTENT_REVIEW
    unset STRICT_DESIGN_GATE
    run bash "$REPO_ROOT/skills/guide-design/scripts/run_content_review.sh"
    [ "$status" -eq 0 ]

    # Helper invocation 2 (proves per-item call)
    export IMPROVEMENTS_PATH="$imp_b"
    run bash "$REPO_ROOT/skills/guide-design/scripts/run_content_review.sh"
    [ "$status" -eq 0 ]
    unset IMPROVEMENTS_PATH
}

# --- Static check: approve_proposal.sh references the helper, not duplicated check logic ---

@test "approve_proposal.sh invokes run_content_review.sh (no duplicated review logic)" {
    grep -q "run_content_review.sh" "$REPO_ROOT/skills/guide-design/scripts/approve_proposal.sh"
}

@test "approve_proposal.sh does NOT call design_content_review.py directly" {
    # Per design decision 1: "MUST NOT copy design_content_review.py's check logic"
    # Direct .py calls would bypass the wrapper and SKIP/STRICT semantics.
    if grep -q "design_content_review\.py" "$REPO_ROOT/skills/guide-design/scripts/approve_proposal.sh"; then
        # Allow only via the helper path or env-var handoff
        ! grep -E "(python3|python)\s+.*design_content_review\.py" "$REPO_ROOT/skills/guide-design/scripts/approve_proposal.sh"
    fi
}

# --- Helper contract tests ---

@test "run_content_review.sh exits 2 when IMPROVEMENTS_PATH is missing" {
    unset IMPROVEMENTS_PATH
    unset SKIP_CONTENT_REVIEW
    unset STRICT_DESIGN_GATE

    run bash "$REPO_ROOT/skills/guide-design/scripts/run_content_review.sh"
    [ "$status" -eq 2 ]
    [[ "$output" == *"IMPROVEMENTS_PATH not set"* ]]
}

@test "run_content_review.sh exits 2 when IMPROVEMENTS_PATH points to nonexistent file" {
    export IMPROVEMENTS_PATH="$BATS_TMPDIR/does-not-exist.md"
    unset SKIP_CONTENT_REVIEW
    unset STRICT_DESIGN_GATE

    run bash "$REPO_ROOT/skills/guide-design/scripts/run_content_review.sh"
    [ "$status" -eq 2 ]
    [[ "$output" == *"not found"* ]]
    unset IMPROVEMENTS_PATH
}

@test "run_content_review.sh propagates review exit codes unchanged" {
    # Default mode: review of broken content exits 0 (warning).
    local imp="$BATS_TMPDIR/propagate-default.md"
    write_broken_improvement "$imp"
    export IMPROVEMENTS_PATH="$imp"
    unset STRICT_DESIGN_GATE
    unset SKIP_CONTENT_REVIEW

    run bash "$REPO_ROOT/skills/guide-design/scripts/run_content_review.sh"
    [ "$status" -eq 0 ]

    # Strict mode: same content exits 1 (blocking).
    export STRICT_DESIGN_GATE="yes"
    run bash "$REPO_ROOT/skills/guide-design/scripts/run_content_review.sh"
    [ "$status" -eq 1 ]

    unset IMPROVEMENTS_PATH STRICT_DESIGN_GATE
}

@test "run_content_review.sh echo's SKIP marker distinguishable from PASS" {
    local imp="$BATS_TMPDIR/skip-marker.md"
    write_clean_improvement "$imp"

    # PASS path
    export IMPROVEMENTS_PATH="$imp"
    unset SKIP_CONTENT_REVIEW
    run bash "$REPO_ROOT/skills/guide-design/scripts/run_content_review.sh"
    pass_output="$output"
    [[ "$pass_output" != *"review skipped"* ]]

    # SKIP path
    export SKIP_CONTENT_REVIEW="yes"
    run bash "$REPO_ROOT/skills/guide-design/scripts/run_content_review.sh"
    skip_output="$output"
    [[ "$skip_output" == *"review skipped"* ]]

    unset IMPROVEMENTS_PATH SKIP_CONTENT_REVIEW
}