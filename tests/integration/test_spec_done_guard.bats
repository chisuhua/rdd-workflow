#!/usr/bin/env bats

# T14 (P1-10): guide-spec.md Phase 3 (spec-done) must refuse to exit
# when there are zero active changes in openspec/changes/ (excluding
# archive/). This prevents the "no work to ship" escape hatch where
# a user could otherwise bypass Propose → Roadmap by jumping straight
# to spec-done. Tests are static against the markdown source — full
# functional execution requires the openspec CLI which is not present
# in CI. The tests lock the guard block into the source and protect
# against regression.

load ../test_helper

@test "guide-spec.md has zero-change guard before spec-done verification" {
  [ -f "$REPO_ROOT/skills/guide-spec.md" ]
  # P1-10 guard must precede the verification loop (Phase 3 / Exit guard check).
  # The actual guard if-line is `if [ "$CHANGE_COUNT" -eq 0 ]; then` (note the
  # embedded `"` between `CHANGE_COUNT` and ` -eq`). We match it with a regex
  # that allows the intervening quote so the test locks onto the real source.
  # grep -B 1 returns the line immediately above the if-statement
  # (the CHANGE_COUNT= assignment), confirming placement before the for-loop.
  grep -B 1 'CHANGE_COUNT.*-eq 0' "$REPO_ROOT/skills/guide-spec.md" | head -1
  # grep -A 3 returns the 3 lines after the if-statement: the two echo
  # messages and the exit 1. All three must be present.
  grep -A 3 'CHANGE_COUNT.*-eq 0' "$REPO_ROOT/skills/guide-spec.md"
}

@test "guide-spec.md guard message tells user to go to Propose" {
  [ -f "$REPO_ROOT/skills/guide-spec.md" ]
  # Should mention "回到 Propose 阶段" so the user knows where to recover
  # from the zero-change refusal (back to guide-spec Phase 0 Propose).
  grep -q "回到 Propose 阶段" "$REPO_ROOT/skills/guide-spec.md"
}
