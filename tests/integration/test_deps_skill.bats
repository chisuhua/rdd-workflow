#!/usr/bin/env bats
# tests/integration/test_deps_skill.bats
#
# Structural / metadata coverage for skills/deps/SKILL.md.
# Locks the frontmatter, the proposal/design/specs input surface,
# the Mermaid output format, and the AI 语义分析未启用 disclaimer
# (P2-4, defense-in-depth, complementary to test_ai_disclaimer.bats).
#
# Run: bats tests/integration/test_deps_skill.bats

load ../test_helper
load_lib skill

setup() {
  f="$REPO_ROOT/skills/deps/SKILL.md"
}

@test "deps_skill has correct frontmatter" {
  [ "$(skill_field "$f" name)" = "deps" ]
}

@test "deps_skill reads proposal.md / design.md / specs/" {
  grep -q 'proposal\.md' "$f"
  grep -q 'design\.md' "$f"
  grep -q 'specs/' "$f"
}

@test "deps_skill generates Mermaid output" {
  grep -qiE 'mermaid' "$f"
}

@test "deps_skill disclaims AI semantic analysis" {
  grep -q 'AI 语义分析未启用' "$f"
}
