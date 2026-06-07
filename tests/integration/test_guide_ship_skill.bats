#!/usr/bin/env bats
# tests/integration/test_guide_ship_skill.bats
#
# Structural / metadata coverage for skills/guide-ship.md.
# Locks the frontmatter, the prometheus-planning delegation
# (with SKIP_PROMETHEUS_PLANNING escape hatch), the execute/status
# sub-skill references, and the $3-vs-$2 branch matching fix
# (defense-in-depth, complementary to test_status_worktree_lookup.bats).
#
# Run: bats tests/integration/test_guide_ship_skill.bats

load ../test_helper
load_lib skill

setup() {
  f="$REPO_ROOT/skills/guide-ship.md"
}

@test "guide_ship_skill has correct frontmatter" {
  [ "$(skill_field "$f" name)" = "guide-ship" ]
  [ "$(skill_meta_field "$f" user-invocable)" = "true" ]
}

@test "guide_ship_skill delegates plan to prometheus-planning" {
  grep -q 'prometheus-planning' "$f"
  grep -q 'SKIP_PROMETHEUS_PLANNING' "$f"
}

@test "guide_ship_skill references execute and status sub-skills" {
  grep -q 'execute' "$f"
  grep -q 'status' "$f"
}

@test "guide_ship_skill uses \$3 (not \$2) for openspec/ branch match" {
  # Defense-in-depth: the fix for git worktree list using $3 for branch
  # (P0-7: $2 is commit hash, $3 is "[branch]"). Tolerant regex.
  grep -qE '\$3.*openspec' "$f"
}
