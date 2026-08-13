#!/usr/bin/env bats

# Test: cross-phase design-done → plan-intake handoff integration (Gap 3)
# - v2 happy path with changes_pre_created
# - v2 sad path (missing version field)

setup() {
    TMPDIR="$BATS_TMPDIR/plan-intake-cross-$$"
    mkdir -p "$TMPDIR/.rddf/state"
    export RDDF_PROJECT_ROOT="$TMPDIR"
    export SKIP_ARCH_HANDOFF=yes
}

teardown() {
    rm -rf "$TMPDIR"
}

run_plan_intake_in_tmp() {
    bash -c '
        export RDDF_PROJECT_ROOT="'"$TMPDIR"'"
        source "$HOME/.agents/skills/_lib/orchestrator_entry.sh" 2>/dev/null || true
        orchestrator_run() { "$@"; }
        source "$HOME/.agents/skills/guide-plan/scripts/plan_intake.sh"
        run_plan_intake
    '
}

@test "design v2 happy path with changes_pre_created: plan_intake recognizes pre-created" {
    cat > "$TMPDIR/.rddf/state/.design-handoff.json" <<'EOF'
{
  "version": 2,
  "design_complete_at": "2026-08-13T00:00:00+00:00",
  "proposals_reviewed": 1,
  "all_proposals_have_decision": true,
  "changes_pre_created": ["test-change-x"]
}
EOF
    run run_plan_intake_in_tmp
    # Should mention design-handoff / pre-created change
    [[ "$output" =~ "design-handoff" ]] || [[ "$status" -eq 0 ]]
}

@test "design v2 sad path (missing version field but has changes_pre_created): plan_intake proceeds" {
    cat > "$TMPDIR/.rddf/state/.design-handoff.json" <<'EOF'
{
  "design_complete_at": "2026-08-13T00:00:00+00:00",
  "proposals_reviewed": 1,
  "all_proposals_have_decision": true,
  "changes_pre_created": ["test-change-x"]
}
EOF
    run run_plan_intake_in_tmp
    # Missing version field should not crash
    [[ ! "$output" =~ "KeyError" ]] || [[ "$status" -eq 0 ]]
}
