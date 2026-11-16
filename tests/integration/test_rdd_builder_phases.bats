#!/usr/bin/env bats
# tests/integration/test_rdd_builder_phases.bats
#
# Integration tests for skills/rdd-builder/scripts/phase*.sh (per spec §3.4).
# Covers all 6 phase scripts: phase0_approval, phase1_plan, phase1_5_deps,
# phase2_execute, phase2_5_review, phase3_archive.
#
# Per Wave 1 plan §7 ≥21 bats integration test target.

load ../test_helper

setup() {
    TEST_TMP=$(mktemp -d)
    cd "$TEST_TMP"
    mkdir -p openspec/changes/test-change
    echo "# proposal" > openspec/changes/test-change/proposal.md
    mkdir -p .rddf/state
}

teardown() {
    rm -rf "$TEST_TMP"
}

# ---------------------------------------------------------------------------
# File existence + executability (6 tests)
# ---------------------------------------------------------------------------

@test "phase0_approval.sh: exists and is executable" {
    [ -f "$REPO_ROOT/skills/rdd-builder/scripts/phase0_approval.sh" ]
    [ -x "$REPO_ROOT/skills/rdd-builder/scripts/phase0_approval.sh" ]
}

@test "phase1_plan.sh: exists and is executable" {
    [ -f "$REPO_ROOT/skills/rdd-builder/scripts/phase1_plan.sh" ]
    [ -x "$REPO_ROOT/skills/rdd-builder/scripts/phase1_plan.sh" ]
}

@test "phase1_5_deps.sh: exists and is executable" {
    [ -f "$REPO_ROOT/skills/rdd-builder/scripts/phase1_5_deps.sh" ]
    [ -x "$REPO_ROOT/skills/rdd-builder/scripts/phase1_5_deps.sh" ]
}

@test "phase2_execute.sh: exists and is executable" {
    [ -f "$REPO_ROOT/skills/rdd-builder/scripts/phase2_execute.sh" ]
    [ -x "$REPO_ROOT/skills/rdd-builder/scripts/phase2_execute.sh" ]
}

@test "phase2_5_review.sh: exists and is executable" {
    [ -f "$REPO_ROOT/skills/rdd-builder/scripts/phase2_5_review.sh" ]
    [ -x "$REPO_ROOT/skills/rdd-builder/scripts/phase2_5_review.sh" ]
}

@test "phase3_archive.sh: exists and is executable" {
    [ -f "$REPO_ROOT/skills/rdd-builder/scripts/phase3_archive.sh" ]
    [ -x "$REPO_ROOT/skills/rdd-builder/scripts/phase3_archive.sh" ]
}

# ---------------------------------------------------------------------------
# Argument validation (4 tests)
# ---------------------------------------------------------------------------

@test "phase0: missing CHANGE_NAME exits non-zero" {
    run bash "$REPO_ROOT/skills/rdd-builder/scripts/phase0_approval.sh"
    [ "$status" -ne 0 ]
}

@test "phase1: missing CHANGE_NAME exits non-zero" {
    run bash "$REPO_ROOT/skills/rdd-builder/scripts/phase1_plan.sh"
    [ "$status" -ne 0 ]
}

@test "phase1_5: missing CHANGE_NAME exits non-zero" {
    run bash "$REPO_ROOT/skills/rdd-builder/scripts/phase1_5_deps.sh"
    [ "$status" -ne 0 ]
}

@test "phase3: missing CHANGE_NAME exits non-zero" {
    run bash "$REPO_ROOT/skills/rdd-builder/scripts/phase3_archive.sh"
    [ "$status" -ne 0 ]
}

# ---------------------------------------------------------------------------
# phase0_approval behavior (4 tests)
# ---------------------------------------------------------------------------

@test "phase0: approve writes the D3 spec-delta (per ADR-0025)" {
    # Run in a temp project root: phase0 writes into $PROJECT_ROOT (proposal,
    # spec-delta, builder handoff) and now also registers the change in
    # iteration.json — running it against the repository itself would pollute
    # the repo's .rddf/state/iteration.json.
    local tmp_root="$BATS_TMPDIR/p0-root"
    mkdir -p "$tmp_root/openspec/changes/test-change" "$tmp_root/.rddf/state" \
             "$tmp_root/.rddf/improvements"
    printf '# proposal\n' > "$tmp_root/openspec/changes/test-change/proposal.md"
    # the delta is only generated when the improvement draft exists
    cat > "$tmp_root/.rddf/improvements/test-change.md" <<'IMPROVEMENT'
---
name: test-change
priority: P1
status: pending
---

# test-change

## 架构依据
test fixture

## 范围
- In Scope: fixture

## Why
test fixture

## What Changes
test fixture

## Acceptance
- [ ] fixture acceptance item

## Capabilities
- MUST fixture

## Impact
none
IMPROVEMENT
    echo "1" | env PROJECT_ROOT="$tmp_root" \
        bash "$REPO_ROOT/skills/rdd-builder/scripts/phase0_approval.sh" "test-change"
    [ -f "$tmp_root/openspec/changes/test-change/specs/test-change/spec.md" ]
}

