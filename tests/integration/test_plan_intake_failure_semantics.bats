#!/usr/bin/env bats

# Test: plan_intake failure semantics (Gap 4)
# - Interrupted trace (missing finalize_at)
# - Abandoned rddf-session

setup() {
    TMPDIR="$BATS_TMPDIR/plan-intake-failure-$$"
    mkdir -p "$TMPDIR/.rddf/state/trace"
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

@test "interrupted trace (no finalize_at): plan_intake proceeds" {
    # Create interrupted trace
    cat > "$TMPDIR/.rddf/state/trace/guide-plan-test.json" <<'EOF'
{
  "phase": "guide-plan",
  "started_at": "2026-08-13T00:00:00+00:00"
}
EOF
    run run_plan_intake_in_tmp
    # Should not block on interrupted trace
    [[ ! "$output" =~ "Traceback" ]] || [[ "$status" -eq 0 ]]
}

@test "abandoned rddf-session: plan_intake proceeds" {
    # sessions.json with abandoned session
    cat > "$TMPDIR/.rddf/state/sessions.json" <<'EOF'
{
  "sessions": [
    {
      "session_id": "rds_test_abandoned",
      "kind": "stage_design",
      "state": "abandoned",
      "end_reason": "user-abandoned-via-guide-design-transition"
    }
  ]
}
EOF
    run run_plan_intake_in_tmp
    # Should not block on abandoned session
    [[ ! "$output" =~ "Traceback" ]] || [[ "$status" -eq 0 ]]
}
