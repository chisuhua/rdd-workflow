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

@test "guide_skill scan covers all 11 priorities (RECOMMEND branches)" {
  # Each scan branch assigns RECOMMEND=...  v2.0.1+: scan logic lives in
  # skills/_lib/scan-state.sh (extracted from guide.md). The 11-branch
  # priority chain emits 11 RECOMMEND= assignments; count them there.
  rec_count=$(grep -cE '^[[:space:]]*RECOMMEND=' "$REPO_ROOT/skills/_lib/scan-state.sh")
  [ "$rec_count" -ge 11 ]
}

@test "guide_skill delegates only to 3-phase skills (RECOMMEND whitelist)" {
  # v2.0.1+: RECOMMEND assignments live in scan-state.sh, not guide.md.
  # Whitelist covers all 3-phase arch→plan→ship values + guide-spec alias.
  bad=$(grep -E '^[[:space:]]*RECOMMEND=' "$REPO_ROOT/skills/_lib/scan-state.sh" | \
        grep -vE 'RECOMMEND="(guide-plan|guide-arch|guide-ship|status --roadmap)"' || true)
  [ -z "$bad" ]
}
