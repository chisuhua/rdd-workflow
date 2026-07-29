# Fix guide-ship archive bats tests for non-worktree environments

**Priority**: P2 | **Phase**: default | **Category**: infra-setup
**Source**: improvements/fix-guide-ship-archive-bats.md

## Problem

Multiple archive-related bats integration tests fail when run outside a git worktree context. The root cause is inconsistent use of `$REPO_ROOT` vs inline `git rev-parse --show-toplevel`:

1. **`test_archive_proposal_status.bats`** (3 tests): Uses `PROJECT_ROOT=$(git rev-parse --show-toplevel)` instead of the pre-set `$REPO_ROOT` from `test_helper.bash`. Fails with `fatal: not a git repository` when run standalone.

2. **`test_archive_iteration_sync.bats`** (3 tests): Same pattern — uses `PROJECT_ROOT=$(git rev-parse --show-toplevel)` inline.

3. **`test_ship_archive_extraction.bats`** (detect_archive_mode tests): Creates temp repos with `git init` but the `source $REPO_ROOT/skills/...` calls assume the test runs from a repo root context.

4. **`test_archive_dedup.bats`** (check_worktree_commits / verify_merge_result tests): Same temp-repo creation pattern, no shared setup helper.

## Scope

- **In Scope**: Create a shared test helper `tests/_lib/test_archive_helper.bash` that provides `archive_test_setup()` for creating a minimal git repo with mock OpenSpec change structure. Fix existing archive bats tests to use the helper.
- **Out Scope**: No changes to guide-ship source code, archive.sh, or production code.

## Solution

Add `tests/_lib/test_archive_helper.bash` with:
- `archive_test_setup()`: Creates a temp dir, initializes git, sets up basic OpenSpec directory structure, exports `TEST_REPO_DIR`, `TEST_CHANGE_NAME`, `TEST_PROJECT_ROOT`
- `archive_test_teardown()`: Cleans up temp dir

Fix tests to use the helper and `$REPO_ROOT`/`$PROJECT_ROOT` from `test_helper.bash` instead of inline `git rev-parse`.

## Acceptance Criteria

- All 5+ archive bats test files pass when run from repo root: `bats tests/integration/test_archive_*.bats tests/integration/test_ship_archive_*.bats tests/integration/test_iteration_archive_hook.bats tests/integration/test_commit_archive_moves.bats`
- No changes to production code under `skills/`