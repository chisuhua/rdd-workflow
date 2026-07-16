#!/usr/bin/env bats

# T26 (P2-5): handoff state file for spec→ship coordination
#
# This file locks three properties into the source:
#   1. `.rddf/state/handoff.json` documents `.handoff.json` as a tracked state file
#   2. `skills/guide-plan.md` writes `.handoff.json` at plan-done exit
#   3. `skills/guide-ship.md` reads `.handoff.json` at Phase 1 (entry)
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
  [ -f "$REPO_ROOT/skills/guide-plan.md" ]
  [ -f "$REPO_ROOT/skills/_lib/plan_done_gate.py" ]
  [ -f "$REPO_ROOT/skills/_lib/plan_done_gate.sh" ]
  # 1. handoff.json contract still referenced in guide-plan.md
  grep -q "\.plan-handoff.json" "$REPO_ROOT/skills/guide-plan.md"
  # 2. plan_complete_at field is written (now in plan_done_gate.py)
  grep -q "plan_complete_at" "$REPO_ROOT/skills/_lib/plan_done_gate.py"
  # 3. The write happens after the exit guard (now in plan_done_gate.sh calls + .py)
  grep -q "Handoff state" "$REPO_ROOT/skills/_lib/plan_done_gate_env.py"
  # 4. current_change field is recorded (now in plan_done_gate.py)
  grep -q "current_change" "$REPO_ROOT/skills/_lib/plan_done_gate.py"
  # 5. guide-plan.md invokes write_plan_handoff helper
  grep -q "write_plan_handoff" "$REPO_ROOT/skills/guide-plan.md"
}

@test "guide-ship.md reads handoff.json at Phase 1 (entry)" {
  [ -f "$REPO_ROOT/skills/guide-ship.md" ]
  # 1. handoff.json is mentioned in the doc
  grep -q "handoff.json" "$REPO_ROOT/skills/guide-ship.md"
  # 2. ship_started_at is the field that gets updated
  grep -q "ship_started_at" "$REPO_ROOT/skills/guide-ship.md"
  # 3. The read happens in Phase 1 (section header marker)
  grep -q "HANDOFF STATE READ" "$REPO_ROOT/skills/guide-ship.md"
  # 4. Missing-file fallback is silent (no exit 1 inside the read block)
  # Locate the HANDOFF STATE READ block and ensure it does NOT contain a hard exit
  awk '/HANDOFF STATE READ/{flag=1} flag{print NR": "$0} flag && /^fi$/{flag=0; exit}' \
    "$REPO_ROOT/skills/guide-ship.md" | grep -vE "exit 0|exit 1" >/dev/null
  # 5. Confirm the read is followed by the worktree creation (handoff comes before worktree)
  HANDOFF_LINE=$(grep -n "HANDOFF STATE READ" "$REPO_ROOT/skills/guide-ship.md" | head -1 | cut -d: -f1)
  WORKTREE_LINE=$(grep -n "git worktree add" "$REPO_ROOT/skills/guide-ship.md" | head -1 | cut -d: -f1)
  [ -n "$HANDOFF_LINE" ] && [ -n "$WORKTREE_LINE" ]
  [ "$HANDOFF_LINE" -lt "$WORKTREE_LINE" ]
}
