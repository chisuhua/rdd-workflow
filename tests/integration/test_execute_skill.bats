#!/usr/bin/env bats
# tests/integration/test_execute_skill.bats
#
# Structural / metadata coverage for skills/execute/SKILL.md.
# Locks the frontmatter, the _lib/worktree.sh source, the main_repo_root
# PROJECT_ROOT fix (P0-8), and the EXECUTE_CHOICE escape hatch (P0-9).
#
# Run: bats tests/integration/test_execute_skill.bats

load ../test_helper
load_lib skill

setup() {
  f="$REPO_ROOT/skills/execute/SKILL.md"
}

@test "execute_skill has correct frontmatter" {
  [ "$(skill_field "$f" name)" = "execute" ]
}

@test "execute_skill sources _lib/worktree.sh" {
  grep -q '_lib/worktree\.sh' "$f"
}

@test "execute_skill uses main_repo_root for PROJECT_ROOT" {
  # Round A extraction: main_repo_root is now in the helper, sourced by execute.md
  grep -q 'main_repo_root' "$f" || grep -q 'main_repo_root' "$REPO_ROOT/skills/_lib/select_worktree.sh"
}

@test "execute_skill honors EXECUTE_CHOICE escape hatch" {
  # Round A extraction: EXECUTE_CHOICE is now in the helper, sourced by execute.md
  grep -q 'EXECUTE_CHOICE' "$f" || grep -q 'EXECUTE_CHOICE' "$REPO_ROOT/skills/_lib/select_worktree.sh"
  # Default value pattern: ${EXECUTE_CHOICE:-1}
  grep -qE 'EXECUTE_CHOICE:[[:space:]]*-[[:space:]]*1' "$f" || grep -qE 'EXECUTE_CHOICE:-1' "$REPO_ROOT/skills/_lib/select_worktree.sh"
}
