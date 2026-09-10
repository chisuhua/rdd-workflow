# fix-remove-stale-filled-at-regression-test Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor `TestFilledAtRegression::test_actual_repo_iteration_json_validates_after_fix` to use `tmp_path` fixture instead of the real `.rddf/state/iteration.json` (which no longer contains `filled_at`).

**Architecture:** Replace the dependency on the real repository state with a deterministic tmp_path-constructed iteration.json that contains `filled_at`. The test intent (schema accepts `filled_at`) is preserved per the change proposal's Option B.

**Tech Stack:** Python 3.11+, pytest, tmp_path fixture, json schema validation.

---

## File Structure


### Production Code


### Tests

| `tests/unit/test_cli_all_subcommands.py` | Refactor TestFilledAtRegression::test_actual_repo_iteration_json_validates_after_fix to use tmp_path instead of real .rddf/state/iteration.json. |

---

### Task 1: Use tmp_path fixture for TestFilledAtRegression

**Files:**
Modify: tests/unit/test_cli_all_subcommands.py

- [ ] **Step 1: Verify 1 test fails in baseline**

Run: `pytest tests/unit/test_cli_all_subcommands.py::TestFilledAtRegression -v`
Expected: `test_actual_repo_iteration_json_validates_after_fix` fails because `.rddf/state/iteration.json` has no `filled_at` fields.

- [ ] **Step 2: Add a failing regression test for the invariant**

Add a new test in the TestFilledAtRegression class:
```python
def test_does_not_read_real_repo_iteration_json(self):
    import inspect
    source = inspect.getsource(self.test_actual_repo_iteration_json_validates_after_fix)
    assert '.rddf/state/iteration.json' not in source, (
        'Test must use tmp_path fixture, not the real repo iteration.json'
    )
```
This test must FAIL initially because the existing test still references the real path.

- [ ] **Step 3: Refactor the failing test to use tmp_path**

In tests/unit/test_cli_all_subcommands.py:
- Modify `test_actual_repo_iteration_json_validates_after_fix`:
  - Remove the dependency on real `.rddf/state/iteration.json`
  - Use `tmp_path` fixture to construct a minimal valid iteration.json containing one change with `filled_at: '2026-09-10T00:00:00+00:00'`
  - Call the schema validator with this tmp_path file
  - Assert that schema accepts it (no rejection)
- Update docstring: 'verifies schema accepts filled_at via tmp_path fixture, not real repo state'
DO NOT change `_lib/iteration/store.py` or schema (product code stable).

- [ ] **Step 4: Verify all tests pass**

Run: `pytest tests/unit/test_cli_all_subcommands.py::TestFilledAtRegression -v`
Expected: all tests in the class pass (1 refactored + 1 new regression test).
Run: `pytest tests/unit/test_cli_all_subcommands.py -v` to confirm no other regressions in the file.

- [ ] **Step 5: Commit**

Stage and commit: `test(test-cli): use tmp_path for TestFilledAtRegression (per schema v6 stability)`
Update tests/KNOWN_FAILURES.txt to remove the 1 entry this proposal unblocks.

