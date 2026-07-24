#!/usr/bin/env bats

# T26 (P2-5): handoff state file for spec→ship coordination
#
# This file locks three properties into the source:
#   1. `.rddf/state/handoff.json` documents `.handoff.json` as a tracked state file
#   2. `skills/guide-plan/SKILL.md` writes `.handoff.json` at plan-done exit
#   3. `skills/guide-ship/SKILL.md` reads `.handoff.json` at Phase 1 (entry)
#
# All three are static grep tests against the markdown source — full
# functional execution requires git worktree + openspec CLI which is not
# present in CI. The tests lock the contract into the docs and protect
# against accidental removal during future refactors.

load ../test_helper

@test ".rddf/state/index.md documents handoff.json" {
  [ -f "$REPO_ROOT/.rddf/state/index.md" ]
  # 1. The filename is mentioned
  grep -q ".handoff.json" "$REPO_ROOT/.rddf/state/index.md"
  # 2. The handoff role is described (Chinese or English token)
  grep -qE "handoff|交接" "$REPO_ROOT/.rddf/state/index.md"
  # 3. plan side is named as writer
  grep -q "guide-plan.md" "$REPO_ROOT/.rddf/state/index.md"
  # 4. ship side is named as reader
  grep -q "guide-ship.md" "$REPO_ROOT/.rddf/state/index.md"
}

@test "guide-plan.md writes handoff.json at plan-done exit" {
  # After Round A extraction, the handoff implementation lives in _lib/plan_done_gate.{py,sh}
  # while guide-plan.md still references .plan-handoff.json at the contract level.
  [ -f "$REPO_ROOT/skills/guide-plan/SKILL.md" ]
  [ -f "$REPO_ROOT/skills/guide-plan/scripts/plan_done_gate.py" ]
  [ -f "$REPO_ROOT/skills/guide-plan/scripts/plan_done_gate.sh" ]
  # 1. handoff.json contract still referenced in guide-plan.md
  grep -q "\.plan-handoff.json" "$REPO_ROOT/skills/guide-plan/SKILL.md"
  # 2. plan_complete_at field is written (now in plan_done_gate.py)
  grep -q "plan_complete_at" "$REPO_ROOT/skills/guide-plan/scripts/plan_done_gate.py"
  # 3. The write happens after the exit guard (now in plan_done_gate.sh calls + .py)
  grep -q "Handoff state" "$REPO_ROOT/skills/guide-plan/scripts/plan_done_gate_env.py"
  # 4. current_change field is recorded (now in plan_done_gate.py)
  grep -q "current_change" "$REPO_ROOT/skills/guide-plan/scripts/plan_done_gate.py"
  # 5. guide-plan.md invokes write_plan_handoff helper
  grep -q "write_plan_handoff" "$REPO_ROOT/skills/guide-plan/SKILL.md"
}

@test "guide-ship.md reads handoff.json at Phase 1 (entry)" {
  # v2.0.8: handoff read logic lives in scripts/ship_plan.sh::read_plan_handoff;
  # SKILL.md is a thin orchestrator that calls it at Phase 1 entry (step 0).
  [ -f "$REPO_ROOT/skills/guide-ship/SKILL.md" ]
  [ -f "$REPO_ROOT/skills/guide-ship/scripts/ship_plan.sh" ]
  # 1. handoff.json contract referenced in the ship_plan.sh helper
  grep -q "\.plan-handoff.json" "$REPO_ROOT/skills/guide-ship/scripts/ship_plan.sh"
  # 2. ship_started_at is the field that gets updated (in the helper)
  grep -q "ship_started_at" "$REPO_ROOT/skills/guide-ship/scripts/ship_plan.sh"
  # 3. The read function exists in the helper
  grep -q "read_plan_handoff" "$REPO_ROOT/skills/guide-ship/scripts/ship_plan.sh"
  # 4. SKILL.md invokes read_plan_handoff at Phase 1 entry
  grep -q "read_plan_handoff" "$REPO_ROOT/skills/guide-ship/SKILL.md"
  # 5. Missing-file fallback is silent (no exit 1 in the read function body)
  #    The function returns 0 early if the file is missing.
  awk '/^read_plan_handoff\(\)/{flag=1} flag{print NR": "$0} flag && /^}$/{flag=0; exit}' \
    "$REPO_ROOT/skills/guide-ship/scripts/ship_plan.sh" | grep -vE "exit 1" >/dev/null
  # 6. Confirm the read happens before worktree creation (handoff called before setup_execution_workspace)
  HANDOFF_LINE=$(grep -n "read_plan_handoff" "$REPO_ROOT/skills/guide-ship/SKILL.md" | head -1 | cut -d: -f1)
  WORKTREE_LINE=$(grep -n "setup_execution_workspace\|git worktree add" "$REPO_ROOT/skills/guide-ship/SKILL.md" | head -1 | cut -d: -f1)
  [ -n "$HANDOFF_LINE" ] && [ -n "$WORKTREE_LINE" ]
  [ "$HANDOFF_LINE" -lt "$WORKTREE_LINE" ]
}
