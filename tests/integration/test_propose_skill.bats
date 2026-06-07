#!/usr/bin/env bats
# tests/integration/test_propose_skill.bats
#
# Structural / metadata coverage for skills/propose.md.
# Locks the frontmatter, the roadmap.md dependency, the Phase -1..4
# structure (≥5 headings), and the THIS_SESSION_CREATED auto-commit
# gating (coarse, complementary to test_propose_parsing.bats).
#
# Run: bats tests/integration/test_propose_skill.bats

load ../test_helper
load_lib skill

setup() {
  f="$REPO_ROOT/skills/propose.md"
}

@test "propose_skill has correct frontmatter" {
  [ "$(skill_field "$f" name)" = "propose" ]
  v=$(skill_meta_field "$f" version)
  [[ "$v" =~ ^[0-9]+\.[0-9]+$ ]]
}

@test "propose_skill declares roadmap.md dependency" {
  grep -q 'roadmap\.md' "$f"
}

@test "propose_skill phases span -1 through 4 (≥5 phase headings)" {
  phases=$(grep -cE '^##+[[:space:]]+Phase[[:space:]]+(-?[0-9]+)' "$f")
  [ "$phases" -ge 5 ]
}

@test "propose_skill auto-commit is gated by THIS_SESSION_CREATED" {
  grep -q 'THIS_SESSION_CREATED' "$f"
}
