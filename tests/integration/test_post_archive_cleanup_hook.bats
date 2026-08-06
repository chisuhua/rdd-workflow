#!/usr/bin/env bats
# tests/integration/test_post_archive_cleanup_hook.bats
# Tests for _lib/post_archive_cleanup.sh
load ../test_helper

setup() {
  TEST_TMPDIR="$(mktemp -d)"
  export PROJECT_ROOT="$TEST_TMPDIR/fake-repo"
  mkdir -p "$PROJECT_ROOT"/{_lib,openspec/changes,openspec/specs,.rddf/state}
  cd "$PROJECT_ROOT"
  git init -q -b master
  git config user.email "test@example.com"
  git config user.name "Test"
  git commit --allow-empty -m "init" -q
  # Source the hook under test
  source "$BATS_TEST_DIRNAME/../../_lib/post_archive_cleanup.sh"
}
teardown() { rm -rf "$TEST_TMPDIR"; }

# helper: create a "deleted" file (tracked then deleted)
make_deleted() {
  local p="$1"
  mkdir -p "$(dirname "$p")"
  echo "x" > "$p"
  git add "$p"
  git commit -q -m "add"
  rm "$p"
}

# helper: create a modified file
make_modified() {
  local p="$1"
  mkdir -p "$(dirname "$p")"
  echo "x" > "$p"
  git add "$p"
  git commit -q -m "add"
  echo "y" >> "$p"
}

@test "hook: deletes-tracked .rddf/plans/<name>.md" {
  make_deleted ".rddf/plans/foo.md"
  run post_archive_cleanup "$PROJECT_ROOT" "foo"
  [ "$status" -eq 0 ]
  # Now git rm-ed; commit lands
  run git log --oneline
  [[ "$output" == *"chore(post-archive): clean residue from foo"* ]]
  run git status --porcelain
  [ -z "$output" ]
}

@test "hook: idempotent — second run produces no extra commit" {
  make_deleted ".rddf/plans/foo.md"
  post_archive_cleanup "$PROJECT_ROOT" "foo"
  local commit_count_after_first
  commit_count_after_first=$(git rev-list --count HEAD)
  post_archive_cleanup "$PROJECT_ROOT" "foo"
  local commit_count_after_second
  commit_count_after_second=$(git rev-list --count HEAD)
  [ "$commit_count_after_second" -eq "$commit_count_after_first" ]
}

@test "hook: DRY_RUN=yes echoes but does not mutate" {
  make_deleted ".rddf/plans/foo.md"
  DRY_RUN_POST_ARCHIVE_CLEANUP=yes run post_archive_cleanup "$PROJECT_ROOT" "foo"
  # Echo present
  [[ "$output" == *"would git rm"* ]]
  # File still deleted-from-disk but untracked in git
  run git status --porcelain
  [[ "$output" == *" D .rddf/plans/foo.md"* ]]
  # No chore commit added
  run git log --oneline
  [[ "$output" != *"chore(post-archive)"* ]]
}

@test "hook: SKIP_POST_ARCHIVE_CLEANUP=yes early-returns 0" {
  make_deleted ".rddf/plans/foo.md"
  SKIP_POST_ARCHIVE_CLEANUP=yes run post_archive_cleanup "$PROJECT_ROOT" "foo"
  [ "$status" -eq 0 ]
  # Nothing changed
  run git status --porcelain
  [[ "$output" == *" D .rddf/plans/foo.md"* ]]
}

@test "hook: dirty tasks.md is NOT auto-committed" {
  make_modified "openspec/changes/foo/tasks.md"
  make_deleted ".rddf/plans/foo.md"
  post_archive_cleanup "$PROJECT_ROOT" "foo"
  # tasks.md still shows as modified (not staged, not committed by us)
  run git status --porcelain
  [[ "$output" == *" M openspec/changes/foo/tasks.md"* ]]
  # chore commit only contains the plan-file delete
  local head_commit_files
  head_commit_files=$(git show --name-only --pretty="" HEAD)
  [[ "$head_commit_files" == *".rddf/plans/foo.md"* ]]
  [[ "$head_commit_files" != *"tasks.md"* ]]
}

@test "hook: modified proposal-approved.md is staged but not auto-committed" {
  make_modified "proposal-approved.md"
  post_archive_cleanup "$PROJECT_ROOT" "foo"
  run git status --porcelain
  # 'M ' (second col space) means: index staged, worktree unchanged
  [[ "$output" == *"M  proposal-approved.md"* ]]
  # No chore commit at all (rm bucket empty)
  run git log --oneline
  [[ "$output" != *"chore(post-archive)"* ]]
}

@test "hook: works inside worktree (no main-repo state pollution)" {
  git worktree add .rddf/wt/foo -b foo openspec/foo 2>/dev/null || \
    git worktree add .rddf/wt/foo -b foo
  cd .rddf/wt/foo
  make_deleted ".rddf/plans/foo.md"
  post_archive_cleanup "$(pwd)" "foo"
  run git status --porcelain
  [ -z "$output" ]
  git worktree remove .rddf/wt/foo --force
}

@test "hook: cleans real-world residue (.rddf/plans/<existing>)" {
  # Simulates the bug from commit 9f31a68: archive left dangling plan file
  make_deleted ".rddf/plans/fix-rddf-init-broken-layout.md"
  run post_archive_cleanup "$PROJECT_ROOT" "fix-rddf-init-broken-layout"
  [ "$status" -eq 0 ]
  run git log --oneline
  [[ "$output" == *"chore(post-archive): clean residue from fix-rddf-init-broken-layout"* ]]
  run git status --porcelain
  [ -z "$output" ]
}
