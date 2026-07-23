#!/usr/bin/env bats
# tests/integration/test_archive_dedup.bats
# P1-14 regression: archive logic was duplicated between status.md Mode C
# and guide-ship.md Phase 3. Extracted to skills/_lib/archive.sh.
#
# These tests lock the refactor in place:
#   1. The helper file exists with archive_change, check_worktree_commits,
#      verify_merge_result defined.
#   2. status.md Mode C uses archive_change (not the inline 6-step flow).
#   3. guide-ship.md Phase 3 uses archive_change (not the inline 11-step
#      flow).
#   4. archive.sh sources worktree.sh for the wt_path_for_branch /
#      find_default_branch helpers.
#   5. Runtime: check_worktree_commits returns the right number / error
#      on a real scratch repo. verify_merge_result distinguishes HEAD
#      changed vs branch-ancestor-of-HEAD.

load ../test_helper

@test "skills/_lib/archive.sh exists with archive_change function" {
  [ -f "$REPO_ROOT/skills/_lib/archive.sh" ]
  grep -q "^archive_change()" "$REPO_ROOT/skills/_lib/archive.sh"
}

@test "skills/_lib/archive.sh also defines check_worktree_commits and verify_merge_result" {
  [ -f "$REPO_ROOT/skills/_lib/archive.sh" ]
  grep -q "^check_worktree_commits()" "$REPO_ROOT/skills/_lib/archive.sh"
  grep -q "^verify_merge_result()" "$REPO_ROOT/skills/_lib/archive.sh"
}

@test "archive.sh sources worktree.sh helpers" {
  [ -f "$REPO_ROOT/skills/_lib/archive.sh" ]
  grep -q "worktree.sh" "$REPO_ROOT/skills/_lib/archive.sh"
}

@test "status.md Mode C sources and uses archive.sh::archive_change" {
  [ -f "$REPO_ROOT/skills/status/SKILL.md" ]
  # Source line
  grep -nE 'source .*_lib/archive.sh' "$REPO_ROOT/skills/status/SKILL.md"
  # Call line
  grep -nE 'archive_change "' "$REPO_ROOT/skills/status/SKILL.md"
}

@test "status.md Mode C no longer inlines the 6-step archive flow (P1-14 dedup)" {
  [ -f "$REPO_ROOT/skills/status/SKILL.md" ]
  # The old code had `git merge --ff-only` and `git merge --no-ff` inline
  # in the Mode C bash block. After the refactor, these should only live
  # in archive.sh, not in status.md.
  ! grep -nE 'git merge --ff-only' "$REPO_ROOT/skills/status/SKILL.md"
  ! grep -nE 'git merge --no-ff' "$REPO_ROOT/skills/status/SKILL.md"
  # `openspec archive` may still appear in the explanatory block-quote
  # (the refactor note that documents WHAT was extracted), but it must
  # not appear as an executable command — i.e. not preceded by `^`
  # (start of line) inside a code block. We restrict the negative-grep
  # to lines that are NOT inside a markdown block-quote / comment.
  # Concretely: the only acceptable mention of `openspec archive` is in
  # the form `\`openspec archive\`` (backticked, inside the > block).
  # We assert that there is no `openspec archive <name>` style invocation.
  ! grep -nE '^openspec archive <name> --yes' "$REPO_ROOT/skills/status/SKILL.md"
}

@test "guide-ship.md Phase 3 sources and uses archive.sh::archive_change" {
  [ -f "$REPO_ROOT/skills/guide-ship/SKILL.md" ]
  local found=0
  # v3.0: source path moved to scripts/ship_archive.sh (was _lib/archive.sh)
  if grep -nE 'source .*archive.sh' "$REPO_ROOT/skills/guide-ship/SKILL.md" >/dev/null 2>&1; then
    found=1
  fi
  # Call line (either in SKILL.md or ship_archive.sh)
  if grep -nE 'archive_change[[:space:]]+"?\$CHANGE_NAME' "$REPO_ROOT/skills/guide-ship/SKILL.md" >/dev/null 2>&1; then
    found=1
  fi
  if [ -f "$REPO_ROOT/skills/guide-ship/scripts/ship_archive.sh" ] && \
     grep -nE 'archive_change' "$REPO_ROOT/skills/guide-ship/scripts/ship_archive.sh" >/dev/null 2>&1; then
    found=1
  fi
  [ "$found" -gt 0 ] || { echo "archive_change not found in guide-ship.md or scripts/ship_archive.sh"; return 1; }
}

