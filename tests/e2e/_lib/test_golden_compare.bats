#!/usr/bin/env bats
# tests/e2e/_lib/test_golden_compare.bats
# Self-test for golden_compare.bash (per 2026-09-08-e2e-test-plan-phase1 Task 3)
# Will be deleted in Task 14 after real coverage lives in tests/e2e/script/.

load ../../test_helper

setup() {
    source "$REPO_ROOT/tests/e2e/_lib/golden_compare.bash"
    GOLDEN_DIR="$BATS_TEST_TMPDIR/golden"
    mkdir -p "$GOLDEN_DIR"
}

@test "golden_compare::update writes file with sha256 + fields" {
    local actual_file="$BATS_TEST_TMPDIR/actual.json"
    echo '{"ac_id": "AC-1", "status": "pass", "confidence": 0.95}' > "$actual_file"
    run golden_compare::update "$GOLDEN_DIR/v1.json" "$actual_file" "ac_id,status,confidence"
    [ "$status" -eq 0 ]
    [ -f "$GOLDEN_DIR/v1.json" ]
    grep -q "sha256:" "$GOLDEN_DIR/v1.json"
    grep -q "fields:ac_id,status,confidence" "$GOLDEN_DIR/v1.json"
    grep -q "values:" "$GOLDEN_DIR/v1.json"
}

@test "golden_compare::check returns 0 when current matches golden" {
    local actual_file="$BATS_TEST_TMPDIR/actual.json"
    echo '{"ac_id": "AC-1", "status": "pass"}' > "$actual_file"
    golden_compare::update "$GOLDEN_DIR/v1.json" "$actual_file" "ac_id,status"
    run golden_compare::check "$GOLDEN_DIR/v1.json" "$actual_file" "ac_id,status"
    [ "$status" -eq 0 ]
}

@test "golden_compare::check returns 1 when field drift detected" {
    local actual_file="$BATS_TEST_TMPDIR/actual.json"
    echo '{"ac_id": "AC-1", "status": "pass"}' > "$actual_file"
    golden_compare::update "$GOLDEN_DIR/v1.json" "$actual_file" "ac_id,status"
    echo '{"ac_id": "AC-1", "status": "fail"}' > "$actual_file"
    run golden_compare::check "$GOLDEN_DIR/v1.json" "$actual_file" "ac_id,status"
    [ "$status" -eq 1 ]
}

@test "golden_compare::regen is alias for update" {
    local actual_file="$BATS_TEST_TMPDIR/actual.json"
    echo '{"ac_id": "AC-1"}' > "$actual_file"
    golden_compare::regen "$GOLDEN_DIR/v1.json" "$actual_file" "ac_id"
    [ -f "$GOLDEN_DIR/v1.json" ]
    grep -q "fields:ac_id" "$GOLDEN_DIR/v1.json"
}
