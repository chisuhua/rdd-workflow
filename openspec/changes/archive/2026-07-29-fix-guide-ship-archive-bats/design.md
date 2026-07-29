# Design: Fix guide-ship archive bats tests

## Test Layout Analysis

Current archive bats test files (11 files in `tests/integration/`):

| File | Tests | Issue |
|------|-------|-------|
| `test_archive_handoff_cleanup.bats` | 4 | Uses `$PROJECT_ROOT` (from test_helper) — OK |
| `test_archive_gate.bats` | 3 | Uses `$PROJECT_ROOT` — OK |
| `test_archive_dedup.bats` | 10 | Uses `$REPO_ROOT` + temp repos — OK |
| `test_archive_confirmation.bats` | 2 | Greps status.md — OK |
| `test_archive_proposal_status.bats` | 3 | **Uses `git rev-parse --show-toplevel` inline — FAILS in non-repo** |
| `test_archive_iteration_sync.bats` | 3 | **Uses `git rev-parse --show-toplevel` inline — FAILS in non-repo** |
| `test_ship_archive_extraction.bats` | 7 | Uses `$REPO_ROOT` + temp repos — OK (but no shared helper) |
| `test_ship_archive_incomplete.bats` | 4 | Uses `$PROJECT_ROOT` — OK |
| `test_iteration_archive_hook.bats` | 7 | Uses `$REPO_ROOT` + WORKDIR — OK |
| `test_commit_archive_moves.bats` | 3 | Uses `$REPO_ROOT` + `$BATS_TEST_TMPDIR` — OK |
| `test_status_archive_menu_extraction.bats` | 7 | Uses `$REPO_ROOT` — OK |

## Root Cause

Two test files (`test_archive_proposal_status.bats` and `test_archive_iteration_sync.bats`) use `PROJECT_ROOT=$(git rev-parse --show-toplevel)` instead of the pre-set `$REPO_ROOT` and `$PROJECT_ROOT` from `test_helper.bash`. When bats runs these tests outside a git context (e.g., in CI partial runs), `git rev-parse` fails with `fatal: not a git repository`.

## Solution: Shared Test Helper

### `tests/_lib/test_archive_helper.bash`

```bash
# archive_test_setup(name, [dir]) — Create a minimal git repo with mock OpenSpec structure
# archive_test_teardown() — Clean up temp dir
```

The helper:
1. Creates a temp dir (using `$BATS_TEST_TMPDIR` or `mktemp -d`)
2. `git init -q -b master`
3. Configures user.email/name
4. Creates `README.md` + initial commit
5. Creates `openspec/changes/<name>/` + `openspec/changes/archive/` + `openspec/specs/`
6. Creates `.rddf/state/` structure
7. Exports `TEST_REPO_DIR`, `TEST_CHANGE_NAME`, `TEST_PROJECT_ROOT`
8. `cd`s into the test repo

## Fix Plan

### Task 1: Create `tests/_lib/test_archive_helper.bash`
- `archive_test_setup()` function
- `archive_test_teardown()` function
- Support for optional change name (default: "test-change")
- Support for optional initial tasks.md content

### Task 2: Fix `test_archive_proposal_status.bats`
- Replace `PROJECT_ROOT=$(git rev-parse --show-toplevel)` with `$REPO_ROOT` from test_helper
- Remove `cd` to repo root where not needed
- Keep `mktemp -d` for test fixture isolation

### Task 3: Fix `test_archive_iteration_sync.bats`
- Replace `PROJECT_ROOT=$(git rev-parse --show-toplevel)` with `$REPO_ROOT`
- The Python inline test already uses `sys.path.insert(0, '$PROJECT_ROOT')` — change to `$REPO_ROOT`

## Files Modified

- `tests/_lib/test_archive_helper.bash` (NEW)
- `tests/integration/test_archive_proposal_status.bats` (MODIFY)
- `tests/integration/test_archive_iteration_sync.bats` (MODIFY)