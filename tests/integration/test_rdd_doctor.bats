#!/usr/bin/env bats
# tests/integration/test_rdd_doctor.bats
# Task 9: bash entry + CLI integration tests for rdd-doctor

load '../test_helper'

setup() {
    PROJECT_ROOT="$(git rev-parse --show-toplevel)"
    DOCTOR_SH="$PROJECT_ROOT/skills/rdd-doctor/scripts/doctor.sh"
}

@test "doctor: doctor.sh exists and is executable" {
    [ -x "$DOCTOR_SH" ]
}

@test "doctor: --help prints usage mentioning rdd-doctor" {
    run bash "$DOCTOR_SH" --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"rdd-doctor"* ]]
}

@test "doctor: --version prints version" {
    run bash "$DOCTOR_SH" --version
    [ "$status" -eq 0 ]
    [[ "$output" == *"0.1.0"* ]]
}

@test "doctor: --quiet produces at-most-single-line output" {
    cd "$PROJECT_ROOT"
    run bash "$DOCTOR_SH" --quiet
    [ "$status" -le 2 ]
    lines=$(echo "$output" | wc -l)
    [ "$lines" -le 1 ]
}

@test "doctor: --json writes .doctor-report.json" {
    cd "$PROJECT_ROOT"
    rm -f .rddf/state/.doctor-report.json
    run bash "$DOCTOR_SH" --json
    [ "$status" -le 2 ]
    [ -f .rddf/state/.doctor-report.json ]
}

@test "doctor: --json output has correct schema" {
    cd "$PROJECT_ROOT"
    rm -f .rddf/state/.doctor-report.json
    run bash "$DOCTOR_SH" --json
    [ "$status" -le 2 ]
    [ -f .rddf/state/.doctor-report.json ]
    grep -q '"timestamp"' .rddf/state/.doctor-report.json
    grep -q '"categories_checked"' .rddf/state/.doctor-report.json
    grep -q '"findings"' .rddf/state/.doctor-report.json
    grep -q '"summary"' .rddf/state/.doctor-report.json
}

@test "doctor: --category state runs only state checker" {
    cd "$PROJECT_ROOT"
    run bash "$DOCTOR_SH" --category state
    [ "$status" -le 2 ]
}

@test "doctor: unknown category is rejected by argparse" {
    cd "$PROJECT_ROOT"
    run bash "$DOCTOR_SH" --category nonexistent
    [ "$status" -ne 0 ]
}

@test "doctor: --help mentions all 6 categories" {
    run bash "$DOCTOR_SH" --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"state"* ]]
    [[ "$output" == *"plan-tdd"* ]]
    [[ "$output" == *"roadmap-meta"* ]]
    [[ "$output" == *"proposal-table"* ]]
    [[ "$output" == *"tasks-checkbox"* ]]
    [[ "$output" == *"migration-residue"* ]]
}