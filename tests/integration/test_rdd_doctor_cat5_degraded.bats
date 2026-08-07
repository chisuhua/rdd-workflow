#!/usr/bin/env bats
# tests/integration/test_rdd_doctor_cat5_degraded.bats
# Task 14: cat-5 degraded path verification (MUST #12 + AC5)

load '../test_helper'

setup() {
    PROJECT_ROOT="$(git rev-parse --show-toplevel)"
    DOCTOR_SH="$PROJECT_ROOT/skills/rdd-doctor/scripts/doctor.sh"
    FIXTURE="$PROJECT_ROOT/tests/fixtures/diseased-repo"
    # Build PATH that excludes openspec's directory so shutil.which("openspec")
    # returns None. Keep python3/bash accessible.
    OPENSPEC_LOC="$(command -v openspec 2>/dev/null || true)"
    if [ -n "$OPENSPEC_LOC" ]; then
        OPENSPEC_DIR="$(dirname "$OPENSPEC_LOC")"
        STRIPPED_PATH=$(echo "$PATH" | tr ':' '\n' | grep -v "^${OPENSPEC_DIR}$" | paste -sd: -)
    else
        STRIPPED_PATH="$PATH"
    fi
    export STRIPPED_PATH
}

@test "doctor: cat-5 emits INFO (not exit 3) when openspec not on PATH" {
    cd "$FIXTURE"
    run env RDDF_PROJECT_ROOT="$FIXTURE" PATH="$STRIPPED_PATH" bash "$DOCTOR_SH"
    [ "$status" -ne 3 ]
    [[ "$output" == *"openspec status unavailable"* ]]
}

@test "doctor: cat-5 still produces CRITICAL findings from other categories when degraded" {
    cd "$FIXTURE"
    run env RDDF_PROJECT_ROOT="$FIXTURE" PATH="$STRIPPED_PATH" bash "$DOCTOR_SH"
    [[ "$output" == *"CRITICAL"* ]]
    [[ "$output" == *"silently ignore"* ]]
}

@test "doctor: cat-5 degraded path does NOT mark checker as failed" {
    cd "$FIXTURE"
    run env RDDF_PROJECT_ROOT="$FIXTURE" PATH="$STRIPPED_PATH" bash "$DOCTOR_SH"
    [ "$status" -ne 3 ]
    [[ ! "$output" == *"checker raised"* ]]
}

@test "doctor: with openspec available, no degraded-path INFO emitted" {
    cd "$PROJECT_ROOT"
    OPENSPEC_PATH=$(dirname "$(command -v openspec)")
    run env RDDF_PROJECT_ROOT="$FIXTURE" PATH="$OPENSPEC_PATH:$PATH" bash "$DOCTOR_SH"
    [[ ! "$output" == *"openspec status unavailable"* ]]
}