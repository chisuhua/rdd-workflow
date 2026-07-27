#!/usr/bin/env bats
# tests/integration/test_ship_phase1.bats
# Locks the run_ship_phase1 orchestrator extraction (replaces the 30-line
# inline block at guide-ship.md Phase 1 L116-L145) and the sourced-only
# guard on ship_plan.sh.
#
# Background: the AI platform executing guide-ship's bash blocks may split
# a single markdown block into multiple bash processes. When that happens,
# `source ship_plan.sh` in one process and `detect_execution_mode` in
# another yields "command not found". The defense is:
#   (a) collapse Phase 1 into one function call (run_ship_phase1)
#   (b) put `source` and `run_ship_phase1` on the SAME LINE in SKILL.md
#   (c) guard ship_plan.sh so direct execution gives an actionable error
#
# Pairs with test_ship_plan_extraction.bats (older contract still in force).

load ../test_helper

SHIP_PLAN="$REPO_ROOT/skills/guide-ship/scripts/ship_plan.sh"
SKILL_MD="$REPO_ROOT/skills/guide-ship/SKILL.md"

@test "ship_plan.sh defines run_ship_phase1() orchestrator" {
  [ -f "$SHIP_PLAN" ]
  grep -q "^run_ship_phase1()" "$SHIP_PLAN"
}

@test "ship_plan.sh has sourced-only guard matching discover-arch-artifacts.sh style" {
  [ -f "$SHIP_PLAN" ]
  # Use [ not [[ — must match existing precedent at
  # skills/_lib/discover-arch-artifacts.sh L27.
  grep -qE 'if \[ "\$\{BASH_SOURCE\[0\]\}" = "\$0" \]' "$SHIP_PLAN"
  grep -qE 'echo .*Source it instead' "$SHIP_PLAN"
}

@test "structural: SKILL.md Phase 1 no longer inlines phase-1 helper calls" {
  [ -f "$SKILL_MD" ]
  ! grep -qE '^MODE=\$\(detect_execution_mode' "$SKILL_MD"
  ! grep -qE '^WT_PATH=\$\(setup_execution_workspace' "$SKILL_MD"
  ! grep -qE '^PLAN_STEP_COUNT=\$\(generate_implementation_plan' "$SKILL_MD"
  ! grep -qE '^check_artifacts_committed "\$PROJECT_ROOT"' "$SKILL_MD"
  ! grep -qE '^record_iteration_status "\$PROJECT_ROOT"' "$SKILL_MD"
}

@test "structural: source and run_ship_phase1 on the SAME LINE in SKILL.md" {
  [ -f "$SKILL_MD" ]
  # The core defense against code-block splitting — grep must find both on one line.
  grep -qE 'source .*scripts/ship_plan\.sh" && run_ship_phase1 "\$PROJECT_ROOT" "\$CHANGE_NAME"' "$SKILL_MD"
}

@test "happy path: orchestration order + MODE/WT_PATH/PLAN_STEP_COUNT output" {
  source "$SHIP_PLAN"
  local calls_file="$BATS_TMPDIR/calls"
  : > "$calls_file"
  read_plan_handoff()           { echo "read_plan_handoff"           >> "$calls_file"; }
  check_artifacts_committed()   { echo "check_artifacts_committed"   >> "$calls_file"; return 0; }
  detect_execution_mode()       { echo "detect_execution_mode"       >> "$calls_file"; echo "lightweight"; }
  setup_execution_workspace()   { echo "setup_execution_workspace"   >> "$calls_file"; echo "/tmp/wt/x"; }
  generate_implementation_plan(){ echo "generate_implementation_plan" >> "$calls_file"; echo "7"; }
  record_iteration_status()     { echo "record_iteration_status"     >> "$calls_file"; }
  run run_ship_phase1 "/fake/root" "my-change"
  [ "$status" -eq 0 ]
  [ "$(cat "$calls_file")" = "$(printf 'read_plan_handoff\ncheck_artifacts_committed\ndetect_execution_mode\nsetup_execution_workspace\ngenerate_implementation_plan\nrecord_iteration_status')" ]
  [ "${lines[-3]}" = "MODE=lightweight" ]
  [ "${lines[-2]}" = "WT_PATH=/tmp/wt/x" ]
  [ "${lines[-1]}" = "PLAN_STEP_COUNT=7" ]
}

@test "commit gate failure aborts: no downstream calls, returns nonzero (NOT exit)" {
  source "$SHIP_PLAN"
  local calls_file="$BATS_TMPDIR/calls"
  : > "$calls_file"
  read_plan_handoff()           { echo "read_plan_handoff"           >> "$calls_file"; }
  check_artifacts_committed()   { return 1; }
  detect_execution_mode()       { echo "CALLED"                      >> "$calls_file"; echo "lightweight"; }
  setup_execution_workspace()   { echo "CALLED"                      >> "$calls_file"; echo "/tmp/wt/x"; }
  generate_implementation_plan(){ echo "CALLED"                      >> "$calls_file"; echo "7"; }
  record_iteration_status()     { echo "CALLED"                      >> "$calls_file"; }
  # Run in subshell so a hypothetical `exit 1` doesn't kill the bats harness.
  run bash -c 'source "'"$SHIP_PLAN"'"; run_ship_phase1 "/fake/root" "my-change"'
  [ "$status" -ne 0 ]
  ! grep -q "CALLED" "$calls_file"
  [[ "$output" == *"请先 commit"* ]]
}

@test "guard: direct execution blocked with actionable message" {
  run bash "$SHIP_PLAN"
  [ "$status" -eq 1 ]
  [[ "$output" == *"Source it instead"* ]]
}

@test "missing change_name: clear usage error, returns nonzero" {
  source "$SHIP_PLAN"
  run run_ship_phase1 "/fake/root"
  [ "$status" -ne 0 ]
  [[ "$output" == *"用法: run_ship_phase1"* ]]
}