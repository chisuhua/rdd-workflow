# archive-iteration-sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Fix iteration.json sync regression where archived changes lack `archived_at` timestamp, causing feature_view.archived_count to drift.

**Architecture:** Modify `skills/_lib/archive.sh` so `archive_change()` calls `iteration.mark_archived(name)` at end. Add 3 bats regression tests in `tests/integration/test_archive_iteration_sync.bats`.

**Tech Stack:** Bash, bats-core, Python (iteration module).

---

## File Structure

### Production Code
| File | Responsibility |
|---|---|
| `skills/_lib/archive.sh` | Append `iteration.mark_archived` call at end of `archive_change()` |
| `skills/_lib/iteration/__init__.py` | (existing) Already exports `mark_archived(name, project_root)` |

### Tests
| File | Responsibility |
|---|---|
| `tests/integration/test_archive_iteration_sync.bats` | 3 regression tests |

---

## Task 1: Wire iteration.mark_archived into archive_change()

**Files:**
- Modify: `skills/_lib/archive.sh`
- Test: `tests/integration/test_archive_iteration_sync.bats`

- [x] **Step 1: Write failing test for normal archive**

```bash
# tests/integration/test_archive_iteration_sync.bats
@test "archive: writes archived_at to iteration.json":
    cd "$TEST_PROJECT_ROOT"
    openspec new change "test-sync-change"
    git add . && git commit -m "test: fixture"
    bash skills/_lib/archive.sh archive_change "test-sync-change"
    run jq -r '.changes[] | select(.name=="test-sync-change") | .archived_at' .rddf/state/iteration.json
    [ -n "$output" ]
```

- [x] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_archive_iteration_sync.bats`
Expected: FAIL (no `archived_at` field)

- [x] **Step 3: Modify archive.sh to call mark_archived**

Add at end of `archive_change()`:
```bash
PY_PROJECT_ROOT="$PROJECT_ROOT" python3 -c "
import os
from skills._lib.iteration import mark_archived
mark_archived('$CHANGE_NAME', os.environ['PY_PROJECT_ROOT'])
" || echo "WARN: iteration sync failed (non-fatal)" >&2
```

- [x] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_archive_iteration_sync.bats`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add skills/_lib/archive.sh tests/integration/test_archive_iteration_sync.bats
git commit -m "feat(archive): sync iteration.json archived_at on archive"
```

## Task 2: Idempotent archive test

**Files:**
- Test: `tests/integration/test_archive_iteration_sync.bats`

- [x] **Step 1: Write idempotent test**

Add test: archiving twice produces same archived_at

- [x] **Step 2: Run test**

Run: `bats tests/integration/test_archive_iteration_sync.bats`
Expected: PASS

- [x] **Step 3: Commit**

```bash
git commit -am "test(archive): verify archive idempotency"
```

## Task 3: feature_view archived_count dynamic calc

**Files:**
- Modify: `skills/_lib/feature_view.py`

- [x] **Step 1: Write failing test**

```python
def test_feature_view_archived_count_dynamic():
    # Set up: 3 archived changes in iteration.json
    # Verify: archived_count = 3 (not from cache)
```

- [x] **Step 2: Run test, verify fail**

Run: `pytest tests/unit/test_feature_view.py::test_feature_view_archived_count_dynamic -v`

- [x] **Step 3: Modify feature_view.py**

Replace cached `archived_count` with `len([c for c in changes if c.status == 'archived'])`

- [x] **Step 4: Verify pass**

Run: `pytest tests/unit/test_feature_view.py::test_feature_view_archived_count_dynamic -v`

- [x] **Step 5: Commit**

```bash
git add skills/_lib/feature_view.py tests/unit/test_feature_view.py
git commit -m "feat(feature-view): dynamic archived_count from iteration.json"
```
