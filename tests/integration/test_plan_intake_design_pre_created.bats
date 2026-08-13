#!/usr/bin/env bats
# tests/integration/test_plan_intake_design_pre_created.bats
# Gap 1 fix: CHANGES_PRE_CREATED contract consumption.
# plan_intake.sh exports CHANGES_PRE_CREATED but downstream consumers (label,
# skip-creation, narrow-fill) are missing. These tests lock the consumer
# behavior introduced to close the contract.
#
# CONTRACT (consumed by guide-plan/SKILL.md Phase 0/2/2.5):
#   is_design_pre_created <name>           → exit 0 if in CHANGES_PRE_CREATED
#   get_design_pre_created_label <name>    → "🆕 design-pre-created" or ""
#   get_fill_artifacts_for <name>          → "specs design tasks" or
#                                            "proposal design tasks specs"
#
# SKIP_DESIGN_HANDOFF=yes → CHANGES_PRE_CREATED=() → helpers return 1 / ""

load ../test_helper

setup() {
    REPO_ROOT="$(git rev-parse --show-toplevel)"
    WORK_DIR="$(mktemp -d)"
    mkdir -p "$WORK_DIR/.rddf/state"
    mkdir -p "$WORK_DIR/openspec/changes"
    # plan_intake.sh's bootstrap uses ${RDDF_PROJECT_ROOT:-...} to find
    # orchestrator_entry.sh. WORK_DIR is not a git repo, so without this
    # export the bootstrap silently fails and orchestrator_run is undefined.
    export RDDF_PROJECT_ROOT="$REPO_ROOT"
}

teardown() {
    rm -rf "$WORK_DIR"
}

# Helper to write a v2 design-handoff
write_v2_handoff() {
    local pre_created_json="$1"
    cat > "$WORK_DIR/.rddf/state/.design-handoff.json" <<EOF
{
  "design_complete_at": "2026-08-01T10:00:00+00:00",
  "proposals_reviewed": 2,
  "all_proposals_have_decision": true,
  "version": 2,
  "changes_pre_created": ${pre_created_json}
}
EOF
}

@test "plan_intake: is_design_pre_created returns 0 for name in CHANGES_PRE_CREATED" {
    write_v2_handoff '["alpha", "beta"]'
    cd "$WORK_DIR"
    run bash -c "
        source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh'
        check_design_handoff '$WORK_DIR' >/dev/null
        is_design_pre_created 'alpha'
    "
    [ "$status" -eq 0 ]
}

@test "plan_intake: is_design_pre_created returns 0 for second name in array" {
    write_v2_handoff '["alpha", "beta"]'
    cd "$WORK_DIR"
    run bash -c "
        source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh'
        check_design_handoff '$WORK_DIR' >/dev/null
        is_design_pre_created 'beta'
    "
    [ "$status" -eq 0 ]
}

@test "plan_intake: is_design_pre_created returns 1 for name NOT in CHANGES_PRE_CREATED" {
    write_v2_handoff '["alpha"]'
    cd "$WORK_DIR"
    run bash -c "
        source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh'
        check_design_handoff '$WORK_DIR' >/dev/null
        is_design_pre_created 'gamma'
    "
    [ "$status" -eq 1 ]
}

@test "plan_intake: is_design_pre_created returns 1 when CHANGES_PRE_CREATED is empty" {
    write_v2_handoff '[]'
    cd "$WORK_DIR"
    run bash -c "
        source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh'
        check_design_handoff '$WORK_DIR' >/dev/null
        is_design_pre_created 'alpha'
    "
    [ "$status" -eq 1 ]
}

@test "plan_intake: get_design_pre_created_label returns 🆕 design-pre-created for pre-created" {
    write_v2_handoff '["alpha"]'
    cd "$WORK_DIR"
    run bash -c "
        source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh'
        check_design_handoff '$WORK_DIR' >/dev/null
        get_design_pre_created_label 'alpha'
    "
    [ "$status" -eq 0 ]
    [ "$output" = "🆕 design-pre-created" ]
}

@test "plan_intake: get_design_pre_created_label returns empty for NOT pre-created" {
    write_v2_handoff '["alpha"]'
    cd "$WORK_DIR"
    run bash -c "
        source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh'
        check_design_handoff '$WORK_DIR' >/dev/null
        get_design_pre_created_label 'gamma'
    "
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "plan_intake: get_fill_artifacts_for returns narrow set for pre-created (no proposal)" {
    write_v2_handoff '["alpha"]'
    cd "$WORK_DIR"
    run bash -c "
        source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh'
        check_design_handoff '$WORK_DIR' >/dev/null
        get_fill_artifacts_for 'alpha'
    "
    [ "$status" -eq 0 ]
    # Pre-created changes have complete proposal.md from design approval.
    # Plan must fill only the missing artifacts (design.md, tasks.md, specs/).
    # Must NOT include 'proposal' in the narrow list.
    [[ "$output" == *"design"* ]]
    [[ "$output" == *"tasks"* ]]
    [[ "$output" == *"specs"* ]]
    [[ "$output" != *"proposal"* ]]
}

@test "plan_intake: get_fill_artifacts_for returns full set for NOT pre-created" {
    write_v2_handoff '[]'
    cd "$WORK_DIR"
    run bash -c "
        source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh'
        check_design_handoff '$WORK_DIR' >/dev/null
        get_fill_artifacts_for 'gamma'
    "
    [ "$status" -eq 0 ]
    # Non-pre-created (fresh pending proposal) needs full fill including proposal.
    [[ "$output" == *"proposal"* ]]
    [[ "$output" == *"design"* ]]
    [[ "$output" == *"tasks"* ]]
    [[ "$output" == *"specs"* ]]
}

@test "plan_intake: SKIP_DESIGN_HANDOFF=yes → all helpers return safe defaults" {
    cd "$WORK_DIR"
    run bash -c "
        export SKIP_DESIGN_HANDOFF=yes
        source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh'
        check_design_handoff '$WORK_DIR' >/dev/null
        is_design_pre_created 'anything'
        echo \"is_design_pre_created exit: \$?\"
        get_design_pre_created_label 'anything'
        echo \"label: '\$(get_design_pre_created_label 'anything')'\"
    "
    [ "$status" -eq 0 ]
    # With SKIP_DESIGN_HANDOFF, CHANGES_PRE_CREATED should be empty →
    # is_design_pre_created returns 1, label returns empty string.
    [[ "$output" == *"exit: 1"* ]]
    [[ "$output" == *"label: ''"* ]]
}