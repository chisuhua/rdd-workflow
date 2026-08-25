# fix-skill-count-and-table-schema Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task.

**Goal:** Fix 3 `test_doc_contracts` failures (skill count logic) + 16 `proposal-table` warnings (schema drift in `proposal-approved.md`).

**Architecture:** Change `_count_skill_files()` to count only sub-skill SKILL.md files (exclude INSTALL.md). Add `| 已批准 |` column to 9 rows in `proposal-approved.md` lines 108-116. Add 1 regression test.

**Tech Stack:** Python 3.11+, pytest

---

## File Structure

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_doc_contracts.py` | Fix `_count_skill_files()` — only count sub-skill SKILL.md |
| `tests/unit/test_proposal_table_schema.py` | **NEW** — regression: every linked row in `proposal-approved.md` is 4 cols |

### Docs

| File | Responsibility |
|---|---|
| `proposal-approved.md` | Add `状态` column to lines 108-116 (9 rows) |

---

### Task 1: Write failing tests

**Files:**
- Modify: `tests/unit/test_doc_contracts.py` (the `_count_skill_files()` function)
- Create: `tests/unit/test_proposal_table_schema.py` (NEW)

- [ ] **Step 1: Read existing test_doc_contracts.py**

Use `read` to load `tests/unit/test_doc_contracts.py`. Confirm:
- `_count_skill_files()` at line 56-60 returns `len(top) + len(sub)` = 25
- 3 test functions assert against this count

- [ ] **Step 2: Run current failing tests to confirm baseline**

Run: `cd $WT_PATH && python3 -m pytest tests/unit/test_doc_contracts.py -v 2>&1 | tail -10`
Expected: 3 FAIL (test_install_description_skill_count_matches_disk, test_package_json_skills_count_within_delta, test_install_sub_skill_table_count_matches_disk).

- [ ] **Step 3: Create `tests/unit/test_proposal_table_schema.py`**

Create the regression test file:

```python
"""Regression: every linked row in proposal-approved.md has 4 columns.

Fix-adr-0027-skill-count-and-table-schema: rdd-doctor's
proposal_table_check.py enforces 4 columns for proposal-approved.md
(提案 | 优先级 | 完成时间 | 状态). Previously, 9 rows in lines 108-116
were 3 columns, generating 16 WARNINGs (1 header + some data rows).

This test locks the 4-column invariant.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
ROW_PATTERN = re.compile(r"^\|\s*\[([^\]]+)\]\(([^)]+)\)\s*\|")


def _count_columns(line: str) -> int:
    return line.count("|") - 1


def test_proposal_approved_data_rows_have_four_columns() -> None:
    """Every linked data row in proposal-approved.md must have 4 columns."""
    path = REPO_ROOT / "proposal-approved.md"
    if not path.is_file():
        pytest.skip("proposal-approved.md not found")
    text = path.read_text()
    in_data = False
    offenders = []
    for line_no, raw in enumerate(text.splitlines(), 1):
        stripped = raw.strip()
        if stripped.startswith("|------") or stripped.startswith("| ---"):
            in_data = True
            continue
        if not in_data or not stripped.startswith("|"):
            continue
        if not ROW_PATTERN.match(stripped):
            continue
        cols = _count_columns(stripped)
        if cols != 4:
            offenders.append(f"  line {line_no}: {cols} columns: {stripped[:80]}")
    assert not offenders, (
        "proposal-approved.md has non-4-column linked rows:\n" + "\n".join(offenders)
    )


def test_proposal_approved_status_column_populated() -> None:
    """The 4th column (status) must be non-empty for every linked row."""
    path = REPO_ROOT / "proposal-approved.md"
    if not path.is_file():
        pytest.skip("proposal-approved.md not found")
    text = path.read_text()
    in_data = False
    empty_status = []
    for line_no, raw in enumerate(text.splitlines(), 1):
        stripped = raw.strip()
        if stripped.startswith("|------") or stripped.startswith("| ---"):
            in_data = True
            continue
        if not in_data or not stripped.startswith("|"):
            continue
        if not ROW_PATTERN.match(stripped):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) < 4 or not cells[3]:
            empty_status.append(f"  line {line_no}: {stripped[:80]}")
    assert not empty_status, (
        "proposal-approved.md rows with empty status column:\n"
        + "\n".join(empty_status)
    )
```

- [ ] **Step 4: Run the new test to verify RED**

Run: `cd $WT_PATH && python3 -m pytest tests/unit/test_proposal_table_schema.py -v 2>&1 | tail -10`
Expected: both FAIL (schema drift still present).

- [ ] **Step 5: Defer commit**

---

### Task 2: Fix `_count_skill_files()` to count only sub-skill SKILL.md

**Files:**
- Modify: `tests/unit/test_doc_contracts.py` (lines 56-60)

- [ ] **Step 1: Replace the counter function**

Edit `tests/unit/test_doc_contracts.py`:

```python
def _count_skill_files() -> int:
    """Count sub-skill SKILL.md files only.

    INSTALL.md is the installer, not a sub-skill — excluded from the
    count so this matches what INSTALL.md ("24 个子技能") and
    package.json (`skills: [...24 entries]`) claim. The previous
    version returned `len(top) + len(sub)` which inflated the count by
    1 and caused 3 baseline failures (fix-skill-count-and-table-schema).
    """
    sub = list((REPO_ROOT / "skills").glob("*/SKILL.md"))
    return len(sub)
```

- [ ] **Step 2: Run test_doc_contracts to verify GREEN**

Run: `cd $WT_PATH && python3 -m pytest tests/unit/test_doc_contracts.py -v 2>&1 | tail -15`
Expected: 10/10 pass (7 already + 3 now fixed).

- [ ] **Step 3: Run full unit suite to verify no regression**

Run: `cd $WT_PATH && python3 -m pytest tests/unit/ -q --tb=short 2>&1 | tail -5`
Expected: no NEW failures (3 fixed, 0 new).

- [ ] **Step 4: Defer commit**

---

### Task 3: Add `状态` column to `proposal-approved.md` lines 108-116

**Files:**
- Modify: `proposal-approved.md` (9 rows, lines 108-116)

- [ ] **Step 1: Read lines 108-116 to confirm scope**

Run: `cd $WT_PATH && sed -n '108,116p' proposal-approved.md`
Expected: 9 rows with 3 columns each.

- [ ] **Step 2: Edit each row to add `| 已批准 |` as the 4th column**

For each of the 9 rows (lines 108-116), replace the trailing `|` with `| 已批准 |`.

Use `Edit` tool with precise oldString/newString. Example for one row:

```
old: | [fix-discover-ship-changes-needs-planning-fallback](.rddf/improvements/fix-discover-ship-changes-needs-planning-fallback.md) | P1 | 2026-08-21 |
new: | [fix-discover-ship-changes-needs-planning-fallback](.rddf/improvements/fix-discover-ship-changes-needs-planning-fallback.md) | P1 | 2026-08-21 | 已批准 |
```

Repeat for all 9 rows.

- [ ] **Step 3: Verify all 9 rows have 4 columns**

Run: `cd $WT_PATH && awk 'NR>=108 && NR<=116' proposal-approved.md | awk -F'|' '{print NR": "NF-2" cols"}'`
Expected: each line shows "4 cols".

- [ ] **Step 4: Run regression test to verify GREEN**

Run: `cd $WT_PATH && python3 -m pytest tests/unit/test_proposal_table_schema.py -v 2>&1 | tail -8`
Expected: 2 passed.

- [ ] **Step 5: Run rdd-doctor to verify WARNING reduced**

Run: `cd $WT_PATH && bash skills/rdd-doctor/scripts/doctor.sh 2>&1 | grep "Summary:"`
Expected: WARNING count drops from 84 → 68 (16 fewer from proposal-table).

- [ ] **Step 6: Defer commit**

---

### Task 4: Run full unit + verification suite

- [ ] **Step 1: Full unit suite**

Run: `cd $WT_PATH && python3 -m pytest tests/unit/ -q --tb=short 2>&1 | tail -5`
Expected: no NEW failures.

- [ ] **Step 2: Run new + fixed tests together**

Run: `cd $WT_PATH && python3 -m pytest tests/unit/test_doc_contracts.py tests/unit/test_proposal_table_schema.py -v 2>&1 | tail -20`
Expected: 12/12 pass (10 doc_contracts + 2 proposal_table).

- [ ] **Step 3: Defer commit**

---

### Task 5: Update `tasks.md` and stage for archive

- [ ] **Step 1: Mark all `- [ ]` as `- [x]` in `openspec/changes/fix-skill-count-and-table-schema/tasks.md`**

Leave CHANGELOG / commit `[ ]`.

- [ ] **Step 2: Stage all changes**

```bash
cd $WT_PATH && git add tests/unit/test_doc_contracts.py \
  tests/unit/test_proposal_table_schema.py \
  proposal-approved.md \
  openspec/changes/fix-skill-count-and-table-schema/tasks.md \
  .rddf/plans/fix-skill-count-and-table-schema.md
git status --short
```

- [ ] **Step 3: Defer commit (orchestrator owns worktree commit)**

---

## Acceptance Verification

- [ ] All 6 AC met (AC-1 through AC-6)
- [ ] 2 new tests pass + 3 baseline failures fixed
- [ ] Full unit suite: no NEW failures
- [ ] rdd-doctor WARNING: 84 → 68
- [ ] INSTALL.md still claims "24 个子技能" (NOT changed)
- [ ] package.json still has 24 skills (NOT changed)
- [ ] `openspec validate fix-skill-count-and-table-schema` → valid

## Out of Scope (DO NOT IMPLEMENT)

- ❌ Modify INSTALL.md skill count (correct as-is)
- ❌ Modify package.json skills array (correct as-is)
- ❌ Modify rdd-doctor `proposal_table_check.py` schema (4 cols is correct)
- ❌ Add new external dependencies
- ❌ Touch `.rddf/state/` files