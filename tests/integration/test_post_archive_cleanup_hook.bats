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
  local commits_before
  commits_before=$(git rev-list --count HEAD)
  run post_archive_cleanup "$PROJECT_ROOT" "foo"
  [ "$status" -eq 0 ]
  # v2.2.4+ (reduce-archive-commit-noise): hook git rm's + stages but does
  # NOT create an independent commit — archive_change --amends the cleanup
  # into the main archive commit. So:
  #   - no new commit lands
  #   - index shows the delete staged ("D " in porcelain = staged)
  [ "$(git rev-list --count HEAD)" -eq "$commits_before" ]
  [[ ! "$(git log --oneline)" == *"chore(post-archive)"* ]]
  run git status --porcelain
  [[ "$output" == *"D  .rddf/plans/foo.md"* ]]
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
  local commits_before
  commits_before=$(git rev-list --count HEAD)
  post_archive_cleanup "$PROJECT_ROOT" "foo"
  # tasks.md is NOT in _WHITELIST_MODIFIED_PATTERNS (only proposal-approved/roadmap),
  # so hook leaves it as worktree-modified (" M"), not staged and not committed.
  run git status --porcelain
  [[ "$output" == *" M openspec/changes/foo/tasks.md"* ]]
  # No independent chore commit (v2.2.4+: hook stages only the rm bucket)
  [ "$(git rev-list --count HEAD)" -eq "$commits_before" ]
  [[ ! "$(git log --oneline)" == *"chore(post-archive)"* ]]
  # The deleted plan file IS staged (in deleted_to_rm bucket)
  [[ "$output" == *"D  .rddf/plans/foo.md"* ]]
}

@test "hook: modified improvement-approved.md is staged but not auto-committed" {
  make_modified "improvement-approved.md"
  post_archive_cleanup "$PROJECT_ROOT" "foo"
  run git status --porcelain
  # 'M ' (second col space) means: index staged, worktree unchanged
  [[ "$output" == *"M  improvement-approved.md"* ]]
  # No chore commit at all (rm bucket empty)
  run git log --oneline
  [[ "$output" != *"chore(post-archive)"* ]]
}

@test "hook: works inside worktree (no main-repo state pollution)" {
  local main_commits_before
  main_commits_before=$(git rev-list --count HEAD)
  git worktree add .rddf/wt/foo -b foo openspec/foo 2>/dev/null || \
    git worktree add .rddf/wt/foo -b foo
  cd .rddf/wt/foo
  make_deleted ".rddf/plans/foo.md"
  post_archive_cleanup "$(pwd)" "foo"
  # Worktree has the staged delete (expected)
  run git status --porcelain
  [[ "$output" == *"D  .rddf/plans/foo.md"* ]]
  # Main repo must NOT receive a chore commit (v2.2.4+ hook stages only)
  cd "$PROJECT_ROOT"
  [ "$(git rev-list --count HEAD)" -eq "$main_commits_before" ]
  [[ ! "$(git log --oneline)" == *"chore(post-archive)"* ]]
  git worktree remove .rddf/wt/foo --force
}

@test "hook: cleans real-world residue (.rddf/plans/<existing>)" {
  # Simulates the bug from commit 9f31a68: archive left dangling plan file
  make_deleted ".rddf/plans/fix-rddf-init-broken-layout.md"
  local commits_before
  commits_before=$(git rev-list --count HEAD)
  run post_archive_cleanup "$PROJECT_ROOT" "fix-rddf-init-broken-layout"
  [ "$status" -eq 0 ]
  # v2.2.4+: no independent chore commit, but residue is staged for amend
  [ "$(git rev-list --count HEAD)" -eq "$commits_before" ]
  [[ ! "$(git log --oneline)" == *"chore(post-archive)"* ]]
  run git status --porcelain
  [[ "$output" == *"D  .rddf/plans/fix-rddf-init-broken-layout.md"* ]]
}
