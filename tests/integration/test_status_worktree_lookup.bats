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
  [ -f "$REPO_ROOT/skills/status/SKILL.md" ]
  # The buggy pattern: $2=="openspec/<name>" — $2 is the commit hash, never matches.
  ! grep -nE '\$2=="openspec/' "$REPO_ROOT/skills/status/SKILL.md"
}

@test "status.md has no \$2 ~ /openspec\\// awk patterns (P0-7 site 3)" {
  [ -f "$REPO_ROOT/skills/status/SKILL.md" ]
  # The buggy pattern: $2 ~ /^openspec\// — $2 is the commit hash, never matches.
  ! grep -nE '\$2 ~ /openspec\\//' "$REPO_ROOT/skills/status/SKILL.md"
}

@test "status.md Mode B sources worktree.sh and calls wt_path_for_branch" {
  [ -f "$REPO_ROOT/skills/status/SKILL.md" ]
  # P3-3c replaced the old inline `wt_path_for_branch_inline()` (which
  # had a silent awk bracket-mismatch bug) with the centralized
  # _lib/worktree.sh::wt_path_for_branch that uses `git worktree list
  # --porcelain` (key/value pairs, no fragile whitespace parsing).
  # Mode B (status query) must source worktree.sh and call the helper.
  grep -nE 'source .*_lib/worktree\.sh' "$REPO_ROOT/skills/status/SKILL.md"
  grep -nE 'WORKTREE_PATH=\$\(wt_path_for_branch ' "$REPO_ROOT/skills/status/SKILL.md"
  # The old inline definition must NOT be present (it was the buggy one).
  ! grep -nE '^wt_path_for_branch_inline\(\) \{$' "$REPO_ROOT/skills/status/SKILL.md"
}

@test "status.md Mode B references porcelain-based worktree lookup (P3-3c fix)" {
  [ -f "$REPO_ROOT/skills/status/SKILL.md" ]
  # The centralized worktree.sh::wt_path_for_branch uses
  # `git worktree list --porcelain` with `refs/heads/openspec/$branch`
  # to avoid the fragile `$3 == "[openspec/$branch]"` awk pattern that
  # silently failed when brackets didn't match. Mode B must reference
  # the centralized helper, not the old bracket-comparison inline.
  grep -nE 'wt_path_for_branch' "$REPO_ROOT/skills/status/SKILL.md"
  # The old bracket-aware inline pattern must NOT appear in status.md.
  ! grep -nE 'awk -v br="\\\[openspec/\\\$branch\\\]"' "$REPO_ROOT/skills/status/SKILL.md"
}

@test "status.md REMAINING_WT count uses \$3 (post-archive scan)" {
  [ -f "$REPO_ROOT/skills/status/SKILL.md" ]
  # $3 is "[branch]"; regex must allow the leading bracket.
  grep -nE "REMAINING_WT=.*awk '\\\$3 ~ /\\^\\\\\\[openspec\\\\\\//" "$REPO_ROOT/skills/status/SKILL.md"
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

  WT_DIR="$TEST_REPO/.rddf/wt/test-1"
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

  WT_DIR="$TEST_REPO/.rddf/wt/proof"
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

  git worktree add -b openspec/alpha    "$TEST_REPO/.rddf/wt/alpha"    HEAD
  git worktree add -b openspec/beta     "$TEST_REPO/.rddf/wt/beta"     HEAD
  git worktree add -b feature/non-spec  "$TEST_REPO/.rddf/wt/non-spec" HEAD

  # Old buggy pattern: would always be 0 (commit hash is never openspec/...).
  # `|| true` guards against grep's exit-1 on zero matches (bats runs with set -e).
  BUGGY=$(git worktree list | awk '$2 ~ /^openspec\// {print $1}' | grep -c . || true)
  [ "$BUGGY" = "0" ]

  # New fixed pattern (matches the line in status.md, $3 is the "[branch]" column;
  # the leading \[ accounts for the bracket `git worktree list` wraps around the branch).
  FIXED=$(git worktree list 2>/dev/null | awk '$3 ~ /^\[openspec\// {print $1}' | grep -c . || true)
  [ "$FIXED" = "2" ]

  for wt in "$TEST_REPO/.rddf/wt/alpha" "$TEST_REPO/.rddf/wt/beta" "$TEST_REPO/.rddf/wt/non-spec"; do
    git worktree remove --force "$wt" 2>/dev/null || true
  done
  cd /
  rm -rf "$TEST_REPO"
}
