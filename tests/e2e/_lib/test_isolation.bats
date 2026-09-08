#!/usr/bin/env bats
# tests/e2e/_lib/test_isolation.bats
# Self-test for isolation.bash (per 2026-09-08-e2e-test-plan-phase1 Task 1)
# Will be deleted in Task 14 after real coverage lives in tests/e2e/script/.

load ../../test_helper

setup() {
    source "$REPO_ROOT/tests/e2e/_lib/isolation.bash"
}

@test "isolation::snapshot_repo_state writes sha256 to file" {
    run isolation::snapshot_repo_state "$BATS_TEST_TMPDIR/baseline.sha256"
    [ "$status" -eq 0 ]
    [ -f "$BATS_TEST_TMPDIR/baseline.sha256" ]
    [ -s "$BATS_TEST_TMPDIR/baseline.sha256" ]
}

@test "isolation::verify_zero_pollution returns 0 when state unchanged" {
    isolation::snapshot_repo_state "$BATS_TEST_TMPDIR/baseline.sha256"
    # No mutation between snapshot and verify
    run isolation::verify_zero_pollution "$BATS_TEST_TMPDIR/baseline.sha256"
    [ "$status" -eq 0 ]
}

@test "isolation::verify_zero_pollution returns 1 when .rddf/ modified" {
    isolation::snapshot_repo_state "$BATS_TEST_TMPDIR/baseline.sha256"
    # Simulate pollution
    mkdir -p "$REPO_ROOT/.rddf/state"
    echo "polluted" > "$REPO_ROOT/.rddf/state/test_isolation_pollution.sha256"
    run isolation::verify_zero_pollution "$BATS_TEST_TMPDIR/baseline.sha256"
    # Cleanup before assertion to avoid polluting later tests
    rm -f "$REPO_ROOT/.rddf/state/test_isolation_pollution.sha256"
    [ "$status" -eq 1 ]
}
