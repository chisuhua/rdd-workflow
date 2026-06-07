#!/usr/bin/env bats
# tests/integration/test_guide_skill.bats
#
# Structural / metadata coverage for skills/guide.md.
# Locks the frontmatter (name + user-invocable), the "无状态/只读不写"
# self-declarations, the 6-priority scan (RECOMMEND= branches), and
# that all RECOMMEND values are valid delegations.
#
# Run: bats tests/integration/test_guide_skill.bats

load ../test_helper
load_lib skill

setup() {
  f="$REPO_ROOT/skills/guide.md"
}

@test "guide_skill has correct frontmatter" {
  [ "$(skill_field "$f" name)" = "guide" ]
  [ "$(skill_meta_field "$f" user-invocable)" = "true" ]
}

@test "guide_skill declares itself stateless and read-only" {
  grep -q '无状态' "$f"
  grep -q '只读不写' "$f"
}

@test "guide_skill scan covers all 6 priorities (RECOMMEND branches)" {
  # Each scan branch assigns RECOMMEND=...
  rec_count=$(grep -cE '^[[:space:]]*RECOMMEND=' "$f")
  [ "$rec_count" -ge 6 ]
}

@test "guide_skill delegates only to guide-spec / guide-ship / status --roadmap" {
  # All RECOMMEND= assignments must use one of the three valid values
  bad=$(grep -E '^[[:space:]]*RECOMMEND=' "$f" | \
        grep -vE 'RECOMMEND="(guide-spec|guide-ship|status --roadmap)"' || true)
  [ -z "$bad" ]
}
