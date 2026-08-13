#!/usr/bin/env bats
# Tests for plan_intake.sh v1+v2 design-handoff compat + changes_pre_created skip.

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

@test "plan_intake: v1 design-handoff is accepted (backward compat)" {
    cat > "$WORK_DIR/.rddf/state/.design-handoff.json" <<EOF
{
  "design_complete_at": "2026-08-01T10:00:00+00:00",
  "proposals_reviewed": 1,
  "all_proposals_have_decision": true,
  "version": 1
}
EOF
    cd "$WORK_DIR"
    run bash -c "source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh' && check_design_handoff '$WORK_DIR'"
    [ "$status" -eq 0 ]
}

@test "plan_intake: v2 design-handoff is accepted (with changes_pre_created)" {
    cat > "$WORK_DIR/.rddf/state/.design-handoff.json" <<EOF
{
  "design_complete_at": "2026-08-01T10:00:00+00:00",
  "proposals_reviewed": 1,
  "all_proposals_have_decision": true,
  "version": 2,
  "changes_pre_created": ["demo"]
}
EOF
    cd "$WORK_DIR"
    run bash -c "source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh' && check_design_handoff '$WORK_DIR'"
    [ "$status" -eq 0 ]
}

@test "plan_intake: unknown version is rejected" {
    cat > "$WORK_DIR/.rddf/state/.design-handoff.json" <<EOF
{
  "design_complete_at": "2026-08-01T10:00:00+00:00",
  "proposals_reviewed": 1,
  "all_proposals_have_decision": true,
  "version": 99
}
EOF
    cd "$WORK_DIR"
    run bash -c "source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh' && check_design_handoff '$WORK_DIR'"
    [ "$status" -ne 0 ]
}

@test "plan_intake: v2 handoff exposes changes_pre_created as CHANGES_PRE_CREATED" {
    cat > "$WORK_DIR/.rddf/state/.design-handoff.json" <<EOF
{
  "design_complete_at": "2026-08-01T10:00:00+00:00",
  "proposals_reviewed": 1,
  "all_proposals_have_decision": true,
  "version": 2,
  "changes_pre_created": ["alpha", "beta"]
}
EOF
    cd "$WORK_DIR"
    # The function should expose CHANGES_PRE_CREATED as a global
    run bash -c "
        source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh'
        check_design_handoff '$WORK_DIR' >/dev/null
        echo \"\${CHANGES_PRE_CREATED[@]}\"
    "
    [ "$status" -eq 0 ]
    [[ "$output" == *"alpha"* ]]
    [[ "$output" == *"beta"* ]]
}

@test "plan_intake: v1 handoff treats changes_pre_created as empty" {
    cat > "$WORK_DIR/.rddf/state/.design-handoff.json" <<EOF
{
  "design_complete_at": "2026-08-01T10:00:00+00:00",
  "proposals_reviewed": 1,
  "all_proposals_have_decision": true,
  "version": 1
}
EOF
    cd "$WORK_DIR"
    run bash -c "
        source '$REPO_ROOT/skills/guide-plan/scripts/plan_intake.sh'
        check_design_handoff '$WORK_DIR' >/dev/null
        echo \"\${CHANGES_PRE_CREATED[@]}\"
    "
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}
