#!/usr/bin/env bats

load ../test_helper

# P1-13: guide-ship.md pre-merge check for new commits.
# After T21 refactor (_lib/archive.sh::check_worktree_commits),
# the markers may live in archive.sh instead of guide-ship.md.
# Tests accept EITHER location to be forward-compatible with the refactor.

setup() {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  git init -q
  git config user.email "test@test"
  git config user.name "test"
  echo "x" > a && git add a && git commit -q -m init
  git worktree add -b openspec/test-1 .rddf/wt/test-1 HEAD
}

teardown() {
  cd /
  rm -rf "$TEST_REPO"
}

# _premerge_marker_present <pattern>
#   Asserts <pattern> is present in guide-ship.md OR _lib/archive.sh.
_premerge_marker_present() {
  local pattern="$1"
  for f in "$REPO_ROOT/skills/guide-ship/SKILL.md" "$REPO_ROOT/_lib/archive.sh"; do
    [ -f "$f" ] && grep -q "$pattern" "$f" && return 0
  done
  return 1
}

@test "P1-13: pre-merge check verifies new commits" {
  _premerge_marker_present "rev-list --count"
}

@test "P1-13: pre-merge check uses find_default_branch helper" {
  _premerge_marker_present "find_default_branch"
}

@test "P1-13: pre-merge check exits on zero commits" {
  _premerge_marker_present "worktree 分支无新提交"
}
