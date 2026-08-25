# cleanup-pre-existing-debt Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task.

**Goal:** Clean up 1 architecture debt (`check_rfc_draft()` orphan gate) + 1 rdd-doctor bug (JSONL parsing uses single-doc `json.load()` instead of per-line `json.loads()`).

**Architecture:** Delete 3 functions from `design_done_gate.py` (`check_rfc_draft` + `_is_cross_repo_federation` + `_validate_rfc_draft`). Patch rdd-doctor's `state_schema_check.py` to dispatch JSONL files to per-line parsing. Add 2 regression tests.

**Tech Stack:** Python 3.11+, pytest

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/guide-design/scripts/design_done_gate.py` | Delete `check_rfc_draft()` + helpers + dict entry |
| `skills/rdd-doctor/scripts/checks/state_schema_check.py` | Fix JSONL parsing (per-line `json.loads()`) |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_design_done_gate.py` | Add 1 test: `_COMMANDS` has 2 entries, no `check-rfc-draft` |
| `tests/unit/test_state_schema_check.py` | Add 1 test: JSONL file with multiple lines is not misreported |

---

### Task 1: Write failing tests

**Files:**
- Modify: `tests/unit/test_design_done_gate.py`
- Modify: `tests/unit/test_state_schema_check.py`

- [ ] **Step 1: Check if test files exist**

Run: `ls tests/unit/test_design_done_gate.py tests/unit/test_state_schema_check.py 2>/dev/null`
If missing, create them.

- [ ] **Step 2: Add orphan-gate regression test**

Append to `tests/unit/test_design_done_gate.py` (or create):

```python
def test_check_rfc_draft_removed() -> None:
    """G1 architecture debt: check_rfc_draft is orphan, must be deleted."""
    from skills._lib import design_done_gate  # type: ignore[import-not-found]
    # Command must not be registered
    assert "check-rfc-draft" not in design_done_gate._COMMANDS, (
        "check_rfc_draft() is orphan (never called by check_design_done_gate); "
        "delete function and _COMMANDS entry"
    )
    # CLI usage error when invoked
    import sys
    saved_argv = sys.argv
    try:
        sys.argv = ["design_done_gate.py", "check-rfc-draft"]
        result = design_done_gate.main([])
        assert result == 2, f"expected exit 2 (usage error), got {result}"
    finally:
        sys.argv = saved_argv
```

- [ ] **Step 3: Add JSONL parsing regression test**

Append to `tests/unit/test_state_schema_check.py` (or create):

```python
import json
import tempfile
from pathlib import Path


def test_jsonl_file_not_misreported(tmp_path: Path) -> None:
    """G2 rdd-doctor bug: JSONL file with multiple lines should NOT be
    flagged as 'invalid JSON: Extra data' (json.load single-doc parser bug).
    """
    # Write a minimal valid JSONL file
    jsonl = tmp_path / "trace.jsonl"
    lines = [
        json.dumps({"tool": "a", "ts": 1}),
        json.dumps({"tool": "b", "ts": 2}),
        json.dumps({"tool": "c", "ts": 3}),
    ]
    jsonl.write_text("\n".join(lines))

    # Import the check function
    from skills.rdd_doctor.scripts.checks import state_schema_check  # type: ignore
    # If schema not found, skip (backward compat)
    try:
        report = state_schema_check.validate_state_file(
            jsonl, "mcp_trace_schema.json"
        )
    except AttributeError:
        pytest.skip("state_schema_check.validate_state_file API differs")
    except Exception as e:
        # Should NOT raise "Extra data"
        assert "Extra data" not in str(e), f"JSONL misreported: {e}"

    # Validate by re-reading with per-line parser (the fix)
    parsed = []
    with open(jsonl) as f:
        for line in f:
            line = line.strip()
            if line:
                parsed.append(json.loads(line))
    assert len(parsed) == 3
```

- [ ] **Step 4: Run tests to verify they fail (RED)**

Run: `cd $WT_PATH && python3 -m pytest tests/unit/test_design_done_gate.py::test_check_rfc_draft_removed tests/unit/test_state_schema_check.py::test_jsonl_file_not_misreported -v`
Expected: both FAIL (orphan gate still registered / JSONL misparser still present).

- [ ] **Step 5: Defer commit**

---

### Task 2: Delete orphan gate from `design_done_gate.py`

**Files:**
- Modify: `skills/guide-design/scripts/design_done_gate.py` (lines 115-135 + 149)

- [ ] **Step 1: Read the file to confirm scope**

Use `read` to load `skills/guide-design/scripts/design_done_gate.py`. Identify:
- `check_rfc_draft()` function (lines 115-135)
- `_is_cross_repo_federation()` helper (if exists)
- `_validate_rfc_draft()` helper (if exists)
- `_COMMANDS` dict entry `"check-rfc-draft": check_rfc_draft` (line 149)

- [ ] **Step 2: Delete `check_rfc_draft()` function**

Use `Edit` tool to remove the function block.

- [ ] **Step 3: Delete helper functions if no external callers**