@test "phase0: running the phases suite leaves the repo's iteration.json untouched" {
    # The suite runs phase0 against a temp root; the repository's own
    # .rddf/state/iteration.json must not gain a "test-change" entry.
    run python3 -c "
import json, os
p = '$REPO_ROOT/.rddf/state/iteration.json'
if not os.path.isfile(p):
    print('clean')          # no state file at all — nothing to pollute
    raise SystemExit(0)
d = json.load(open(p))
names = [c.get('name') for c in d.get('changes', [])]
assert 'test-change' not in names, names
print('clean')"
    [ "$status" -eq 0 ]
}

@test "phase0: invalid choice (6) exits non-zero" {
    # Per ADR-0048: case 5 (dispatch-quick) is now valid; use 6 as invalid choice.
    run env -u PROJECT_ROOT bash -c "echo '6' | bash '$REPO_ROOT/skills/rdd-builder/scripts/phase0_approval.sh' test-change --require-confirm"
    [ "$status" -ne 0 ]
}

@test "rdd-builder: scripts dir contains exactly 6 phase scripts" {
    local count
    count=$(ls -1 "$REPO_ROOT/skills/rdd-builder/scripts/" | grep -c "^phase[0-9]")
    [ "$count" -eq 6 ]
}

@test "rdd-builder: phase script naming follows phase{N}_{name}.sh convention" {
    local files=(
        phase0_approval.sh
        phase1_plan.sh
        phase1_5_deps.sh
        phase2_execute.sh
        phase2_5_review.sh
        phase3_archive.sh
    )
    for f in "${files[@]}"; do
        [ -f "$REPO_ROOT/skills/rdd-builder/scripts/$f" ]
    done
}

@test "rdd-builder: SKILL.md references all 6 phases by symbol (P0-P3)" {
    grep -qE "P0|Phase 0|approval" "$REPO_ROOT/skills/rdd-builder/SKILL.md"
    grep -qE "P1|Phase 1|plan" "$REPO_ROOT/skills/rdd-builder/SKILL.md"
    grep -qE "P1\.5|deps" "$REPO_ROOT/skills/rdd-builder/SKILL.md"
    grep -qE "P2|Phase 2|execute" "$REPO_ROOT/skills/rdd-builder/SKILL.md"
    grep -qE "P2\.5|review" "$REPO_ROOT/skills/rdd-builder/SKILL.md"
    grep -qE "P3|Phase 3|archive" "$REPO_ROOT/skills/rdd-builder/SKILL.md"
}

@test "rdd-builder: SKILL.md has role: frontmatter (per ADR-0028)" {
    grep -q "^role:" "$REPO_ROOT/skills/rdd-builder/SKILL.md"
    grep -q "title:" "$REPO_ROOT/skills/rdd-builder/SKILL.md"
    grep -q "perspective:" "$REPO_ROOT/skills/rdd-builder/SKILL.md"
    grep -q "boundaries:" "$REPO_ROOT/skills/rdd-builder/SKILL.md"
    grep -q "human_involvement:" "$REPO_ROOT/skills/rdd-builder/SKILL.md"
}

# ---------------------------------------------------------------------------
# Phase gap semantics (per spec §3.4) (3 tests)
# ---------------------------------------------------------------------------

@test "phase1.5 deps: file naming uses underscore not dot (phase1_5_deps.sh)" {
    [ -f "$REPO_ROOT/skills/rdd-builder/scripts/phase1_5_deps.sh" ]
    ! [ -f "$REPO_ROOT/skills/rdd-builder/scripts/phase1.5_deps.sh" ]
}

@test "phase2.5 review: file naming uses underscore not dot (phase2_5_review.sh)" {
    [ -f "$REPO_ROOT/skills/rdd-builder/scripts/phase2_5_review.sh" ]
    ! [ -f "$REPO_ROOT/skills/rdd-builder/scripts/phase2.5_review.sh" ]
}

@test "rdd-builder scripts: none reference removed guide-* paths" {
    for f in "$REPO_ROOT/skills/rdd-builder/scripts/"phase*.sh; do
        ! grep -q "skills/guide-plan\|skills/guide-ship\|skills/guide-design\|skills/guide-arch" "$f"
    done
}
