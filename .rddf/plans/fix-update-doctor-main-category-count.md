# fix-update-doctor-main-category-count Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update test_doctor_main.py assertions from 10 → 11 to match the new `gitignore_check` category added by commit `add-gitignore-hard-protection`.

**Architecture:** Update the `set()` and `len()` assertions; extract a `_CATEGORY_NAMES = frozenset({...})` constant so future additions require only one edit. Add a sanity assertion that directory file count == category count.

**Tech Stack:** Python 3.11+, pytest, no new dependencies.

---

## File Structure


### Production Code


### Tests

| `tests/unit/test_doctor_main.py` | Update assertions 10 → 11; extract `_CATEGORY_NAMES` constant; add sanity assertion linking dir file count to category count. |

---

### Task 1: Update test_doctor_main category count from 10 to 11

**Files:**
Modify: tests/unit/test_doctor_main.py

- [ ] **Step 1: Verify 2 tests fail in baseline**

Run: `pytest tests/unit/test_doctor_main.py -v`
Expected: `test_aggregate_runs_all_10_categories` and `test_checkers_dict_has_10_entries` fail with 'gitignore' missing from the set and `len == 10` != 11.

- [ ] **Step 2: Add a failing regression test for the constant extraction**

Add a new test `test_category_names_constant_matches_disk` that:
- imports `_CATEGORY_NAMES` from `tests.unit.test_doctor_main` (after the constant is added in step 3)
- asserts `len(_CATEGORY_NAMES) == len([f for f in Path('skills/rdd-doctor/scripts/checks').glob('*.py') if f.stem != '__init__'])`
This test must FAIL initially because `_CATEGORY_NAMES` is not yet defined.

- [ ] **Step 3: Update the test file**

In tests/unit/test_doctor_main.py:
- Add module-level constant `_CATEGORY_NAMES = frozenset({"state", "plan-tdd", "roadmap-meta", "proposal-table", "proposal-section", "tasks-checkbox", "migration-residue", "orphan-gates", "roadmap-refs", "docs-consistency", "gitignore"})`
- Replace the hardcoded `set()` in `test_aggregate_runs_all_10_categories` with `_CATEGORY_NAMES`
- Update `len(_CHECKERS) == 10` → `len(_CHECKERS) == 11` (or use `_CATEGORY_NAMES`)
- Update docstrings from 'all 10 categories' → 'all 11 categories (10 baseline + gitignore)'
- Add the new sanity assertion `len([f for f in Path('skills/rdd-doctor/scripts/checks').glob('*.py') if f.stem != '__init__']) == len(_CATEGORY_NAMES)`

- [ ] **Step 4: Verify all tests pass**

Run: `pytest tests/unit/test_doctor_main.py -v`
Expected: all tests pass (2 previously-failing + 1 new regression test).
Run: `pytest tests/unit/test_doctor_main.py --tb=short` to confirm no other regressions.

- [ ] **Step 5: Commit**

Stage and commit: `test(rdd-doctor): update category count 10 → 11 + extract _CATEGORY_NAMES constant`
Update tests/KNOWN_FAILURES.txt to remove the 2 entries this proposal unblocks.

