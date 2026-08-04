# add-known-failures-baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a versioned Bats failure baseline and one shared regression-reporting path so known failures remain visible while only newly introduced failures fail local and CI gates.

**Architecture:** `tests/scripts/report_regression.sh` owns the full-run, TAP failure-name extraction, baseline comparison, and exit status. `tests/scripts/refresh_known_failures.sh` owns explicit baseline regeneration while preserving existing reason comments. CI calls the report script after the existing recursive Bats run, so local and CI use identical comparison behavior.

**Tech Stack:** Bash, bats-core TAP output, `awk`/`sed`/`sort`/`comm`, GitHub Actions, Bats integration tests.

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `tests/KNOWN_FAILURES.txt` | Canonical test-name baseline; one normalized Bats test name per line with a reason/environment comment. |
| `tests/scripts/report_regression.sh` | Run recursive Bats, normalize failed test names, report known versus incremental failures, and return non-zero only for incremental failures. |
| `tests/scripts/refresh_known_failures.sh` | Run recursive Bats and rewrite the canonical failure set while retaining comments for unchanged names. |
| `.github/workflows/test.yml` | Invoke the shared regression report after the existing recursive Bats step. |
| `tests/README.md` | Document baseline maintenance, explicit refresh behavior, and local/CI commands. |
| `CHANGELOG.md` | Record the new regression-baseline workflow. |

### Tests

| File | Responsibility |
|---|---|
| `tests/integration/test_known_failures_baseline.bats` | Exercise TAP parsing, known-failure visibility, incremental-failure exit status, refresh round-trip, and comment preservation with temporary fake Bats output. |

---

### Task 1: Lock the failure-set and report contracts

**Files:**
- Create: `tests/integration/test_known_failures_baseline.bats`
- Test: `tests/scripts/report_regression.sh`
- Test: `tests/scripts/refresh_known_failures.sh`

- [ ] **Step 1: Write the failing tests**

Create a Bats file that builds a temporary `bin/bats` executable in `BATS_TEST_TMPDIR` and makes it print deterministic TAP lines such as `not ok 1 known test` and `not ok 2 new test`. Add cases for: a known failure being counted but not failing; an unlisted failure being reported as incremental and returning non-zero; no failures returning zero; a refresh preserving a `# reason` suffix for an unchanged test; and refresh output matching the report parser’s normalized names.

- [ ] **Step 2: Run tests to verify they fail**

Run: `bats tests/integration/test_known_failures_baseline.bats`

Expected: FAIL because `tests/scripts/report_regression.sh` and `tests/scripts/refresh_known_failures.sh` do not exist yet; the failure output must identify the missing scripts rather than silently passing.

- [ ] **Step 3: Write the minimal test harness implementation**

Keep the fake Bats executable and all temporary baseline files inside the Bats temporary directory. Assert exact observable contracts: output contains `已知失败`, output contains `新增失败` only for an unlisted failure, and exit codes are `0` for zero incremental failures and non-zero for one incremental failure. Do not mock any other command or add a new test framework.

- [ ] **Step 4: Run focused tests to verify the harness is ready**

Run: `bats tests/integration/test_known_failures_baseline.bats`

Expected: The tests still fail only because the two production scripts are absent; no test should fail due to an invalid fixture or an unasserted exit code.

- [ ] **Step 5: Commit the contract tests**

```bash
git add tests/integration/test_known_failures_baseline.bats
git commit -m "test: lock known failure regression contracts"
```

### Task 2: Add the baseline and incremental regression reporter

**Files:**
- Create: `tests/KNOWN_FAILURES.txt`
- Create: `tests/scripts/report_regression.sh`
- Modify: `tests/integration/test_known_failures_baseline.bats`

- [ ] **Step 1: Write the failing test**

