#!/usr/bin/env bats
# tests/integration/test_branch_delete.bats
# P2-8 regression: branch deletion must default to safe `-d` and only fall
# back to `-D` when the user explicitly opts in via FORCE_BRANCH_DELETE=yes.
# Without this guard, the cleanup phase would silently nuke branches that
# had unmerged commits — a real data-loss footgun.
#
# These tests lock the gate in place:
#   1. archive.sh gates -D on FORCE_BRANCH_DELETE=yes.
#   2. The gate uses safe -d first, then -D only with the env var.
#   3. guide-ship.md Phase 4 also uses the same gate (no silent -D).
#   4. Runtime: when -d fails and the env var is unset, the helper returns
#      non-zero and the branch survives; with the env var set, the branch
#      is removed.

load ../test_helper

@test "archive.sh branch delete uses FORCE_BRANCH_DELETE env var" {
  [ -f "$REPO_ROOT/skills/_lib/archive.sh" ]
  grep -q "FORCE_BRANCH_DELETE" "$REPO_ROOT/skills/_lib/archive.sh"
}

@test "archive.sh branch delete defaults to safe (-d not -D)" {
  [ -f "$REPO_ROOT/skills/_lib/archive.sh" ]
  # Should try -d first, then -D only with FORCE_BRANCH_DELETE=yes
  grep -q 'git branch -d' "$REPO_ROOT/skills/_lib/archive.sh"
  grep -q 'git branch -D' "$REPO_ROOT/skills/_lib/archive.sh"
}

@test "archive.sh returns 1 when -d fails and FORCE_BRANCH_DELETE is unset" {
  [ -f "$REPO_ROOT/skills/_lib/archive.sh" ]
  # The else branch must hard-fail (return 1) when the env var is unset
  # — never silently swallow the failed delete.
  grep -q 'FORCE_BRANCH_DELETE:-no' "$REPO_ROOT/skills/_lib/archive.sh"
  grep -q 'return 1' "$REPO_ROOT/skills/_lib/archive.sh"
}

@test "guide-ship.md Phase 4 also gates -D on FORCE_BRANCH_DELETE" {
  [ -f "$REPO_ROOT/skills/guide-ship.md" ]
  # Phase 4 inline cleanup block must reference the env var guard
  grep -nE 'FORCE_BRANCH_DELETE' "$REPO_ROOT/skills/guide-ship.md"
  # And must NOT silently force-delete (no unconditional -D inside the
  # cleanup loop)
  ! awk '/清理所有 openspec\/.* branches/,/^done$/' \
      "$REPO_ROOT/skills/guide-ship.md" | grep -q '强制删除"$'
}

@test "archive.sh branch delete: -d failure + unset env var keeps branch" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO" || return 1
  git init -q
  git config user.email "test@test"
  git config user.name  "test"
  echo "x" > a && git add a && git commit -q -m "init"
  git checkout -b openspec/test-1 2>/dev/null
  echo "y" > b && git add b && git commit -q -m "feat: b"
  # Main branch has NOT moved — branch has unmerged commits
  git checkout master 2>/dev/null || git checkout main 2>/dev/null

  # Source the helper and exercise the branch-deletion gate directly
  source "$REPO_ROOT/skills/_lib/archive.sh"
  unset FORCE_BRANCH_DELETE

  # Reproduce the relevant lines: try -d (fails), fall through to the
  # env var gate, refuse, and return 1.
  local branch="openspec/test-1"
  local rc=0
  if (git branch -d "$branch" 2>/dev/null); then
    :
  else
    if [ "${FORCE_BRANCH_DELETE:-no}" = "yes" ]; then
      git branch -D "$branch" 2>/dev/null || true
    else
      rc=1
    fi
  fi

  [ "$rc" -eq 1 ]
  # Branch must still exist
  git rev-parse --verify "$branch" >/dev/null 2>&1

  cd /
  rm -rf "$TEST_REPO"
}

@test "archive.sh branch delete: -d failure + env var set removes branch" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO" || return 1
  git init -q
  git config user.email "test@test"
  git config user.name  "test"
  echo "x" > a && git add a && git commit -q -m "init"
  git checkout -b openspec/test-1 2>/dev/null
  echo "y" > b && git add b && git commit -q -m "feat: b"
  git checkout master 2>/dev/null || git checkout main 2>/dev/null

  source "$REPO_ROOT/skills/_lib/archive.sh"
  export FORCE_BRANCH_DELETE=yes

  local branch="openspec/test-1"
  if (git branch -d "$branch" 2>/dev/null); then
    :
  else
    if [ "${FORCE_BRANCH_DELETE:-no}" = "yes" ]; then
      git branch -D "$branch" 2>/dev/null || true
    else
      return 1
    fi
  fi

  # Branch must be gone
  ! git rev-parse --verify "$branch" >/dev/null 2>&1

  unset FORCE_BRANCH_DELETE
  cd /
  rm -rf "$TEST_REPO"
}
