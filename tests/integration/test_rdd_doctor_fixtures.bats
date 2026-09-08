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

@test "doctor: healthy fixture has no CRITICAL" {
    # Build a synthetic healthy fixture in $BATS_TMPDIR. The original
    # tests/fixtures/healthy-repo dir was never created, only diseased-repo was.
    # Healthy = iteration.json conforms to current schema (v7 per iteration_schema.json:
    # required=version, updated_at, current_phase, changes; version ∈ {3..7}).
    # Note: doctor may still emit WARNINGs for missing schemas (real _lib/ path
    # not in tmpdir); assert "no CRITICAL" rather than "exit 0".
    FIXTURE_HEALTHY="$(mktemp -d)"
    mkdir -p "$FIXTURE_HEALTHY/.rddf/state" "$FIXTURE_HEALTHY/.rddf/roadmap/unknown"
    cat > "$FIXTURE_HEALTHY/.rddf/state/iteration.json" <<'EOF'
{"version":7,"updated_at":"2026-09-08T00:00:00Z","current_phase":"unknown","changes":[]}
EOF
    cd "$FIXTURE_HEALTHY"
    run env RDDF_PROJECT_ROOT="$FIXTURE_HEALTHY" bash "$DOCTOR_SH"
    ! [[ "$output" == *"CRITICAL"* ]]
    ! [[ "$status" -eq 2 ]]
    rm -rf "$FIXTURE_HEALTHY"
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