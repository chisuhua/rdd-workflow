#!/usr/bin/env bats
# tests/e2e/script/test_rdd_quick_smoke.bats
# A-layer smoke for rdd-quick per 2026-09-08-rdd-quick-e2e-scenarios.md
# 4 cases: scaffold + append_history + AC source + isolation.
# Runs in <5s on CI.

load ../../test_helper

setup() {
    source "$REPO_ROOT/tests/e2e/_lib/isolation.bash"
    source "$REPO_ROOT/tests/e2e/_lib/script_smoke.bash"
    source "$REPO_ROOT/tests/e2e/_lib/golden_compare.bash"

    export SMOKE_FAKE_ROOT="$BATS_TEST_TMPDIR/fake-quick"
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

@test "rdd-quick A1: scaffold_plan.sh --no-confirm creates quick-*.md with 5 TDD markers" {
    export RDDF_QUICK_PLAN_DIR="$SMOKE_FAKE_ROOT/.rddf/plans"
    mkdir -p "$RDDF_QUICK_PLAN_DIR"
    run bash "$REPO_ROOT/skills/rdd-quick/scripts/scaffold_plan.sh" \
        --name "smoke-test" --proposal "smoke test" --no-confirm
    [ "$status" -eq 0 ]
    [ -f "$RDDF_QUICK_PLAN_DIR/quick-smoke-test.md" ]
    grep -q "Step 1: Write the failing test" "$RDDF_QUICK_PLAN_DIR/quick-smoke-test.md"
    grep -q "Step 5: Defer commit" "$RDDF_QUICK_PLAN_DIR/quick-smoke-test.md"
}

@test "rdd-quick A2: append_history.py validates and appends to .quick-history.jsonl" {
    HIST="$SMOKE_FAKE_ROOT/.rddf/state/.quick-history.jsonl"
    mkdir -p "$(dirname "$HIST")"
    local entry='{"name":"quick-smoke","plan_file":".rddf/plans/quick-smoke.md","commit_sha":"abcdef0","started_at":"2026-09-08T00:00:00Z","ended_at":"2026-09-08T00:01:00Z","complexity":"simple","reviewed_by":[],"retry_count":0,"verdict_summary":{"total":1,"pass":1,"fail":0},"outcome":"completed","upgraded_to_change":null}'
    RDDF_QUICK_HISTORY_FILE="$HIST" run python3 "$REPO_ROOT/skills/rdd-quick/scripts/append_history.py" <<< "$entry"
    [ "$status" -eq 0 ]
    [ -f "$HIST" ]
    [ "$(wc -l < "$HIST")" -eq 1 ]
}

@test "rdd-quick A3: scaffold_plan.sh plan file contains ## Acceptance section with AC checkboxes" {
    export RDDF_QUICK_PLAN_DIR="$SMOKE_FAKE_ROOT/.rddf/plans"
    mkdir -p "$RDDF_QUICK_PLAN_DIR"
    bash "$REPO_ROOT/skills/rdd-quick/scripts/scaffold_plan.sh" \
        --name "smoke-acceptance" --proposal "smoke" --no-confirm
    run grep -c "^## Acceptance" "$RDDF_QUICK_PLAN_DIR/quick-smoke-acceptance.md"
    [ "$output" -ge 1 ]
    run grep -c "^- \[ \] AC-" "$RDDF_QUICK_PLAN_DIR/quick-smoke-acceptance.md"
    [ "$output" -ge 1 ]
}

@test "rdd-quick A4: scaffold_plan.sh does NOT read openspec/changes/*/proposal.md for AC (zero pollution)" {
    export RDDF_QUICK_PLAN_DIR="$SMOKE_FAKE_ROOT/.rddf/plans"
    mkdir -p "$RDDF_QUICK_PLAN_DIR" "$SMOKE_FAKE_ROOT/openspec/changes/decoy/specs/decoy"
    cat > "$SMOKE_FAKE_ROOT/openspec/changes/decoy/specs/decoy/spec.md" <<EOF
## ADDED Requirements
### Requirement: decoy-requirement
#### Scenario: malicious_AC
- [ ] AC-99: This AC must NOT appear in rdd-quick plan
EOF
    bash "$REPO_ROOT/skills/rdd-quick/scripts/scaffold_plan.sh" \
        --name "decoy-test" --proposal "decoy" --no-confirm
    run grep -c "AC-99\|decoy-requirement" "$RDDF_QUICK_PLAN_DIR/quick-decoy-test.md"
    [ "$output" -eq 0 ]
}
