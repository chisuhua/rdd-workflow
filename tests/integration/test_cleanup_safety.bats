#!/usr/bin/env bats
# tests/integration/test_cleanup_safety.bats
# P2-9 regression: cleanup Phase 4 (guide-ship.md) used unconditional `git branch -D`
# for unmerged branches, which silently destroys work. After this fix:
#   1. The cleanup references FORCE_BRANCH_DELETE env var (must be set to
#      "yes" for `-D` to run).
#   2. The cleanup captures and displays the last commit of the branch
#      before attempting delete, so the user can review what would be lost.
#
# v3.0: Cleanup logic moved to scripts/ship_cleanup.sh. Tests accept
#       references in either SKILL.md or ship_cleanup.sh.

load ../test_helper

_check_pattern() {
  local pattern="$1"
  for src in "$REPO_ROOT/skills/guide-ship/SKILL.md" \
             "$REPO_ROOT/skills/guide-ship/scripts/ship_cleanup.sh"; do
    if [ -f "$src" ] && grep -q "$pattern" "$src" 2>/dev/null; then
      return 0
    fi
  done
  return 1
}

@test "guide-ship.md cleanup uses FORCE_BRANCH_DELETE env var" {
  _check_pattern "FORCE_BRANCH_DELETE" || {
    echo "FORCE_BRANCH_DELETE not found in guide-ship.md or scripts/ship_cleanup.sh"
    return 1
  }
}

@test "guide-ship.md cleanup shows last commit before delete attempt" {
  _check_pattern "LAST_COMMIT" || {
    echo "LAST_COMMIT not found in guide-ship.md or scripts/ship_cleanup.sh"
    return 1
  }
  _check_pattern 'log -1' || {
    echo "git log pattern not found in guide-ship.md or scripts/ship_cleanup.sh"
    return 1
  }
}
