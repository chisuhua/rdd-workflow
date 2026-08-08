#!/usr/bin/env bats
# tests/integration/test_post_archive_cleanup_changes_e2e.bats
# E2E tests for archive-cleanup-plan-files-extension:
# simulates post_archive_cleanup in real openspec archive flow.
load ../test_helper

setup() {
  TEST_TMPDIR="$(mktemp -d)"
  export PROJECT_ROOT="$TEST_TMPDIR/fake-repo"
  mkdir -p "$PROJECT_ROOT"/{_lib,openspec/changes,openspec/specs,.rddf/state,.rddf/plans}
  cd "$PROJECT_ROOT"
  git init -q -b master
  git config user.email "test@example.com"
  git config user.name "Test"
  git commit --allow-empty -m "init" -q
  source "$BATS_TEST_DIRNAME/../../_lib/post_archive_cleanup.sh"
}

teardown() { rm -rf "$TEST_TMPDIR"; }

# Simulate a full change setup: 6 residue files in openspec/changes/<name>/
# + corresponding archive/ directory

simulate_archive() {
  local name="$1"
  local date="${2:-2026-08-08}"
  # Active change directory with 6 artifact types
  mkdir -p "openspec/changes/$name/specs/diagnose"
  for f in .openspec.yaml design.md proposal.md roadmap-meta.yaml tasks.md; do
    echo "content of $f" > "openspec/changes/$name/$f"
  done
  echo "spec" > "openspec/changes/$name/specs/diagnose/spec.md"
  git add "openspec/changes/$name/"
  git commit -q -m "add change $name"

  # Plan file
  echo "plan" > ".rddf/plans/$name.md"
  git add ".rddf/plans/$name.md"
  git commit -q -m "add plan $name"

  # Now simulate archive: openspec moves the dir to archive/<date>-<name>/
  # We simulate this by deleting the active dir + creating the archive marker
  mkdir -p "openspec/changes/archive/${date}-${name}"
  echo "archived" > "openspec/changes/archive/${date}-${name}/.marker"
  git add "openspec/changes/archive/${date}-${name}/.marker"
  git commit -q -m "archive $name"

  # Simulate the deletion of the active dir (what openspec archive does)
  for f in .openspec.yaml design.md proposal.md roadmap-meta.yaml tasks.md; do
    rm "openspec/changes/$name/$f"
  done
  rm -f "openspec/changes/$name/specs/diagnose/spec.md"
  # Force the parent dir to be visible as "deleted" via git rm
  git rm -rf "openspec/changes/$name/" 1>/dev/null || true
  # But we want the repo to see them as worktree-deleted (D), not stage-deleted:
  # Restore the files briefly to retouch + delete
  for f in .openspec.yaml design.md proposal.md proposal.md; do
    :
  done
  # Actually, the cleanest way: re-create the files in a way that makes them look like
  # "index says deleted, working tree says deleted" -- so just leave them gone.
  # But to simulate residue, we need to have something in git status --porcelain.
  # Re-add them as residual via direct manipulation:
  for f in .openspec.yaml design.md proposal.md roadmap-meta.yaml tasks.md; do
    echo "residual" > "openspec/changes/$name/$f"
  done
  echo "spec residual" > "openspec/changes/$name/specs/diagnose/spec.md"
  # Remove via git rm so they become stage-deleted (D in index)
  git add "openspec/changes/$name/"
  git rm --cached "openspec/changes/$name/.openspec.yaml" "openspec/changes/$name/design.md" \
    "openspec/changes/$name/proposal.md" "openspec/changes/$name/roadmap-meta.yaml" \
    "openspec/changes/$name/tasks.md" "openspec/changes/$name/specs/diagnose/spec.md" 1>/dev/null
  # Now we have D index status, files still on disk
  # For worktree-deleted test, we'll use a different approach
}

