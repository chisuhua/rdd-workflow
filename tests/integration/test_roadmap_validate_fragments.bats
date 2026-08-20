#!/usr/bin/env bats
# Test roadmap validate-fragments + rdd-doctor roadmap-refs double entry (Task 10 / T19, AC-2.8).
# Validates: same validate_fragment_refs is exposed via 2 entry points (gate + diagnostic).

load ../test_helper

setup() {
    TMP=$(mktemp -d)
    cd "$TMP"
    git init -q .
    mkdir -p docs/adr
    mkdir -p .rddf/roadmap/features
    # Sample roadmap + R1 violation
    cat > .rddf/roadmap.md <<'EOF'
# Roadmap
| phase-1 | T | active | | |
EOF
    cat > .rddf/roadmap/features/feat-bad.md <<'EOF'
---
id: feat-bad
kind: feature
status: active
phase_refs: [phase-99]
---
body
EOF
    export RDDF_PROJECT_ROOT="$TMP"
    VALIDATE_SCRIPT="/workspace/project/rdd-workflow/skills/roadmap/scripts/roadmap_validate_fragments.sh"
    DOCTOR="/workspace/project/rdd-workflow/skills/rdd-doctor/scripts/doctor.sh"
}

teardown() {
    rm -rf "$TMP"
    unset RDDF_PROJECT_ROOT STRICT_ROADMAP_REFS_GATE SKIP_ROADMAP_REFS_GATE
}

@test "validate-fragments: default mode reports R1 CRITICAL (exit 1)" {
    unset STRICT_ROADMAP_REFS_GATE
    run bash "$VALIDATE_SCRIPT"
    [ "$status" -eq 1 ]
    [[ "$output" == *"R1"* ]]
    [[ "$output" == *"CRITICAL"* ]]
}

@test "validate-fragments: STRICT_ROADMAP_REFS_GATE=yes blocks on R1" {
    export STRICT_ROADMAP_REFS_GATE=yes
    run bash "$VALIDATE_SCRIPT"
    [ "$status" -eq 1 ]
    [[ "$output" == *"R1"* ]]
}

@test "rdd-doctor --category roadmap-refs: matches validate-fragments R1 output" {
    run bash "$DOCTOR" --category roadmap-refs
    [ "$status" -eq 2 ]  # CRITICAL → exit 2 per doctor_render.py::exit_code_for
    [[ "$output" == *"R1"* ]]
    [[ "$output" == *"feat-bad"* ]]
    [[ "$output" == *"CRITICAL"* ]]
}

@test "SKIP_ROADMAP_REFS_GATE=yes: validate-fragments skips and exits 0" {
    export SKIP_ROADMAP_REFS_GATE=yes
    run bash "$VALIDATE_SCRIPT"
    [ "$status" -eq 0 ]
    [[ "$output" == *"skipped"* ]]
}
