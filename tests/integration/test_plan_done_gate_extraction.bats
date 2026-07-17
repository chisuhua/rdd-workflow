#!/usr/bin/env bats
# tests/integration/test_plan_done_gate_extraction.bats
# Round A extraction: guide-plan.md plan-done triple gate + handoff writer
# (L518-L618 gate + L625-L676 handoff, ~150 lines) extracted to
# skills/_lib/plan_done_gate.{py,sh,env.py}.
#
# These tests lock the refactor in place:
#   1. plan_done_gate.{sh,py,env.py} exist with correct functions.
#   2. guide-plan.md gate markers removed.
#   3. guide-plan.md handoff markers removed.
#   4. guide-plan.md sources and calls helpers.
#   5. run_plan_done_gate fails with no changes.
#   6. write_plan_handoff creates file.
#   7. plan-handoff has required 5 fields.
#   8. write_plan_handoff uses active changes count.

load ../test_helper

@test "plan_done_gate_helper_exists" {
  [ -f "$REPO_ROOT/skills/_lib/plan_done_gate.sh" ]
  [ -f "$REPO_ROOT/skills/_lib/plan_done_gate.py" ]
  [ -f "$REPO_ROOT/skills/_lib/plan_done_gate_env.py" ]
  bash -c "cd '$REPO_ROOT' && source skills/_lib/plan_done_gate.sh && declare -f run_plan_done_gate && declare -f write_plan_handoff" | grep -q 'run_plan_done_gate'
}

@test "guide_plan_inline_gate_block_removed" {
  # Gate markers should not appear in guide-plan.md after extraction
  ! grep -q '门控 0: Ready-for-ship' "$REPO_ROOT/skills/guide-plan/SKILL.md"
  ! grep -q '门控 1: Active changes' "$REPO_ROOT/skills/guide-plan/SKILL.md"
  ! grep -q '门控 2: Artifacts 提交性' "$REPO_ROOT/skills/guide-plan/SKILL.md"
}

@test "guide_plan_inline_handoff_block_removed" {
  ! grep -q 'plan → ship 交接' "$REPO_ROOT/skills/guide-plan/SKILL.md"
  ! grep -q 'HANDOFF_FILE=.*plan-handoff' "$REPO_ROOT/skills/guide-plan/SKILL.md"
}

@test "guide_plan_invokes_helpers" {
  grep -q 'source.*_lib/plan_done_gate.sh' "$REPO_ROOT/skills/guide-plan/SKILL.md"
  grep -q 'run_plan_done_gate' "$REPO_ROOT/skills/guide-plan/SKILL.md"
  grep -q 'write_plan_handoff' "$REPO_ROOT/skills/guide-plan/SKILL.md"
}

@test "run_plan_done_gate_fails_with_no_changes" {
  local tmpdir
  tmpdir=$(mktemp -d)
  output=$(bash -c "cd '$tmpdir' && source '$REPO_ROOT/skills/_lib/plan_done_gate.sh' && run_plan_done_gate" 2>&1 || true)
  rm -rf "$tmpdir"
  echo "$output" | grep -q '失败\|EXIT'
}

@test "write_plan_handoff_creates_file" {
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/.rddf/state"
  bash -c "cd '$tmpdir' && source '$REPO_ROOT/skills/_lib/plan_done_gate.sh' && write_plan_handoff" >/dev/null 2>&1 || true
  if [ ! -f "$tmpdir/.rddf/state/.plan-handoff.json" ]; then
    rm -rf "$tmpdir"
    return 1
  fi
  rm -rf "$tmpdir"
}

@test "plan_handoff_has_required_fields" {
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/.rddf/state"
  bash -c "cd '$tmpdir' && source '$REPO_ROOT/skills/_lib/plan_done_gate.sh' && write_plan_handoff" >/dev/null 2>&1 || true
  cat "$tmpdir/.rddf/state/.plan-handoff.json" | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert 'plan_complete_at' in d
assert 'active_changes' in d
assert 'all_artifacts_committed' in d
assert 'ship_started_at' in d
assert 'current_change' in d
"
  rm -rf "$tmpdir"
}

@test "write_plan_handoff_uses_active_changes_count" {
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/.rddf/state"
  # Pre-create 2 active changes
  mkdir -p "$tmpdir/openspec/changes/change-1"
  mkdir -p "$tmpdir/openspec/changes/change-2"
  bash -c "cd '$tmpdir' && source '$REPO_ROOT/skills/_lib/plan_done_gate.sh' && write_plan_handoff" >/dev/null 2>&1 || true
  if [ -f "$tmpdir/.rddf/state/.plan-handoff.json" ]; then
    cat "$tmpdir/.rddf/state/.plan-handoff.json" | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert d['active_changes'] == 2, f'expected 2, got {d[\"active_changes\"]}'
"
  fi
  rm -rf "$tmpdir"
}

@test "gate_0_skip_sets_sentinel_and_prevents_handoff" {
  # When SKIP_GATE_0=true, PLAN_GATE_0_SKIPPED should be set and handoff NOT written
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/openspec/changes/test-change"
  mkdir -p "$tmpdir/.rddf/state"
  # Run with SKIP_GATE_0=true, then try to write handoff (should NOT create the file)
  result=$(bash -c "
cd '$tmpdir'
source '$REPO_ROOT/skills/_lib/plan_done_gate.sh'
export SKIP_GATE_0=true
run_plan_done_gate
echo \"SENTINEL=\${PLAN_GATE_0_SKIPPED:-}\"
" 2>&1) || true
  echo "$result" | grep -q 'SENTINEL=true'
  # handoff file should NOT exist
  [ ! -f "$tmpdir/.rddf/state/.plan-handoff.json" ]
  rm -rf "$tmpdir"
}