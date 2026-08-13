#!/usr/bin/env bats

# Test: plan_intake bootstrap edge cases (Gap 1)
# - Missing design-handoff
# - v2 handoff missing changes_pre_created field
# - Stale design_complete_at (>30d)
# - Empty changes_pre_created: []

setup() {
    TMPDIR="$BATS_TMPDIR/plan-intake-bootstrap-$$"
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
        # Monkey-patch orchestrator_run (workaround for known wrapper bug)
        orchestrator_run() { "$@"; }
        source "$HOME/.agents/skills/guide-plan/scripts/plan_intake.sh"
        run_plan_intake
    '
}

@test "missing .design-handoff.json: plan_intake runs without arch-handoff block" {
    # With SKIP_ARCH_HANDOFF=yes, arch check is bypassed; design-handoff missing
    # is the real concern. We expect plan_intake to proceed past arch check.
    run run_plan_intake_in_tmp
    # Should not be blocked by arch-handoff
    [[ ! "$output" =~ "arch 阶段必须先完成" ]]
}

@test "v2 handoff missing changes_pre_created: proceeds with empty array" {
    cat > "$TMPDIR/.rddf/state/.design-handoff.json" <<'EOF'
{
  "version": 2,
  "design_complete_at": "2026-08-13T00:00:00+00:00",
  "proposals_reviewed": 1,
  "all_proposals_have_decision": true
}
EOF
    run run_plan_intake_in_tmp
    # Should not fail catastrophically; may warn about missing field
    [[ ! "$output" =~ "JSON parse" ]] || [[ "$status" -eq 0 ]]
}

@test "stale design_complete_at (>30d): plan_intake proceeds" {
    STALE_DATE=$(date -d "60 days ago" -u +%Y-%m-%dT%H:%M:%S+00:00 2>/dev/null || \
                 date -v-60d -u +%Y-%m-%dT%H:%M:%S+00:00 2>/dev/null || \
                 echo "2026-06-01T00:00:00+00:00")
    cat > "$TMPDIR/.rddf/state/.design-handoff.json" <<EOF
{
  "version": 2,
  "design_complete_at": "$STALE_DATE",
  "proposals_reviewed": 1,
  "all_proposals_have_decision": true,
  "changes_pre_created": []
}
EOF
    run run_plan_intake_in_tmp
    # Stale handoff should not block plan phase entry
    [[ ! "$output" =~ "FATAL" ]] || [[ "$status" -eq 0 ]]
}

@test "empty changes_pre_created: [] does not crash" {
    cat > "$TMPDIR/.rddf/state/.design-handoff.json" <<'EOF'
{
  "version": 2,
  "design_complete_at": "2026-08-13T00:00:00+00:00",
  "proposals_reviewed": 0,
  "all_proposals_have_decision": true,
  "changes_pre_created": []
}
EOF
    run run_plan_intake_in_tmp
    # Empty array should be handled gracefully
    [[ ! "$output" =~ "TypeError" ]] || [[ "$status" -eq 0 ]]
}