Extend the focused tests with a 41-entry baseline fixture shaped like the committed file format and assert that every normalized baseline entry is counted as known, while a synthetic `not ok` name not in the file is listed as incremental. Keep comments out of the comparison key.

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_known_failures_baseline.bats`

Expected: FAIL because the baseline and report script are not present and no report can distinguish comment text from the test-name key.

- [ ] **Step 3: Write the minimal implementation**

Create `tests/KNOWN_FAILURES.txt` from the measured master failure output, with exactly one normalized Bats test name and a human-readable reason/environment comment per current known failure. Make `report_regression.sh` run `bats tests/ --recursive 2>&1`, extract `not ok` names without line numbers, normalize/sort both actual and baseline sets, compute `comm -23 actual baseline`, print known-failure and incremental-failure counts, and return `0` only when the incremental set is empty. Preserve the underlying Bats failure visibility; do not filter known failures from the run.

- [ ] **Step 4: Run focused tests to verify it passes**

Run: `bats tests/integration/test_known_failures_baseline.bats`

Expected: PASS for known-only, zero-failure, and new-failure scenarios; the new-failure case must show the test name and return non-zero.

- [ ] **Step 5: Commit the reporter**

```bash
git add tests/KNOWN_FAILURES.txt tests/scripts/report_regression.sh tests/integration/test_known_failures_baseline.bats
git commit -m "feat: add incremental failure regression report"
```

### Task 3: Add explicit baseline refresh with comment preservation

**Files:**
- Create: `tests/scripts/refresh_known_failures.sh`
- Modify: `tests/integration/test_known_failures_baseline.bats`
- Modify: `tests/KNOWN_FAILURES.txt`

- [ ] **Step 1: Write the failing test**

Add a test that starts with a baseline containing `known test # environment dependency`, feeds refresh output containing `known test` plus `new known test`, and verifies the generated file retains the existing comment for `known test`, adds the new test with a required reason marker, and removes entries no longer reported as failing.

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_known_failures_baseline.bats --filter refresh`

Expected: FAIL because the refresh command is absent and no generated file exists for comparison.

- [ ] **Step 3: Write the minimal implementation**

Implement `refresh_known_failures.sh` with the same TAP normalization rules as the report script. Read the existing baseline into a name-to-comment lookup, merge comments for names still failing, add a deterministic `# reason required` marker for newly observed names, write through a temporary file, and atomically replace `tests/KNOWN_FAILURES.txt`. Never add incremental failures automatically during reporting; only this explicit command may update the baseline.

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_known_failures_baseline.bats --filter refresh`

Expected: PASS; unchanged comments are byte-for-byte retained, output is sorted/diffable, and no stale entry remains.

- [ ] **Step 5: Commit the refresh command**

```bash
git add tests/scripts/refresh_known_failures.sh tests/KNOWN_FAILURES.txt tests/integration/test_known_failures_baseline.bats
git commit -m "feat: add explicit known failure refresh"
```

### Task 4: Wire CI and document maintenance

**Files:**
- Modify: `.github/workflows/test.yml`
- Modify: `tests/README.md`
- Modify: `CHANGELOG.md`
- Modify: `tests/integration/test_known_failures_baseline.bats`

- [ ] **Step 1: Write the failing test**

Add structural assertions that `.github/workflows/test.yml` invokes `bash tests/scripts/report_regression.sh` after the recursive Bats step, `tests/README.md` documents add/remove/refresh rules and the distinction between known and incremental failures, and `CHANGELOG.md` records the baseline gate.

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_known_failures_baseline.bats --filter documentation`

Expected: FAIL because the CI step and maintenance documentation are not yet present.

- [ ] **Step 3: Write the minimal implementation**

Add a CI step after `Bats smoke (full recursive — v2.0.3)` that invokes the shared report script and therefore fails only on incremental failures. Document the exact commands `bash tests/scripts/report_regression.sh` and `bash tests/scripts/refresh_known_failures.sh`, require manual review of reasons before updating the baseline, and explain that known failures remain visible and counted. Add a concise changelog entry.

- [ ] **Step 4: Run the complete verification suite**

Run: `bash tests/scripts/report_regression.sh`; then `bash tests/scripts/refresh_known_failures.sh`; inspect `git diff -- tests/KNOWN_FAILURES.txt` and `git diff --check`; finally run `npm test` and `python3 -m pytest tests/unit/ tests/integration/ -q --tb=short`.

Expected: Focused tests pass; the clean report prints `0 新增` and exits `0`; known failures remain counted; full repository tests show no regression. If the pre-existing known-failure count differs from 41, record the exact observed count and update only the baseline file/reason comments.

- [ ] **Step 5: Commit the integration and documentation**

```bash
git add .github/workflows/test.yml tests/README.md CHANGELOG.md tests/integration/test_known_failures_baseline.bats
git commit -m "ci: gate only incremental test failures"
```
