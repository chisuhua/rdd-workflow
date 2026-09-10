#!/usr/bin/env bats
# tests/integration/test_rdd_planner_roadmap_bootstrap.bats
# Integration tests for rdd-planner Phase 0 roadmap-bootstrap (per ADR-0048 §Decision 2).
#
# Verifies:
#  - rdd-planner SKILL.md documents Phase 0 roadmap-bootstrap
#  - rdd-planner role.boundaries.owns includes roadmap.md + features/phases
#  - rdd-planner role.boundaries.owns includes .populate-state.json (new per ADR-0048)
#  - rdd-planner SKILL.md mentions Phase 5 double-gate
#  - rdd-planner SKILL.md mentions recommended_route as required
#  - rdd-planner SKILL.md mentions roadmap init guidance

load test_helper

setup() {
    REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
    PLANNER_SKILL="$REPO_ROOT/skills/rdd-planner/SKILL.md"
}

# ---------------------------------------------------------------------------
# SKILL.md structural checks (per ADR-0048 §Decision 2)
# ---------------------------------------------------------------------------

@test "rdd-planner: SKILL.md mentions roadmap-bootstrap" {
    [ -f "$PLANNER_SKILL" ]
    run grep -c "roadmap-bootstrap\|roadmap_bootstrap" "$PLANNER_SKILL"
    [ "$status" -eq 0 ]
    [ "$output" -ge 1 ]
}

@test "rdd-planner: SKILL.md mentions Phase 0 in body" {
    [ -f "$PLANNER_SKILL" ]
    run grep -c "^## Phase 0:" "$PLANNER_SKILL"
    [ "$status" -eq 0 ]
    [ "$output" -ge 1 ]
}

@test "rdd-planner: SKILL.md mentions ADR-0048 (decision traceability)" {
    [ -f "$PLANNER_SKILL" ]
    run grep -c "ADR-0048" "$PLANNER_SKILL"
    [ "$status" -eq 0 ]
    [ "$output" -ge 1 ]
}

@test "rdd-planner: SKILL.md mentions Phase 5 double-gate" {
    [ -f "$PLANNER_SKILL" ]
    run grep -c "双门控" "$PLANNER_SKILL"
    [ "$status" -eq 0 ]
    [ "$output" -ge 1 ]
}

@test "rdd-planner: SKILL.md mentions recommended_route as required" {
    [ -f "$PLANNER_SKILL" ]
    run grep -E "recommended_route.*required|REQUIRED.*recommended_route" "$PLANNER_SKILL"
    [ "$status" -eq 0 ]
}

@test "rdd-planner: SKILL.md mentions roadmap init guidance" {
    [ -f "$PLANNER_SKILL" ]
    run grep -c "rddf roadmap init\|roadmap init" "$PLANNER_SKILL"
    [ "$status" -eq 0 ]
    [ "$output" -ge 1 ]
}

# ---------------------------------------------------------------------------
# role.boundaries content (use a tolerant awk that handles 2/4/6-space indent)
# ---------------------------------------------------------------------------

# Extract role block as flat `OWN:<line>` / `NOT:<line>` entries. Tolerates
# both rdd-arch's 2-space and rdd-planner's 6-space YAML indentation.
extract_role() {
    awk '
        BEGIN { mode = 0 }
        /^role:/ { mode = 1; next }
        mode && /^---$/ { exit }
        mode && /^[ ]+owns:/ && !/not_owns/ { mode = 2; next }
        mode && /^[ ]+not_owns:/ { mode = 3; next }
        mode == 2 && /^    +- / { print "OWN:" substr($0, index($0, "- ")) }
        mode == 3 && /^    +- / { print "NOT:" substr($0, index($0, "- ")) }
    ' "$1"
}

@test "rdd-planner: role.owns includes roadmap.md" {
    [ -f "$PLANNER_SKILL" ]
    run extract_role "$PLANNER_SKILL"
    [ "$status" -eq 0 ]
    [[ "$output" =~ OWN:.*\"roadmap\.md\" ]]
}

@test "rdd-planner: role.owns includes .rddf/roadmap/features/*.md" {
    [ -f "$PLANNER_SKILL" ]
    run extract_role "$PLANNER_SKILL"
    [ "$status" -eq 0 ]
    [[ "$output" =~ OWN:.*\.rddf/roadmap/features ]]
}

@test "rdd-planner: role.owns includes .rddf/roadmap/phases/*.md (new per ADR-0048)" {
    [ -f "$PLANNER_SKILL" ]
    run extract_role "$PLANNER_SKILL"
    [ "$status" -eq 0 ]
    [[ "$output" =~ OWN:.*\.rddf/roadmap/phases ]]
}

@test "rdd-planner: role.owns includes .populate-state.json (new per ADR-0048)" {
    [ -f "$PLANNER_SKILL" ]
    run extract_role "$PLANNER_SKILL"
    [ "$status" -eq 0 ]
    [[ "$output" =~ OWN:.*populate-state ]]
}

@test "rdd-planner: role.owns includes .planner-state.json" {
    [ -f "$PLANNER_SKILL" ]
    run extract_role "$PLANNER_SKILL"
    [ "$status" -eq 0 ]
    [[ "$output" =~ OWN:.*\.planner-state\.json ]]
}

@test "rdd-planner: role.owns includes .planner-feedback.json" {
    [ -f "$PLANNER_SKILL" ]
    run extract_role "$PLANNER_SKILL"
    [ "$status" -eq 0 ]
    [[ "$output" =~ OWN:.*\.planner-feedback\.json ]]
}

@test "rdd-planner: role.owns includes .planner-handoff.json" {
    [ -f "$PLANNER_SKILL" ]
    run extract_role "$PLANNER_SKILL"
    [ "$status" -eq 0 ]
    [[ "$output" =~ OWN:.*\.planner-handoff\.json ]]
}

# not_owns: planner must NOT own roadmap (since it OWNS roadmap)
@test "rdd-planner: role.not_owns does NOT include roadmap.md" {
    [ -f "$PLANNER_SKILL" ]
    run extract_role "$PLANNER_SKILL"
    [ "$status" -eq 0 ]
    ! [[ "$output" =~ NOT:.*\"roadmap\.md\" ]]
}

@test "rdd-planner: role.not_owns includes docs/adr/ADR-*.md (arch owns)" {
    [ -f "$PLANNER_SKILL" ]
    run extract_role "$PLANNER_SKILL"
    [ "$status" -eq 0 ]
    [[ "$output" =~ NOT:.*docs/adr/ADR ]]
}

@test "rdd-planner: role.not_owns includes openspec/changes/<name>/proposal.md" {
    [ -f "$PLANNER_SKILL" ]
    run extract_role "$PLANNER_SKILL"
    [ "$status" -eq 0 ]
    # Use a regex variable to avoid bash interpreting <name> as redirect.
    local pat='NOT:.*openspec/changes/<name>/proposal'
    [[ "$output" =~ $pat ]]
}
