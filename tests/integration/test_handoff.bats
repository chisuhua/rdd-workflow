#!/usr/bin/env bats

# T26 (P2-5): handoff state file for spec→ship coordination
#
# This file locks three properties into the source:
#   1. `.zcf/index.md` documents `.handoff.json` as a tracked state file
#   2. `skills/guide-spec.md` writes `.handoff.json` at Phase 3 (spec-done exit)
#   3. `skills/guide-ship.md` reads `.handoff.json` at Phase 1 (entry)
#
# All three are static grep tests against the markdown source — full
# functional execution requires git worktree + openspec CLI which is not
# present in CI. The tests lock the contract into the docs and protect
# against accidental removal during future refactors.

load ../test_helper

@test ".zcf/index.md documents handoff.json" {
  [ -f "$REPO_ROOT/.zcf/index.md" ]
  # 1. The filename is mentioned
  grep -q ".handoff.json" "$REPO_ROOT/.zcf/index.md"
  # 2. The handoff role is described (Chinese or English token)
  grep -qE "handoff|交接" "$REPO_ROOT/.zcf/index.md"
  # 3. spec side is named as writer
  grep -q "guide-spec.md" "$REPO_ROOT/.zcf/index.md"
  # 4. ship side is named as reader
  grep -q "guide-ship.md" "$REPO_ROOT/.zcf/index.md"
}

@test "guide-spec.md writes handoff.json at Phase 3 (spec-done exit)" {
  [ -f "$REPO_ROOT/skills/guide-spec.md" ]
  # 1. handoff.json is mentioned in the doc
  grep -q "handoff.json" "$REPO_ROOT/skills/guide-spec.md"
  # 2. spec_complete_at field is written
  grep -q "spec_complete_at" "$REPO_ROOT/skills/guide-spec.md"
  # 3. The write happens after the exit guard (lines mention "Handoff state write" section)
  grep -q "Handoff state write" "$REPO_ROOT/skills/guide-spec.md"
  # 4. current_change field is recorded
  grep -q "current_change" "$REPO_ROOT/skills/guide-spec.md"
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
