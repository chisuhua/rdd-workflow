## Tasks

### Task 1: Create tests/_lib/test_archive_helper.bash with mock worktree setup

**Write failing test:**
```bash
# Verify archive_test_setup creates a temp git repo with openspec structure
run bash -c "
  source tests/_lib/test_archive_helper.bash
  archive_test_setup 'test-change'
  [[ -d \"\$TEST_REPO_DIR\" ]] || exit 1
  [[ -f \"\$TEST_REPO_DIR/README.md\" ]] || exit 2
  [[ -d \"\$TEST_REPO_DIR/openspec/changes/test-change\" ]] || exit 3
  [[ -d \"\$TEST_REPO_DIR/openspec/changes/archive\" ]] || exit 4
  [[ -d \"\$TEST_REPO_DIR/openspec/specs\" ]] || exit 5
  [[ -n \"\$TEST_CHANGE_NAME\" ]] || exit 6
  echo \"OK: \$TEST_CHANGE_NAME @ \$TEST_REPO_DIR\"
"
[ "$status" -eq 0 ]
[[ "$output" == "OK: test-change @"* ]]
```

**Verify fail:** The helper doesn't exist yet → `source` fails.

**Implement:**
Create `tests/_lib/test_archive_helper.bash` with:
- `archive_test_setup(name, [dir])` — creates temp git repo, initial commit, `openspec/changes/<name>/`, `openspec/changes/archive/`, `openspec/specs/`, exports `TEST_REPO_DIR`, `TEST_CHANGE_NAME`, `TEST_PROJECT_ROOT`, `cd`s into repo
- `archive_test_teardown()` — `cd /` + `rm -rf "$TEST_REPO_DIR"`

**Verify pass:** Run the test above.

**Commit:** `git add tests/_lib/test_archive_helper.bash && git commit -m "feat(tests): add archive_test_setup helper for archive bats tests"`

---

### Task 2: Fix test_archive_proposal_status.bats to use $REPO_ROOT

**Write failing test:**
```bash
# Verify test_archive_proposal_status.bats uses $REPO_ROOT not inline git rev-parse
! grep -q 'git rev-parse --show-toplevel' tests/integration/test_archive_proposal_status.bats
```

**Verify fail:** Current file has 3 instances of `git rev-parse --show-toplevel`.

**Implement:**
- Replace `PROJECT_ROOT=$(git rev-parse --show-toplevel)` with `$REPO_ROOT` (sourced from `test_helper.bash` via `load ../test_helper`)
- The `load ../test_helper` already sets `$REPO_ROOT` and `$PROJECT_ROOT`

**Verify pass:** Run the grep test above.

**Commit:** `git add tests/integration/test_archive_proposal_status.bats && git commit -m "fix(tests): replace inline git rev-parse with $REPO_ROOT in archive_proposal_status"`

---

### Task 3: Fix test_archive_iteration_sync.bats to use $REPO_ROOT

**Write failing test:**
```bash
# Verify test_archive_iteration_sync.bats uses $REPO_ROOT not inline git rev-parse
! grep -q 'git rev-parse --show-toplevel' tests/integration/test_archive_iteration_sync.bats
```

**Verify fail:** Current file has 3 instances of `git rev-parse --show-toplevel`.

**Implement:**
- Replace `PROJECT_ROOT=$(git rev-parse --show-toplevel)` with `$REPO_ROOT` (sourced from `test_helper.bash` via `load ../test_helper`)
- The `load ../test_helper` already sets `$REPO_ROOT` and `$PROJECT_ROOT`

**Verify pass:** Run the grep test above.

**Commit:** `git add tests/integration/test_archive_iteration_sync.bats && git commit -m "fix(tests): replace inline git rev-parse with $REPO_ROOT in archive_iteration_sync"`