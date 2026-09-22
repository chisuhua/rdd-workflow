#!/usr/bin/env bats
# tests/integration/test_rdd_planner_objective.bats
#
# rdd-planner objective integration (per add-objective-tracking change):
#   - planner_stage_exit.sh refreshes AGENTS.md <!-- AUTO-OBJECTIVES --> sentinel
#   - list-objectives shows PoC files after planner run
#   - revise-objective appends §11 ledger row + bumps last_revised
#
# Run: bats tests/integration/test_rdd_planner_objective.bats

load ../test_helper

setup() {
    PROJECT_ROOT="$(git rev-parse --show-toplevel)"
    export PROJECT_ROOT
    STAGE_EXIT_SH="$PROJECT_ROOT/skills/rdd-planner/scripts/planner_stage_exit.sh"
    REVISE_SH="$PROJECT_ROOT/skills/roadmap/scripts/objective_revise.sh"
    AGENTS_MD="$PROJECT_ROOT/AGENTS.md"
}

@test "planner-objective: AGENTS.md contains AUTO-OBJECTIVES sentinel" {
    [ -f "$AGENTS_MD" ]
    grep -q "<!-- AUTO-OBJECTIVES start -->" "$AGENTS_MD"
    grep -q "<!-- AUTO-OBJECTIVES end -->" "$AGENTS_MD"
}

@test "planner-objective: sentinel lists both PoC objectives" {
    grep -q "objective-bypass-audit-hub-governance" "$AGENTS_MD"
    grep -q "objective-onboard-new-skill" "$AGENTS_MD"
}

@test "planner-objective: revise-objective appends ledger row + bumps last_revised" {
    local TMP_DIR; TMP_DIR="$(mktemp -d)"
    mkdir -p "$TMP_DIR/.rddf/roadmap/objectives"
    cp "$PROJECT_ROOT/.rddf/roadmap/objectives/objective-onboard-new-skill.md" "$TMP_DIR/.rddf/roadmap/objectives/objective-revise-test.md"
    # Normalize id inside file to match filename (revise reads frontmatter id)
    sed -i 's/^id: objective-onboard-new-skill$/id: objective-revise-test/' "$TMP_DIR/.rddf/roadmap/objectives/objective-revise-test.md"

    run bash -c "PROJECT_ROOT='$TMP_DIR' bash '$REVISE_SH' objective-revise-test --kind sprint-review --content 'sprint 复盘验证' --decision 'continue' --reason 'bats test'"
    [ "$status" -eq 0 ]
    [[ "$output" == *"appended ledger row"* ]]

    # Ledger row present
    grep -q "sprint 复盘验证" "$TMP_DIR/.rddf/roadmap/objectives/objective-revise-test.md"
    # last_revised bumped to today
    TODAY="$(date +%Y-%m-%d)"
    grep -q "last_revised: $TODAY" "$TMP_DIR/.rddf/roadmap/objectives/objective-revise-test.md"
    rm -rf "$TMP_DIR"
}

@test "planner-objective: list-objectives CLI integrates with PoC files" {
    run rddf roadmap list-objectives --format json
    [ "$status" -eq 0 ]
    [[ "$output" == *"objective-bypass-audit-hub-governance"* ]]
}
