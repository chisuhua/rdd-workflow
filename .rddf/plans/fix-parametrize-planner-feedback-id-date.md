# fix-parametrize-planner-feedback-id-date Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate hardcoded `pf-20260905-NNN` date strings in 5 failing pytest tests so they pass on any UTC date.

**Architecture:** Refactor tests to construct a tmp_path iteration.json with `date_prefix="20260115"` instead of `_today_prefix()`. Add a regression test that locks the invariant that tests don't depend on real wall-clock time.

**Tech Stack:** Python 3.11+, pytest, tmp_path fixture, monkeypatch, no freezegun/time.sleep.

---

## File Structure


### Production Code


### Tests

| `tests/unit/test_planner_feedback_id_uniqueness.py` | 5 failing tests: replace `_today_prefix()` hardcoded date with `tmp_path` fixture + monkeypatched `datetime.now()`. |
| `tests/conftest.py` | (optional) add shared `_fixed_utc_now` fixture for non-2026-09-05 dates. |
| `tests/KNOWN_FAILURES.txt` | Remove the 5 entries that this proposal unblocks. |

---

### Task 1: Parametrize 5 planner-feedback-id tests with tmp_path fixture

**Files:**
Modify: tests/unit/test_planner_feedback_id_uniqueness.py
Modify (optional): tests/conftest.py
Modify: tests/KNOWN_FAILURES.txt

- [ ] **Step 1: Write the failing regression test (lock invariant)**

Add a new test in tests/unit/test_planner_feedback_id_uniqueness.py that:
- uses monkeypatch to set `datetime.now()` to a fixed date (e.g. 2026-01-15)
- asserts that running the test body does NOT call `_today_prefix()` with real wall-clock
- The new test must FAIL initially because the existing 5 tests use real `datetime.now()`.

- [ ] **Step 2: Verify the new test fails**

Run: `pytest tests/unit/test_planner_feedback_id_uniqueness.py -v`
Expected: new regression test fails; 5 existing tests also fail (baseline).

- [ ] **Step 3: Refactor 5 failing tests to use tmp_path fixture**

For each of the 5 failing tests:
- Replace `_today_prefix()` / hardcoded `pf-20260905-NNN` with a `tmp_path`-constructed iteration.json containing `date_prefix="20260115"`.
- Use monkeypatch on `datetime.now()` if needed to pin the date.
- Preserve original test semantics: same-day recompute, counter at max+1, cross-day isolation, malformed skip, missing-key skip.
DO NOT change `_lib/planner_feedback.py` (product code is correct).

- [ ] **Step 4: Verify all 6 tests pass**

Run: `pytest tests/unit/test_planner_feedback_id_uniqueness.py -v`
Expected: 6/6 tests pass (5 refactored + 1 new regression test).
Then run with date override: `faketime '2026-03-01' pytest tests/unit/test_planner_feedback_id_uniqueness.py` (or monkeypatch) — confirm tests still pass.

- [ ] **Step 5: Commit**

Stage changes and commit: `test(test-planner-feedback): parametrize date prefix via tmp_path fixture + regression lock`
Update tests/KNOWN_FAILURES.txt to remove the 5 entries that this proposal unblocks.

