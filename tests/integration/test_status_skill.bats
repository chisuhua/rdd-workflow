#!/usr/bin/env bats
# tests/integration/test_status_skill.bats
#
# Structural / metadata coverage for skills/status.md.
# Locks the frontmatter, the 4-mode structure (Mode A/B/C/D), the
# $3 branch matching fix (P0-7, defense-in-depth), and the --roadmap
# flag documentation.
#
# Run: bats tests/integration/test_status_skill.bats

load ../test_helper
load_lib skill

setup() {
  f="$REPO_ROOT/skills/status.md"
}

@test "status_skill has correct frontmatter" {
  [ "$(skill_field "$f" name)" = "status" ]
}

@test "status_skill declares 4 modes" {
  # Matches both English "Mode A/B/C/D" and Chinese "模式 A/B/C/D"
  modes=$(grep -cE '(Mode|模式)[[:space:]]+[A-D]' "$f")
  [ "$modes" -ge 4 ]
}

@test "status_skill uses \$3 for branch matching (P0-7 fix)" {
  # Defense-in-depth: P0-7 documented that $2 is commit hash, $3 is "[branch]".
  # Tolerant regex — just confirm $3 appears in a branch-matching context.
  grep -qE '\$3.*openspec' "$f"
}

@test "status_skill --roadmap flag is documented" {
  grep -q -- '--roadmap' "$f"
}