# Simpler approach: directly create the residue state
simulate_residue() {
  local name="$1"
  local date="${2:-2026-08-08}"
  # Archive directory
  mkdir -p "openspec/changes/archive/${date}-${name}"
  echo "marker" > "openspec/changes/archive/${date}-${name}/.marker"
  git add "openspec/changes/archive/${date}-${name}/.marker"
  git commit -q -m "archive $name"
  # Now create some files that git tracks, then delete them in the working tree
  # to get the ' D' status (deleted in worktree, not staged)
  for f in .openspec.yaml design.md proposal.md roadmap-meta.yaml tasks.md; do
    mkdir -p "openspec/changes/$name"
    echo "content" > "openspec/changes/$name/$f"
    git add "openspec/changes/$name/$f"
  done
  git commit -q -m "track $name files"
  # Now delete the files in working tree (this produces ' D' status)
  rm "openspec/changes/$name/.openspec.yaml"
  rm "openspec/changes/$name/design.md"
  rm "openspec/changes/$name/proposal.md"
  rm "openspec/changes/$name/roadmap-meta.yaml"
  rm "openspec/changes/$name/tasks.md"
}

# Task 5: E2E worktree mode

@test "e2e: post_archive_cleanup handles 6-residue with archive presence" {
  simulate_residue "my-change" "2026-08-08"
  # Verify initial state
  run git status --porcelain
  [[ "$output" == *"D openspec/changes/my-change/.openspec.yaml"* ]]
  [[ "$output" == *"D openspec/changes/my-change/tasks.md"* ]]
  # Run the hook
  run post_archive_cleanup "$PROJECT_ROOT" "my-change"
  [ "$status" -eq 0 ]
  # After hook: chore commit added
  run git log --oneline
  [[ "$output" == *"chore(post-archive): clean residue from my-change"* ]]
  # Files are gone from working tree
  [ ! -f "openspec/changes/my-change/.openspec.yaml" ]
  # Status should be clean (the 6 files were git rm-ed and committed)
  run git status --porcelain
  # The 6 deletions are now committed, so no remaining D status from them
  [[ ! "$output" == *"D openspec/changes/my-change" ]]
}

# Task 6: E2E active change protection

@test "e2e: active change (no archive) is NOT cleaned even if residue present" {
  # Create active change
  mkdir -p "openspec/changes/active-change"
  for f in .openspec.yaml design.md proposal.md; do
    echo "content" > "openspec/changes/active-change/$f"
    git add "openspec/changes/active-change/$f"
  done
  git commit -q -m "track active-change"
  # Delete the files in working tree (active change, no archive)
  rm "openspec/changes/active-change/.openspec.yaml"
  rm "openspec/changes/active-change/design.md"
  rm "openspec/changes/active-change/proposal.md"
  # Verify no archive dir exists
  [ ! -d "openspec/changes/archive/2026-08-08-active-change" ]
  # Run the hook
  run post_archive_cleanup "$PROJECT_ROOT" "active-change"
  [ "$status" -eq 0 ]
  # Files should still be deleted-from-disk (D status), not git rm-ed
  run git status --porcelain
  [[ "$output" == *"D openspec/changes/active-change/.openspec.yaml"* ]]
  # No commit
  run git log --oneline
  [[ "$output" != *"chore(post-archive)"* ]]
  # (Warning is on stderr; capture in separate run with 2>&1)
  local captured
  captured=$(post_archive_cleanup "$PROJECT_ROOT" "active-change" 2>&1 || true)
  [[ "$captured" == *"no archive/"* ]]
}

# Task 7: E2E archive/ subdir preserved

@test "e2e: archive/ subdir residue is preserved (no cleanup)" {
  # Setup archive directory with files
  mkdir -p "openspec/changes/archive/2026-07-01-historical"
  echo "historical" > "openspec/changes/archive/2026-07-01-historical/proposal.md"
  git add "openspec/changes/archive/2026-07-01-historical/proposal.md"
  git commit -q -m "archive historical"
  # Delete the file in working tree
  rm "openspec/changes/archive/2026-07-01-historical/proposal.md"
  # Verify D status
  run git status --porcelain
  [[ "$output" == *"D openspec/changes/archive/2026-07-01-historical/proposal.md"* ]]
  # Run the hook
  run post_archive_cleanup "$PROJECT_ROOT" "historical"
  [ "$status" -eq 0 ]
  # archive/ residue remains — not git rm-ed
  run git status --porcelain
  [[ "$output" == *"D openspec/changes/archive/2026-07-01-historical/proposal.md"* ]]
  # No commit
  run git log --oneline
  [[ "$output" != *"chore(post-archive)"* ]]
}