@test "guide-ship.md Phase 3 no longer inlines pre-merge check (P1-14 dedup)" {
  [ -f "$REPO_ROOT/skills/guide-ship/SKILL.md" ]
  # The old code inlined `WORKTREE_NEW_COMMITS=$(git rev-list --count ...)`;
  # after the refactor that lives inside check_worktree_commits.
  # We still expect the P0 FIX detached-HEAD check to remain (it is
  # caller-specific to guide-ship), but the post-merge verify block
  # (BEFORE_MERGE/AFTER_MERGE) is now inside verify_merge_result.
  ! grep -nE '^BEFORE_MERGE=' "$REPO_ROOT/skills/guide-ship/SKILL.md"
  ! grep -nE '^AFTER_MERGE=' "$REPO_ROOT/skills/guide-ship/SKILL.md"
}

@test "guide-ship.md Phase 3 keeps the P0 FIX detached-HEAD check (caller-specific)" {
  [ -f "$REPO_ROOT/skills/guide-ship/SKILL.md" ]
  local found=0
  # v3.0: check may be in guide-ship/SKILL.md or scripts/ship_archive.sh
  for src in "$REPO_ROOT/skills/guide-ship/SKILL.md" "$REPO_ROOT/skills/guide-ship/scripts/ship_archive.sh"; do
    if [ -f "$src" ] && grep -nE 'detach|DETACHED' "$src" 2>/dev/null | grep -q .; then
      found=1
      break
    fi
  done
  [ "$found" -gt 0 ] || { echo "detached-HEAD check not found in guide-ship.md or scripts/ship_archive.sh"; return 1; }
  # Also check the error message exists (either in .md or .sh)
  local msg_found=0
  for src in "$REPO_ROOT/skills/guide-ship/SKILL.md" "$REPO_ROOT/skills/guide-ship/scripts/ship_archive.sh"; do
    if [ -f "$src" ] && grep -nE 'detached HEAD' "$src" 2>/dev/null | grep -q .; then
      msg_found=1
      break
    fi
  done
  [ "$msg_found" -gt 0 ] || { echo "detached HEAD error message not found"; return 1; }
}

@test "check_worktree_commits: returns commit count when branch has new commits" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO" || return 1
  git init -q
  git config user.email "test@test"
  git config user.name  "test"
  echo "x" > a && git add a && git commit -q -m "init"
  git checkout -b openspec/test-1 2>/dev/null
  echo "y" > b && git add b && git commit -q -m "feat: b"
  git checkout master 2>/dev/null || git checkout main 2>/dev/null

  # Source the helper from the rdd-workflow repo
  source "$REPO_ROOT/skills/_lib/archive.sh"

  run check_worktree_commits test-1
  [ "$status" -eq 0 ]
  [ "$output" = "1" ]

  cd /
  rm -rf "$TEST_REPO"
}

@test "check_worktree_commits: exits 1 with clear error when branch missing" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO" || return 1
  git init -q
  git config user.email "test@test"
  git config user.name  "test"
  echo "x" > a && git add a && git commit -q -m "init"

  source "$REPO_ROOT/skills/_lib/archive.sh"

  run check_worktree_commits does-not-exist
  [ "$status" -eq 1 ]
  [[ "$output" == *"不存在"* ]]

  cd /
  rm -rf "$TEST_REPO"
}

@test "check_worktree_commits: exits 1 when worktree branch has zero new commits" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO" || return 1
  git init -q
  git config user.email "test@test"
  git config user.name  "test"
  echo "x" > a && git add a && git commit -q -m "init"
  # Create branch at HEAD — no new commits
  git branch openspec/test-1 HEAD

  source "$REPO_ROOT/skills/_lib/archive.sh"

  run check_worktree_commits test-1
  [ "$status" -eq 1 ]
  [[ "$output" == *"无新提交"* ]]

  cd /
  rm -rf "$TEST_REPO"
}

@test "verify_merge_result: exits 0 when HEAD changed" {
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

  BEFORE=$(git rev-parse HEAD)
  git merge --ff-only openspec/test-1 >/dev/null 2>&1
  AFTER=$(git rev-parse HEAD)
  [ "$BEFORE" != "$AFTER" ]

  run verify_merge_result "$BEFORE" "$AFTER" test-1
  [ "$status" -eq 0 ]

  cd /
  rm -rf "$TEST_REPO"
}

@test "verify_merge_result: exits 0 with warning when branch is ancestor of HEAD" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO" || return 1
  git init -q
  git config user.email "test@test"
  git config user.name  "test"
  echo "x" > a && git add a && git commit -q -m "init"
  git checkout -b openspec/test-1 2>/dev/null
  echo "y" > b && git add b && git commit -q -m "feat: b"
  # Merge into main
  git checkout master 2>/dev/null || git checkout main 2>/dev/null
  git merge --ff-only openspec/test-1 >/dev/null 2>&1
  # After merge, branch is ancestor of HEAD. HEAD has not changed since.
  SAME=$(git rev-parse HEAD)
  source "$REPO_ROOT/skills/_lib/archive.sh"

  run verify_merge_result "$SAME" "$SAME" test-1
  [ "$status" -eq 0 ]
  [[ "$output" == *"祖先"* ]]

  cd /
  rm -rf "$TEST_REPO"
}
