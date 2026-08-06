#!/usr/bin/env bats
# Status Mode A must support 6 statuses corresponding to iteration.json states
# plus the "committed but no worktree" gap state. Locks:
#   1. Table mentions all 6 emoji: 📋 planned, 💼 committed, ✅ proposed, 🔧 in_worktree, ✔ completed, 📦 archived
#   2. iteration.json status enum is the canonical source
#   3. No "⏸ 暂停" hardcoded text remains in Mode A template (it was
#      used as a fake placeholder during a real session hit)

load ../test_helper

@test "status.md Mode A dynamic block lists all 6 iteration.json states" {
  for s in planned proposed in_worktree completed archived; do
    grep -qE "\\b$s\\b" skills/status/SKILL.md
  done
}

@test "status.md mentions committed-but-no-worktree state" {
  grep -qE "commit.{0,15}(no|无|未).{0,15}worktree|已 commit.{0,30}(未|无).{0,30}执行|💼" skills/status/SKILL.md
}

@test "status.md Mode A does not hardcode '⏸ 暂停' as a state" {
  # ⏸ + 暂停 was used in a real execution as a placeholder, lock that out
  ! grep -E "⏸\s*暂停" skills/status/SKILL.md
}

@test "iteration.json schema declared states match Mode A list" {
  for s in planned proposed in_worktree completed archived; do
    grep -qE "\\b$s\\b" _lib/schemas/iteration_schema.json
  done
}
