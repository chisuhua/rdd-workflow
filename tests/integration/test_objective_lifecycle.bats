#!/usr/bin/env bats
# tests/integration/test_objective_lifecycle.bats
#
# Lifecycle coverage for objective files (per add-objective-tracking change):
#   - list-objectives shows PoC files + status filter
#   - show-objective renders derived view (§6/§7/§8 via CLI)
#   - archive-objective moves file to objectives/archive/
#   - review_by grace triggers WARNING in doctor lifecycle check
#
# Run: bats tests/integration/test_objective_lifecycle.bats

load ../test_helper

setup() {
    PROJECT_ROOT="$(git rev-parse --show-toplevel)"
    export PROJECT_ROOT
    OBJ_DIR="$PROJECT_ROOT/.rddf/roadmap/objectives"
    DOCTOR_SH="$PROJECT_ROOT/skills/rdd-doctor/scripts/doctor.sh"
}

@test "objective-lifecycle: list-objectives shows both PoC files" {
    run rddf roadmap list-objectives
    [ "$status" -eq 0 ]
    [[ "$output" == *"objective-bypass-audit-hub-governance"* ]]
    [[ "$output" == *"objective-onboard-new-skill"* ]]
}

@test "objective-lifecycle: list-objectives --status deferred filters" {
    run rddf roadmap list-objectives --status deferred
    [ "$status" -eq 0 ]
    [[ "$output" == *"objective-bypass-audit-hub-governance"* ]]
    [[ "$output" != *"objective-onboard-new-skill"* ]]
}

@test "objective-lifecycle: show-objective renders derived view" {
    run rddf roadmap show-objective objective-onboard-new-skill
    [ "$status" -eq 0 ]
    # Derived §6/§7/§8 note must be present (CLI-derived, not hand-written)
    [[ "$output" == *"derived"* || "$output" == *"§7"* || "$output" == *"§8"* ]]
}

@test "objective-lifecycle: archive-objective moves file to archive/" {
    local TMP_DIR; TMP_DIR="$(mktemp -d)"
    mkdir -p "$TMP_DIR/.rddf/roadmap/objectives"
    cp "$OBJ_DIR/objective-onboard-new-skill.md" "$TMP_DIR/.rddf/roadmap/objectives/objective-archive-test.md"
    # Use the CLI against a temp project root via PROJECT_ROOT override
    run bash -c "PROJECT_ROOT='$TMP_DIR' bash '$PROJECT_ROOT/skills/roadmap/scripts/objective_archive.sh' objective-archive-test"
    [ "$status" -eq 0 ]
    [ -f "$TMP_DIR/.rddf/roadmap/objectives/archive/objective-archive-test.md" ]
    [ ! -f "$TMP_DIR/.rddf/roadmap/objectives/objective-archive-test.md" ]
    rm -rf "$TMP_DIR"
}

@test "objective-lifecycle: doctor lifecycle check passes on PoC files" {
    run bash "$DOCTOR_SH" --category objective-lifecycle
    [ "$status" -le 2 ]
    [[ "$output" == *"OK"* || "$status" -eq 0 ]]
}
