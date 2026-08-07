#!/usr/bin/env bats
# tests/integration/test_rdd_doctor_fixtures.bats
# Task 12: fixture-based integration tests using diseased/healthy fixtures

load '../test_helper'

setup() {
    PROJECT_ROOT="$(git rev-parse --show-toplevel)"
    DOCTOR_SH="$PROJECT_ROOT/skills/rdd-doctor/scripts/doctor.sh"
    FIXTURE_DISEASED="$PROJECT_ROOT/tests/fixtures/diseased-repo"
    FIXTURE_HEALTHY="$PROJECT_ROOT/tests/fixtures/healthy-repo"
}

@test "doctor: healthy fixture exits 0 (all 5 categories OK)" {
    cd "$FIXTURE_HEALTHY"
    run env RDDF_PROJECT_ROOT="$FIXTURE_HEALTHY" bash "$DOCTOR_SH"
    [ "$status" -eq 0 ]
    [[ "$output" == *"All 5 categories OK"* ]]
}

@test "doctor: diseased fixture reports at least one CRITICAL" {
    cd "$FIXTURE_DISEASED"
    run env RDDF_PROJECT_ROOT="$FIXTURE_DISEASED" bash "$DOCTOR_SH"
    [ "$status" -eq 2 ]
    [[ "$output" == *"CRITICAL"* ]]
}

@test "doctor: S4 root cause detected — manual_deps as string (silently ignore)" {
    cd "$FIXTURE_DISEASED"
    run env RDDF_PROJECT_ROOT="$FIXTURE_DISEASED" bash "$DOCTOR_SH"
    [[ "$output" == *"silently ignore"* ]]
    [[ "$output" == *"manual_deps"* ]]
}

@test "doctor: --category state on diseased fixture finds state JSON drift" {
    cd "$FIXTURE_DISEASED"
    run env RDDF_PROJECT_ROOT="$FIXTURE_DISEASED" bash "$DOCTOR_SH" --category state
    [[ "$output" == *"schema iteration_schema.json not found"* ]]
}