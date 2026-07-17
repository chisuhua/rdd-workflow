#!/usr/bin/env bats
# tests/integration/test_cleanup_safety.bats
# P2-9 regression: cleanup Phase 4 (guide-ship.md) used unconditional `git branch -D`
# for unmerged branches, which silently destroys work. After this fix:
#   1. The cleanup block references FORCE_BRANCH_DELETE env var (must be set to
#      "yes" for `-D` to run).
#   2. The cleanup block captures and displays the last commit of the branch
#      before attempting delete, so the user can review what would be lost.

load ../test_helper

@test "guide-ship.md cleanup uses FORCE_BRANCH_DELETE env var" {
  [ -f "$REPO_ROOT/skills/guide-ship/SKILL.md" ]
  grep -q "FORCE_BRANCH_DELETE" "$REPO_ROOT/skills/guide-ship/SKILL.md"
}

@test "guide-ship.md cleanup shows last commit before delete attempt" {
  [ -f "$REPO_ROOT/skills/guide-ship/SKILL.md" ]
  grep -q "LAST_COMMIT" "$REPO_ROOT/skills/guide-ship/SKILL.md"
  grep -q 'git log -1 --format' "$REPO_ROOT/skills/guide-ship/SKILL.md"
}
