#!/usr/bin/env bats
# tests/integration/test_wt_path_for_branch_dedup.bats
# P3-3c regression: status.md and execute.md both inlined a broken
# wt_path_for_branch_inline() function (status.md:230-233, execute.md:186-189).
#
# The inline version parsed `git worktree list` default format with
# awk pattern `\[openspec/<branch>\]`, but the literal string comparison
# `$3 == br` could NEVER match because $3 = `[openspec/<branch>]` (no
# leading backslash) while br = `\[openspec/<branch>\]` (literal backslash).
# This made the function ALWAYS return empty, silently breaking the
# worktree detection in both skills (HAS_WORKTREE would always be false).
#
# The library version _lib/worktree.sh::wt_path_for_branch uses
# `git worktree list --porcelain` and parses key/value pairs, working
# correctly. This refactor replaces both inline copies with the library
# version, fixing the silent bug.
#
# These tests lock:
#   1. status.md and execute.md no longer define wt_path_for_branch_inline
#   2. Library helper correctly returns worktree path for active branch
#   3. Regression: old inline would have returned empty for same scenario

load ../test_helper

@test "status.md no longer defines wt_path_for_branch_inline (P3-3c)" {
  [ -f "$REPO_ROOT/skills/status/SKILL.md" ]
  ! grep -q 'wt_path_for_branch_inline()' "$REPO_ROOT/skills/status/SKILL.md"
}

@test "execute.md no longer defines wt_path_for_branch_inline (P3-3c)" {
  [ -f "$REPO_ROOT/skills/execute/SKILL.md" ]
  ! grep -q 'wt_path_for_branch_inline()' "$REPO_ROOT/skills/execute/SKILL.md"
}

@test "status.md invokes wt_path_for_branch from _lib/worktree.sh" {
  [ -f "$REPO_ROOT/skills/status/SKILL.md" ]
  grep -qE '_lib/worktree\.sh|source.*worktree\.sh|wt_path_for_branch' "$REPO_ROOT/skills/status/SKILL.md"
}

@test "execute.md invokes wt_path_for_branch from _lib/worktree.sh" {
  [ -f "$REPO_ROOT/skills/execute/SKILL.md" ]
  grep -qE '_lib/worktree\.sh|source.*worktree\.sh|wt_path_for_branch' "$REPO_ROOT/skills/execute/SKILL.md"
}

@test "_lib/worktree.sh::wt_path_for_branch returns correct path (was broken in inline version)" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  git init -q -b master
  git config user.email "t@t"
  git config user.name "t"
  echo "x" > README.md && git add . && git commit -q -m "init"
  git worktree add -b openspec/test-change .rddf/wt/test-change HEAD >/dev/null 2>&1
  source "$REPO_ROOT/skills/_lib/worktree.sh"
  result=$(wt_path_for_branch "test-change")
  rm -rf "$TEST_REPO"
  [ "$result" = "$TEST_REPO/.rddf/wt/test-change" ]
}

@test "REGRESSION: old inline version would have returned empty (documented silent bug)" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  git init -q -b master
  git config user.email "t@t"
  git config user.name "t"
  echo "x" > README.md && git add . && git commit -q -m "init"
  git worktree add -b openspec/test-change .rddf/wt/test-change HEAD >/dev/null 2>&1
  # Simulate the BROKEN inline version exactly as it appears in status.md
  inline_result=$(git worktree list 2>/dev/null | awk -v br='\[openspec/test-change\]' '$3 == br {print $1; exit}')
  rm -rf "$TEST_REPO"
  [ -z "$inline_result" ]
}