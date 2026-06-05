#!/usr/bin/env bats
#
# Wave 2 / T10: verify execute.md P0-8 path resolution fix.
# See plan checkbox:
#   - [ ] 10. execute.md worktree-aware path resolution (P0-8)
#
# P0-8: `git rev-parse --show-toplevel` returns the WORKTREE root when called
#       from inside a worktree. execute.md uses PROJECT_ROOT to construct
#       STATE_FILE="$PROJECT_ROOT/.zcf/.roadmap-state.json" (line 301). When
#       run from a worktree, this would write the state to the worktree's
#       .zcf/, not the main repo's — breaking the global state file.
#       Fix: use `git rev-parse --git-common-dir` (identical for main repo
#       and all linked worktrees) to derive the main repo root. Encapsulated
#       in `main_repo_root()` helper in skills/_lib/worktree.sh.

load ../test_helper

# Static checks (verify the source change is in place) --------------------

@test "P0-8: execute.md uses main_repo_root or --git-common-dir" {
  [ -f "skills/execute.md" ]
  # Either the helper function or the direct git command must be referenced
  grep -qE 'git rev-parse --git-common-dir|main_repo_root' skills/execute.md
}

@test "P0-8: execute.md no longer uses just --show-toplevel for PROJECT_ROOT" {
  [ -f "skills/execute.md" ]
  # The old buggy assignment must be gone
  if grep -qE 'PROJECT_ROOT=\$\(git rev-parse --show-toplevel 2>/dev/null \|\| pwd\)' skills/execute.md; then
    echo "FAIL: old --show-toplevel PROJECT_ROOT assignment still present"
    return 1
  fi
}

@test "P0-8: _lib/worktree.sh exports main_repo_root function" {
  [ -f "skills/_lib/worktree.sh" ]
  grep -q "main_repo_root" skills/_lib/worktree.sh
  # Must be defined as a function
  grep -qE '^main_repo_root\(\)' skills/_lib/worktree.sh
}

@test "P0-8: _lib tests cover main_repo_root" {
  [ -f "tests/_lib/test_worktree.bats" ]
  grep -q "main_repo_root" tests/_lib/test_worktree.bats
}

# Runtime checks (verify behavior in a real git repo + worktree) ----------

@test "P0-8: main_repo_root returns main repo from worktree" {
  source "$REPO_ROOT/skills/_lib/worktree.sh"
  # Build a scratch repo with a worktree
  local tmp
  tmp=$(mktemp -d)
  ( cd "$tmp" \
    && git init -q \
    && git config user.email "t@t" \
    && git config user.name "t" \
    && echo x > a && git add a && git commit -q -m init \
    && git worktree add -b openspec/test-1 .zcf/test-1-wt HEAD >/dev/null 2>&1
  )
  cd "$tmp/.zcf/test-1-wt"
  result=$(main_repo_root)
  [ "$result" = "$tmp" ]
  rm -rf "$tmp"
}

@test "P0-8: main_repo_root returns main repo from main repo" {
  source "$REPO_ROOT/skills/_lib/worktree.sh"
  local tmp
  tmp=$(mktemp -d)
  ( cd "$tmp" \
    && git init -q \
    && git config user.email "t@t" \
    && git config user.name "t" \
    && echo x > a && git add a && git commit -q -m init
  )
  cd "$tmp"
  result=$(main_repo_root)
  [ "$result" = "$tmp" ]
  rm -rf "$tmp"
}

@test "P0-8: STATE_FILE points to main repo .zcf (not worktree)" {
  # Simulate execute.md's fix: from worktree, PROJECT_ROOT is main repo,
  # so STATE_FILE goes to main repo's .zcf/, not the worktree's.
  source "$REPO_ROOT/skills/_lib/worktree.sh"
  local tmp wt_dir
  tmp=$(mktemp -d)
  wt_dir="$tmp/.zcf/test-1-wt"
  ( cd "$tmp" \
    && git init -q \
    && git config user.email "t@t" \
    && git config user.name "t" \
    && echo x > a && git add a && git commit -q -m init \
    && git worktree add -b openspec/test-1 "$wt_dir" HEAD >/dev/null 2>&1
  )
  cd "$wt_dir"
  PROJECT_ROOT=$(main_repo_root)
  STATE_FILE="$PROJECT_ROOT/.zcf/.roadmap-state.json"
  # Must NOT contain the worktree path
  [[ "$STATE_FILE" != *".zcf/test-1-wt"* ]]
  # Must contain the main repo path
  [[ "$STATE_FILE" == *"$tmp/.zcf/.roadmap-state.json"* ]]
  rm -rf "$tmp"
}
