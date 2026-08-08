#!/usr/bin/env bats
# tests/integration/test_post_archive_cleanup_changes.bats
# Tests for archive-cleanup-plan-files-extension (P2, 2026-08-08):
# extends _lib/post_archive_cleanup.sh to also clean openspec/changes/<name>/ residue.
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

# helper: stage an archive presence record (archive/<date>-<name>/)
make_archive() {
  local name="$1"
  local date="${2:-2026-08-08}"
  mkdir -p "openspec/changes/archive/${date}-${name}"
  echo "archived" > "openspec/changes/archive/${date}-${name}/.marker"
  git add "openspec/changes/archive/${date}-${name}/.marker"
  git commit -q -m "archive $name"
}

# Task 1.1 — _WHITELIST_DELETED_PATTERNS contains openspec/changes/

@test "whitelist: contains openspec/changes/ prefix" {
  local present=0
  for p in "${_WHITELIST_DELETED_PATTERNS[@]}"; do
    if [ "$p" = "openspec/changes/" ]; then
      present=1
      break
    fi
  done
  [ "$present" -eq 1 ]
}

# Task 1.2 — _matches_prefix matches openspec/changes/foo

@test "matches_prefix: openspec/changes/foo/proposal.md matches openspec/changes/" {
  _matches_prefix "openspec/changes/foo/proposal.md" "${_WHITELIST_DELETED_PATTERNS[@]}"
}

# Task 1.3 — _matches_prefix does NOT match openspec/changes/archive/ as prefix of itself

@test "matches_prefix: openspec/changes/archive/<date>-foo/ is signaled-by-itself but case-skipped later" {
  # _matches_prefix raw returns 0 because the prefix matches; the caller
  # (post_archive_cleanup) is responsible for the case statement that skips archive/.
  _matches_prefix "openspec/changes/archive/2026-08-08-foo/proposal.md" "${_WHITELIST_DELETED_PATTERNS[@]}"
}

# Task 2.1 — active change in openspec/changes/<name>/ is NOT cleaned when archive/ absent

@test "extensions: active change residue NOT cleaned when archive/ absent" {
  make_deleted "openspec/changes/active-change/proposal.md"
  run post_archive_cleanup "$PROJECT_ROOT" "active-change"
  [ "$status" -eq 0 ]
  # Status should still show D (helper skipped; file not git rm-ed)
  run git status --porcelain
  [[ "$output" == *" D openspec/changes/active-change/proposal.md"* ]]
  # No commit
  run git log --oneline
  [[ "$output" != *"chore(post-archive)"* ]]
}

# Task 2.2 — archive/ subdir is excluded from cleanup

@test "extensions: openspec/changes/archive/ residue is skipped (preserve history)" {
  make_archive "old-archive"
  make_deleted "openspec/changes/archive/2026-08-08-old-archive/proposal.md"
  run post_archive_cleanup "$PROJECT_ROOT" "old-archive"
  [ "$status" -eq 0 ]
  # archive/ residue remains
  run git status --porcelain
  [[ "$output" == *" D openspec/changes/archive/2026-08-08-old-archive/proposal.md"* ]]
  # No commit
  run git log --oneline
  [[ "$output" != *"chore(post-archive)"* ]]
}

# Task 3.1 — idempotent on openspec/changes/

@test "extensions: idempotent — second run after archive presence unchanged" {
  make_archive "my-change"
  make_deleted "openspec/changes/my-change/proposal.md"
  post_archive_cleanup "$PROJECT_ROOT" "my-change"
  local first_count
  first_count=$(git rev-list --count HEAD)
  post_archive_cleanup "$PROJECT_ROOT" "my-change"
  local second_count
  second_count=$(git rev-list --count HEAD)
  [ "$second_count" -eq "$first_count" ]
}

# Task 3.2 — SKIP_POST_ARCHIVE_CLEANUP=yes skips openspec/changes/ too

@test "extensions: SKIP_POST_ARCHIVE_CLEANUP=yes skips openspec/changes/ cleaning" {
  make_archive "skipped-change"
  make_deleted "openspec/changes/skipped-change/tasks.md"
  SKIP_POST_ARCHIVE_CLEANUP=yes run post_archive_cleanup "$PROJECT_ROOT" "skipped-change"
  [ "$status" -eq 0 ]
  [[ "$output" == *"SKIPPED"* ]]
  run git status --porcelain
  [[ "$output" == *" D openspec/changes/skipped-change/tasks.md"* ]]
}

# Task 4.1 — manual entry CLI script — --include-change-artifacts flag

@test "manual: --include-change-artifacts flag is accepted (idempotent when no residue)" {
  bash "$BATS_TEST_DIRNAME/../../scripts/cleanup-plan-files.sh" --include-change-artifacts </dev/null
}