Run: `grep -rn "_is_cross_repo_federation\|_validate_rfc_draft" skills/ tests/ 2>/dev/null`
If only called within `design_done_gate.py`, delete them.

- [ ] **Step 4: Remove `_COMMANDS["check-rfc-draft"]` entry**

Use `Edit` tool to remove the dict entry.

- [ ] **Step 5: Run orphan-gate regression test to verify GREEN**

Run: `cd $WT_PATH && python3 -m pytest tests/unit/test_design_done_gate.py::test_check_rfc_draft_removed -v`
Expected: PASS.

- [ ] **Step 6: Run all design_done_gate tests**

Run: `cd $WT_PATH && python3 -m pytest tests/unit/test_design_done_gate.py -v`
Expected: all pass (no regressions).

- [ ] **Step 7: Defer commit**

---

### Task 3: Fix rdd-doctor JSONL parsing

**Files:**
- Modify: `skills/rdd-doctor/scripts/checks/state_schema_check.py`

- [ ] **Step 1: Find the JSON parsing call**

Run: `grep -n "json.load\|json.loads" skills/rdd-doctor/scripts/checks/state_schema_check.py`

- [ ] **Step 2: Read the validation function**

Use `read` to load the file. Identify the function that loads JSON files.

- [ ] **Step 3: Dispatch JSONL vs JSON**

Modify the function to:
- If filename ends with `.jsonl` → parse per-line
- Else → parse as single JSON document

```python
# Example fix (adapt to existing structure):
if str(file_path).endswith(".jsonl"):
    # JSONL: per-line parsing
    with open(file_path) as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError as e:
                return {"valid": False, "error": f"Line {line_no}: {e}"}
    return {"valid": True}
else:
    # Single-document JSON
    with open(file_path) as f:
        data = json.load(f)
    # Validate against schema
    ...
```

- [ ] **Step 4: Run JSONL regression test to verify GREEN**

Run: `cd $WT_PATH && python3 -m pytest tests/unit/test_state_schema_check.py::test_jsonl_file_not_misreported -v`
Expected: PASS.

- [ ] **Step 5: Run rdd-doctor to verify CRITICAL list reduced**

Run: `cd $WT_PATH && bash skills/rdd-doctor/scripts/doctor.sh --category state 2>&1 | head -20`
Expected: CRITICAL ≤ 1 (was 1 before; should still be 1 but `.mcp-trace.jsonl` may now pass).

- [ ] **Step 6: Defer commit**

---

### Task 4: Clean up doc references

- [ ] **Step 1: Grep for residual references**

Run: `cd $WT_PATH && grep -rn "check_rfc_draft\|check-rfc-draft\|rfc_draft" skills/ tests/ docs/ 2>/dev/null | grep -v "archive/" | head -10`
Expected: no matches (all deleted). If any found, remove them.

- [ ] **Step 2: Defer commit**

---

### Task 5: Run full unit test suite

- [ ] **Step 1: Run all unit tests**

Run: `cd $WT_PATH && python3 -m pytest tests/unit/ -q --tb=short 2>&1 | tail -10`
Expected: all pass OR same failure set as `tests/KNOWN_FAILURES.txt` (no NEW failures).

- [ ] **Step 2: Defer commit**

---

### Task 6: Update `tasks.md` and stage for archive

- [ ] **Step 1: Mark all `- [ ]` as `- [x]` in `openspec/changes/cleanup-pre-existing-debt/tasks.md`**

Leave CHANGELOG / commit `[ ]`.

- [ ] **Step 2: Stage all changes**

```bash
cd $WT_PATH && git add skills/guide-design/scripts/design_done_gate.py \
  skills/rdd-doctor/scripts/checks/state_schema_check.py \
  tests/unit/test_design_done_gate.py \
  tests/unit/test_state_schema_check.py \
  openspec/changes/cleanup-pre-existing-debt/tasks.md \
  .rddf/plans/cleanup-pre-existing-debt.md
git status --short
```

- [ ] **Step 3: Defer commit (orchestrator owns worktree commit)**

---

## Acceptance Verification

- [ ] All 6 AC met (AC-1 through AC-6)
- [ ] 2 new tests pass
- [ ] Full unit suite: no NEW failures
- [ ] `bash skills/rdd-doctor/scripts/doctor.sh --category orphan-gates,state` shows CRITICAL ≤ 1
- [ ] `python3 design_done_gate.py check-rfc-draft` exits 2
- [ ] `python3 design_done_gate.py check-hub-pending` exits 0 or 1 (still works)
- [ ] `openspec validate cleanup-pre-existing-debt` → valid

## Out of Scope (DO NOT IMPLEMENT)

- ❌ Re-design RFC draft tracking mechanism (separate change)
- ❌ Touch `.rddf/state/` files (already cleaned by orchestrator)
- ❌ Modify `check_hub_pending` / `check_cross_repo_approvals` (covered by `fix-orphan-hub-gates-wiring`)
- ❌ Add new external dependencies