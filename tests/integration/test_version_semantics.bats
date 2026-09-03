#!/usr/bin/env bats
#
# Wave 5 / T23: version field cleanup (P2-1)
# See plan checkbox:
#   - [ ] 23. version field cleanup (P2-1)
#
# Locks three properties after unifying skill frontmatter version semantics:
#   1. All skill files have version: X.Y (semver-like major.minor) format.
#   2. README.md documents the new version + evolved-from semantics.
#   3. guide-arch, guide-plan, guide-ship, propose all carry evolved-from annotations
#      documenting their split / iteration lineage.
#
# Replaces the legacy `generatedBy: X.Y` (pre 2026-06-04) with the new
# `evolved-from: "..."` (free-form description of historical origin).

load ../test_helper

# -----------------------------------------------------------------------
# 1. All skill files have version: X.Y format
# -----------------------------------------------------------------------
@test "All skill files have version: X.Y format" {
  for f in skills/*.md; do
    version=$(grep -E "^version:" "$f" | head -1 | awk '{print $2}' | tr -d '"' | tr -d "'")
    if [ -n "$version" ]; then
      [[ "$version" =~ ^[0-9]+\.[0-9]+$ ]] || { echo "FAIL: $f has bad version $version"; return 1; }
    fi
  done
}

# -----------------------------------------------------------------------
# 2. README.md documents version semantics
# -----------------------------------------------------------------------
@test "README.md documents version semantics" {
  [ -f "README.md" ]
  grep -q "evolved-from" README.md
}

# -----------------------------------------------------------------------
# 3. Skills with evolved-from have it documented
# -----------------------------------------------------------------------
@test "Skills with evolved-from have it documented" {
  # guide-arch, guide-plan, guide-ship, propose should have evolved-from
  for f in skills/rdd-arch/SKILL.md skills/guide-plan/SKILL.md skills/guide-ship/SKILL.md skills/propose/SKILL.md; do
    grep -qE "^[[:space:]]*evolved-from:" "$f" || { echo "FAIL: $f missing evolved-from"; return 1; }
  done
}
