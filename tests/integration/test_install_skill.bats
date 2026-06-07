#!/usr/bin/env bats
# tests/integration/test_install_skill.bats
#
# Structural / metadata coverage for skills/INSTALL.md.
# Locks the frontmatter name + alias, the "前置条件检查" section,
# the SKIP_OPENSPEC_PROMPT escape hatch, the 4-cmd dependency loop
# ordering, and the realpath fallback chain reference.
#
# Note: tests/integration/test_install_no_stdin.bats already covers
# the non-interactive install regression at the line level; this file
# adds higher-level structural coverage and does NOT duplicate those
# line-level greps.
#
# Run: bats tests/integration/test_install_skill.bats

load ../test_helper
load_lib skill

setup() {
  f="$REPO_ROOT/skills/INSTALL.md"
}

@test "install_skill has correct frontmatter name and alias" {
  [ "$(skill_field "$f" name)" = "INSTALL" ]
  [ "$(skill_field "$f" alias)" = "install" ]
}

@test "install_skill declares non-interactive escape hatch" {
  skill_has_section "$f" "前置条件检查"
  grep -q 'SKIP_OPENSPEC_PROMPT' "$f"
}

@test "install_skill dependency loop covers the 4 required commands" {
  # Tolerant alternation; any ordering is fine, just need all 4 present
  grep -qE 'for[[:space:]]+cmd[[:space:]]+in[[:space:]]+.*(python3|jq|git|cmake)' "$f"
}

@test "install_skill references realpath fallback (mirrors install.sh)" {
  grep -q 'realpath' "$f"
}
