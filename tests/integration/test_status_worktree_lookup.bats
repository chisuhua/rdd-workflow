#!/usr/bin/env bats
# tests/integration/test_status_worktree_lookup.bats
# P0-7 regression: status.md used `awk '$2==openspec/...'` where $2 is the commit
# hash column of `git worktree list`, never the branch. That made WORKTREE_PATH
# always empty so worktree-aware steps silently skipped themselves.
#
# These tests guard the three formerly-buggy sites:
#   - line 144: WORKTREE_PATH lookup in 状态查询 (status query)
#   - line 281: WORKTREE_PATH lookup in 归档前检查 (pre-archive check)
#   - line 387: REMAINING_WT count after archive

load ../test_helper

@test "status.md has no \$2==openspec/ awk patterns (P0-7 site 1+2)" {
  [ -f "$REPO_ROOT/skills/status.md" ]
  # The buggy pattern: $2=="openspec/<name>" — $2 is the commit hash, never matches.
  ! grep -nE '\$2=="openspec/' "$REPO_ROOT/skills/status.md"
}

@test "status.md has no \$2 ~ /openspec\\// awk patterns (P0-7 site 3)" {
  [ -f "$REPO_ROOT/skills/status.md" ]
  # The buggy pattern: $2 ~ /^openspec\// — $2 is the commit hash, never matches.
  ! grep -nE '\$2 ~ /openspec\\//' "$REPO_ROOT/skills/status.md"
}

@test "status.md inline helper exists at Mode B (status query) site" {
  [ -f "$REPO_ROOT/skills/status.md" ]
  # P1-14 (T21) refactored Mode C archive flow to use the centralized
  # _lib/archive.sh::archive_change helper, so the inline helper is no
  # longer needed in Mode C. It must still exist for the Mode B status
  # query (line ~146) where the caller needs the raw worktree path
  # before running the Mode B detection logic.
  local helper_defs
  helper_defs=$(grep -cE '^wt_path_for_branch_inline\(\) \{$' "$REPO_ROOT/skills/status.md")
  [ "$helper_defs" -ge 1 ]
  local helper_calls
  helper_calls=$(grep -cE 'WORKTREE_PATH=\$\(wt_path_for_branch_inline' "$REPO_ROOT/skills/status.md")
  [ "$helper_calls" -ge 1 ]
}

@test "status.md inline helper compares to bracketed branch column" {
  [ -f "$REPO_ROOT/skills/status.md" ]
  # `git worktree list` outputs `path  hash  [branch]` — so $3 is "[branch]".
  # The helper must include the brackets in the comparison, otherwise the
  # lookup silently fails (the very bug P0-7 was supposed to fix).
  grep -nE 'awk -v br="\[openspec/\$branch\]"' "$REPO_ROOT/skills/status.md"
}

@test "status.md REMAINING_WT count uses \$3 (post-archive scan)" {
  [ -f "$REPO_ROOT/skills/status.md" ]
  # $3 is "[branch]"; regex must allow the leading bracket.
  grep -nE "REMAINING_WT=.*awk '\\\$3 ~ /\\^\\\\\\[openspec\\\\\\//" "$REPO_ROOT/skills/status.md"
}

@test "inline helper returns the worktree path in a real git repo" {
  # Reproduce the inlined helper verbatim from status.md and assert it
  # returns the expected worktree path. Protects against a future edit
  # that re-introduces the $2 typo or drops the brackets.
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO" || return 1
  git init -q
  git config user.email "test@test"
  git config user.name  "test"
  echo "initial" > README.md
  git add . && git commit -q -m "initial"

  WT_DIR="$TEST_REPO/.zcf/test-1-wt"
  git worktree add -b openspec/test-1 "$WT_DIR" HEAD

  # Verbatim copy of the helper from status.md (with brackets around the branch):
  wt_path_for_branch_inline() {
    local branch="${1:-}"
    [[ -z "$branch" ]] && return 1
    git worktree list 2>/dev/null | awk -v br="[openspec/$branch]" '$3 == br {print $1; exit}'
  }

  run wt_path_for_branch_inline "test-1"
  [ "$status" -eq 0 ]
  [ "$output" = "$WT_DIR" ]

  # Negative case: nonexistent branch returns empty.
  run wt_path_for_branch_inline "does-not-exist"
  [ "$status" -eq 0 ]
  [ -z "$output" ]

  git worktree remove --force "$WT_DIR" 2>/dev/null || true
  cd /
  rm -rf "$TEST_REPO"
}

@test "old \$2==openspec/ pattern is empty even when worktree exists (P0-7 reproducer)" {
  # Direct repro of the original P0-7 bug: with the old `$2=="openspec/..."`
  # pattern, the var was always empty even when the worktree existed.
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO" || return 1
  git init -q
  git config user.email "test@test"
  git config user.name  "test"
  echo "initial" > README.md
  git add . && git commit -q -m "initial"

  WT_DIR="$TEST_REPO/.zcf/proof-wt"
  git worktree add -b openspec/proof "$WT_DIR" HEAD

  # Old buggy pattern (kept for documentation; would always be empty):
  BUGGY=$(git worktree list | awk '$2=="openspec/proof" {print $1}')
  [ -z "$BUGGY" ]

  # New fixed pattern (matches the helper from status.md, with brackets):
  FIXED=$(git worktree list 2>/dev/null | awk -v br="[openspec/proof]" '$3 == br {print $1; exit}')
  [ "$FIXED" = "$WT_DIR" ]

  git worktree remove --force "$WT_DIR" 2>/dev/null || true
  cd /
  rm -rf "$TEST_REPO"
}

@test "REMAINING_WT pattern correctly counts openspec worktrees" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO" || return 1
  git init -q
  git config user.email "test@test"
  git config user.name  "test"
  echo "initial" > README.md
  git add . && git commit -q -m "initial"

  git worktree add -b openspec/alpha    "$TEST_REPO/.zcf/alpha-wt"    HEAD
  git worktree add -b openspec/beta     "$TEST_REPO/.zcf/beta-wt"     HEAD
  git worktree add -b feature/non-spec  "$TEST_REPO/.zcf/non-spec-wt" HEAD

  # Old buggy pattern: would always be 0 (commit hash is never openspec/...).
  # `|| true` guards against grep's exit-1 on zero matches (bats runs with set -e).
  BUGGY=$(git worktree list | awk '$2 ~ /^openspec\// {print $1}' | grep -c . || true)
  [ "$BUGGY" = "0" ]

  # New fixed pattern (matches the line in status.md, $3 is the "[branch]" column;
  # the leading \[ accounts for the bracket `git worktree list` wraps around the branch).
  FIXED=$(git worktree list 2>/dev/null | awk '$3 ~ /^\[openspec\// {print $1}' | grep -c . || true)
  [ "$FIXED" = "2" ]

  for wt in "$TEST_REPO/.zcf/alpha-wt" "$TEST_REPO/.zcf/beta-wt" "$TEST_REPO/.zcf/non-spec-wt"; do
    git worktree remove --force "$wt" 2>/dev/null || true
  done
  cd /
  rm -rf "$TEST_REPO"
}
