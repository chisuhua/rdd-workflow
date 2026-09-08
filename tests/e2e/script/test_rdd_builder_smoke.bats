#!/usr/bin/env bats
# tests/e2e/script/test_rdd_builder_smoke.bats
# A-layer smoke for rdd-builder per 2026-09-08-rdd-builder-e2e-scenarios.md
# 6 cases: one per phase script (B-E1..B-E6 from spec, A-layer subset).
# Runs in <30s on CI.

load ../../test_helper

setup() {
    source "$REPO_ROOT/tests/e2e/_lib/isolation.bash"
    source "$REPO_ROOT/tests/e2e/_lib/script_smoke.bash"

    export SMOKE_FAKE_ROOT="$BATS_TEST_TMPDIR/fake-builder"
    export SMOKE_REPO_ROOT="$REPO_ROOT"
    script_smoke::setup_fake_project "$SMOKE_FAKE_ROOT"
    BASELINE_FILE="$BATS_TEST_TMPDIR/baseline.sha256"
    isolation::snapshot_repo_state "$BASELINE_FILE"
}

teardown() {
    script_smoke::cleanup_fake_project "$SMOKE_FAKE_ROOT"
    if ! isolation::verify_zero_pollution "$BASELINE_FILE"; then
        echo "POLLUTION DETECTED — see diff above" >&2
        return 1
    fi
}

@test "rdd-builder A1: phase0_approval.sh --auto-approve handles non-interactive (B-E1 subset)" {
    mkdir -p "$SMOKE_FAKE_ROOT/openspec/changes/b-e1"
    cat > "$SMOKE_FAKE_ROOT/openspec/changes/b-e1/proposal.md" <<EOF
# Proposal b-e1
## Why
Test.
## What Changes
- Add test
## Capabilities
- capability-1
## Acceptance
- [ ] AC-1: pass
EOF
    git -C "$SMOKE_FAKE_ROOT" add -A && git -C "$SMOKE_FAKE_ROOT" commit -q -m "init b-e1" 2>/dev/null || true
    run timeout 10 env PROJECT_ROOT="$SMOKE_FAKE_ROOT" \
        bash "$SMOKE_REPO_ROOT/skills/rdd-builder/scripts/phase0_approval.sh" \
        "b-e1" --auto-approve
    [ "$status" -ne 124 ]
}

@test "rdd-builder A2: phase1_plan.sh --auto-approve runs without TTY hang (B-E3 subset)" {
    run timeout 10 env PROJECT_ROOT="$SMOKE_FAKE_ROOT" \
        bash "$SMOKE_REPO_ROOT/skills/rdd-builder/scripts/phase1_plan.sh" \
        "b-e2" --auto-approve
    [ "$status" -ne 124 ]
}

@test "rdd-builder A3: phase1_5_deps.sh --auto-approve runs without TTY hang (B-E4 subset)" {
    run timeout 10 env PROJECT_ROOT="$SMOKE_FAKE_ROOT" \
        bash "$SMOKE_REPO_ROOT/skills/rdd-builder/scripts/phase1_5_deps.sh" \
        "b-e3" --auto-approve
    [ "$status" -ne 124 ]
}

@test "rdd-builder A4: phase2_execute.sh --auto-approve runs without TTY hang (B-E6 subset)" {
    run timeout 10 env PROJECT_ROOT="$SMOKE_FAKE_ROOT" \
        bash "$SMOKE_REPO_ROOT/skills/rdd-builder/scripts/phase2_execute.sh" \
        "b-e4" --auto-approve
    [ "$status" -ne 124 ]
}

@test "rdd-builder A5: phase2_5_review.sh --auto-approve runs without TTY hang (B-E8 subset)" {
    run timeout 10 env PROJECT_ROOT="$SMOKE_FAKE_ROOT" \
        bash "$SMOKE_REPO_ROOT/skills/rdd-builder/scripts/phase2_5_review.sh" \
        "b-e5" --auto-approve
    [ "$status" -ne 124 ]
}

@test "rdd-builder A6: phase3_archive.sh --auto-approve handles missing change gracefully" {
    run timeout 10 env PROJECT_ROOT="$SMOKE_FAKE_ROOT" \
        bash "$SMOKE_REPO_ROOT/skills/rdd-builder/scripts/phase3_archive.sh" \
        "nonexistent" --auto-approve
    [ "$status" -ne 124 ]
}
