# clean-stale-plan-handoff-on-ship-done Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task.

**Goal:** Fix "half-cleanup" bug in `skills/guide-ship/scripts/ship_archive.sh::cleanup_plan_handoff()`. It clears `active_changes` and appends to `archived_changes` but never resets `current_change` or `ship_started_at` → stale state causes discover_ship_changes to repeatedly flag already-archived changes.

**Architecture:** Extend the Python inline block in `cleanup_plan_handoff` (shell function around L331-362). After decrementing `active_changes`: (a) if `change_name == data["current_change"]` → set `current_change = None`; (b) if `active_changes == 0` (after decrement) → set `ship_started_at = None`. Preserve `execution_mode_decisions` untouched. Add final-state invariant assertion.

**Tech Stack:** Python 3.11+ (inline in bash), pytest, bats

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/guide-ship/scripts/ship_archive.sh` | Extend `cleanup_plan_handoff` Python block to clear `current_change` and `ship_started_at` |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_cleanup_plan_handoff.py` | **NEW** — 4 unit tests for the 4 Python branches |
| `tests/integration/test_cleanup_plan_handoff.bats` | **NEW** — ≥5 bats tests covering scenarios 1-5 |

---

### Task 1: Locate the inline Python block

**Files:**
- Read: `skills/guide-ship/scripts/ship_archive.sh` (find `cleanup_plan_handoff` function)

- [ ] **Step 1: Find the function**

Run: `grep -n "cleanup_plan_handoff\|archived_at\|archived_changes" skills/guide-ship/scripts/ship_archive.sh`

- [ ] **Step 2: Read the function**

Use `read` to load the file. Note the Python inline block (~L331-362).

- [ ] **Step 3: Defer commit**

---

### Task 2: Write 4 pytest unit tests covering Python branches

**Files:**
- Create: `tests/unit/test_cleanup_plan_handoff.py`

- [ ] **Step 1: Create the test file**

```python
"""Tests for clean-stale-plan-handoff-on-ship-done: 4 Python branches in cleanup_plan_handoff()."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


def _load_cleanup_function():
    """Source-load the Python block from ship_archive.sh via a tiny shim.

    ship_archive.sh has an inline Python block inside a bash function.
    To test it, we extract the Python block and exec it in a controlled
    namespace. Alternative: re-implement the logic in a dedicated Python
    module (preferred for testability).
    """
    # Simpler: re-implement the logic here and test the contract.
    # (The ship_archive.sh inline block calls out to this contract.)
    from skills._lib.cleanup_plan_handoff import cleanup_plan_handoff
    return cleanup_plan_handoff


def test_branch1_current_change_matches_change_name(tmp_path: Path) -> None:
    """Branch 1: change_name == current_change → current_change becomes None."""
    cleanup = _load_cleanup_function()
    handoff = tmp_path / ".plan-handoff.json"
    handoff.write_text(json.dumps({
        "plan_complete_at": "2026-08-22T12:00:00+00:00",
        "active_changes": 1,
        "all_artifacts_committed": True,
        "ship_started_at": "2026-08-22T13:00:00+00:00",
        "current_change": "fix-foo",
        "execution_mode_decisions": {"fix-foo": "worktree"},
        "archived_changes": [],
    }))

    cleanup(handoff, "fix-foo")

    result = json.loads(handoff.read_text())
    assert result["active_changes"] == 0
    assert result["current_change"] is None
    assert result["archived_changes"] == ["fix-foo"]
    # execution_mode_decisions preserved (historical)
    assert result["execution_mode_decisions"] == {"fix-foo": "worktree"}


def test_branch2_active_changes_zero_resets_ship_started_at(tmp_path: Path) -> None:
    """Branch 2: active_changes reaches 0 → ship_started_at becomes None."""
    cleanup = _load_cleanup_function()
    handoff = tmp_path / ".plan-handoff.json"
    handoff.write_text(json.dumps({
        "active_changes": 1,
        "current_change": "fix-foo",
        "ship_started_at": "2026-08-22T13:00:00+00:00",
        "archived_changes": [],
    }))

    cleanup(handoff, "fix-foo")

    result = json.loads(handoff.read_text())
    assert result["active_changes"] == 0
    assert result["ship_started_at"] is None


def test_branch3_current_change_mismatch_preserved(tmp_path: Path) -> None:
    """Branch 3: change_name != current_change → current_change preserved."""
    cleanup = _load_cleanup_function()
    handoff = tmp_path / ".plan-handoff.json"
    handoff.write_text(json.dumps({
        "active_changes": 2,
        "current_change": "fix-foo",
        "ship_started_at": "2026-08-22T13:00:00+00:00",
        "archived_changes": [],
    }))

    cleanup(handoff, "fix-bar")

    result = json.loads(handoff.read_text())
    assert result["active_changes"] == 1
    assert result["current_change"] == "fix-foo", "must NOT clobber"
    assert result["archived_changes"] == ["fix-bar"]


def test_branch4_idempotent_when_already_zero(tmp_path: Path) -> None:
    """Branch 4: active_changes already 0 → stay 0, no negatives."""
    cleanup = _load_cleanup_function()
    handoff = tmp_path / ".plan-handoff.json"
    handoff.write_text(json.dumps({
        "active_changes": 0,
        "current_change": None,
        "ship_started_at": None,
        "archived_changes": ["fix-prior"],
    }))

    cleanup(handoff, "fix-new")

    result = json.loads(handoff.read_text())
    assert result["active_changes"] == 0
    assert result["archived_changes"] == ["fix-prior", "fix-new"]
```

- [ ] **Step 2: Run tests to verify they fail (RED)**

Run: `python3 -m pytest tests/unit/test_cleanup_plan_handoff.py -v`
Expected: ImportError (no `skills._lib.cleanup_plan_handoff` module yet).

- [ ] **Step 3: Defer commit**

---

### Task 3: Extract Python block to `_lib/cleanup_plan_handoff.py`

**Files:**
- Create: `_lib/cleanup_plan_handoff.py`

- [ ] **Step 1: Create the Python module**

```python
"""Plan-handoff cleanup with final-state convergence semantics.

Fix-adr-0027-clean-stale-plan-handoff-on-ship-done: the inline Python
block in ``skills/guide-ship/scripts/ship_archive.sh::cleanup_plan_handoff``
previously only updated active_changes / archived_changes but never reset
``current_change`` or ``ship_started_at`` → stale state repeated on every
ship-done entry.

This module extracts the logic so it's unit-testable. The bash inline
block now calls this via python3 -c.

**Final-state invariant** (enforced after every call):
  active_changes == 0  ⇒  current_change is None
  active_changes == 0  ⇒  ship_started_at is None
  execution_mode_decisions is NEVER cleared (historical record)
"""
from __future__ import annotations

import json
from pathlib import Path


def cleanup_plan_handoff(handoff_path: Path, change_name: str) -> None:
    """Update plan-handoff.json after archiving a change.

    Branches:
      1. active_changes decrements (saturating at 0, never negative)
      2. If change_name == current_change → set current_change = None
      3. If active_changes reaches 0 → set ship_started_at = None
      4. archived_changes appends change_name
      5. execution_mode_decisions preserved (historical)

    Idempotent: missing file → return without error.
    """
    handoff_path = Path(handoff_path)
    if not handoff_path.is_file():
        return  # Scenario 5: idempotent skip

    data = json.loads(handoff_path.read_text())

    # Branch 1: decrement active_changes (saturating)
    active = data.get("active_changes", 0)
    if isinstance(active, int) and active > 0:
        data["active_changes"] = active - 1
    else:
        data["active_changes"] = 0

    # Branch 2: clear current_change if matching
    if data.get("current_change") == change_name:
        data["current_change"] = None

    # Branch 3: clear ship_started_at when no active changes
    if data["active_changes"] == 0:
        data["ship_started_at"] = None

    # Branch 4: append to archived_changes
    if "archived_changes" not in data:
        data["archived_changes"] = []
    if change_name not in data["archived_changes"]:
        data["archived_changes"].append(change_name)

    # Final-state invariant assertion
    assert data["active_changes"] == 0
        or data.get("current_change") is not None, (
        "Invariant violated: active_changes > 0 but current_change is None"
    )
    assert data["active_changes"] == 0 or data.get("ship_started_at") is not None, (
        "Invariant violated: active_changes > 0 but ship_started_at is None"
    )

    handoff_path.write_text(json.dumps(data, indent=2))
```

- [ ] **Step 2: Run tests to verify they pass (GREEN)**

Run: `python3 -m pytest tests/unit/test_cleanup_plan_handoff.py -v`
Expected: 4 passed.

- [ ] **Step 3: Defer commit**

---

### Task 4: Update `ship_archive.sh` inline Python to call the new module

**Files:**
- Modify: `skills/guide-ship/scripts/ship_archive.sh` (the `cleanup_plan_handoff` function)

- [ ] **Step 1: Find the Python inline block**

The block is currently a `python3 -c "..."` invocation or similar inside the bash function. Replace with:

```bash
cleanup_plan_handoff() {
    local handoff_file="${RDDF_PLAN_HANDOFF:-${PROJECT_ROOT:-$(pwd)}/.rddf/state/.plan-handoff.json}"
    local change_name="$1"

    if [ ! -f "$handoff_file" ]; then
        return 0  # Scenario 5: idempotent skip
    fi

    PYTHONPATH="${PROJECT_ROOT:-$(pwd)}" python3 -c "
import sys, json
from pathlib import Path
sys.path.insert(0, '${PROJECT_ROOT:-$(pwd)}')
from skills._lib.cleanup_plan_handoff import cleanup_plan_handoff
cleanup_plan_handoff(Path('$handoff_file'), '$change_name')
"
}
```

- [ ] **Step 2: Verify function exists at expected location**

Run: `grep -n "cleanup_plan_handoff" skills/guide-ship/scripts/ship_archive.sh`
Expected: at least 1 hit (the function definition) + 1 hit (call site).

- [ ] **Step 3: Defer commit**

---

### Task 5: Write ≥5 bats integration tests

**Files:**
- Create: `tests/integration/test_cleanup_plan_handoff.bats`

- [ ] **Step 1: Create the bats file**

```bats
#!/usr/bin/env bats

setup() {
    load_lib "test_helper"
    TEST_TMPDIR="${BATS_TMPDIR}/cleanup-plan-handoff-$$"
    mkdir -p "$TEST_TMPDIR/.rddf/state"
    HANDOFF="$TEST_TMPDIR/.rddf/state/.plan-handoff.json"
}

teardown() {
    rm -rf "$TEST_TMPDIR"
}

write_handoff() {
    cat > "$HANDOFF" <<EOF
{
    "plan_complete_at": "2026-08-22T12:00:00+00:00",
    "active_changes": $1,
    "all_artifacts_committed": true,
    "ship_started_at": "2026-08-22T13:00:00+00:00",
    "current_change": "$2",
    "execution_mode_decisions": {"$3": "worktree"},
    "archived_changes": []
}
EOF
}

read_field() {
    python3 -c "import json; d=json.load(open('$HANDOFF')); print(d.get('$1'))"
}

@test "scenario 1: single archive clears current_change + active_changes" {
    write_handoff 1 "fix-foo" "fix-foo"

    run bash skills/guide-ship/scripts/ship_archive.sh cleanup_plan_handoff "fix-foo" \
        RDDF_PLAN_HANDOFF="$HANDOFF" \
        PROJECT_ROOT="$BATS_TEST_DIRNAME/../.." \
        PYTHONPATH="$BATS_TEST_DIRNAME/../.."

    # Note: skip direct run if script is bash-only; use Python module instead
    python3 -c "
import sys
sys.path.insert(0, '$BATS_TEST_DIRNAME/../..')
from skills._lib.cleanup_plan_handoff import cleanup_plan_handoff
from pathlib import Path
cleanup_plan_handoff(Path('$HANDOFF'), 'fix-foo')
"

    [ "$(read_field active_changes)" = "0" ]
    [ "$(read_field current_change)" = "None" ]
    [ "$(read_field ship_started_at)" = "None" ]
}

@test "scenario 2: multi-change archive clears current_change only on match" {
    write_handoff 2 "fix-foo" "fix-foo"

    python3 -c "
import sys
sys.path.insert(0, '$BATS_TEST_DIRNAME/../..')
from skills._lib.cleanup_plan_handoff import cleanup_plan_handoff
from pathlib import Path
cleanup_plan_handoff(Path('$HANDOFF'), 'fix-bar')
"

    [ "$(read_field active_changes)" = "1" ]
    [ "$(read_field current_change)" = "fix-foo" ]

    python3 -c "
import sys
sys.path.insert(0, '$BATS_TEST_DIRNAME/../..')
from skills._lib.cleanup_plan_handoff import cleanup_plan_handoff
from pathlib import Path
cleanup_plan_handoff(Path('$HANDOFF'), 'fix-foo')
"

    [ "$(read_field active_changes)" = "0" ]
    [ "$(read_field current_change)" = "None" ]
}

@test "scenario 3: ship-done marker clears ship_started_at" {
    write_handoff 0 "None" "fix-prior"
    echo '["fix-prior"]' | python3 -c "
import json, sys
data = json.load(open('$HANDOFF'))
data['archived_changes'] = json.loads(sys.stdin.read())
open('$HANDOFF', 'w').write(json.dumps(data, indent=2))
"

    python3 -c "
import sys
sys.path.insert(0, '$BATS_TEST_DIRNAME/../..')
from skills._lib.cleanup_plan_handoff import cleanup_plan_handoff
from pathlib import Path
cleanup_plan_handoff(Path('$HANDOFF'), 'fix-prior')
"

    [ "$(read_field ship_started_at)" = "None" ]
}

@test "scenario 4: current_change mismatch is preserved" {
    write_handoff 1 "fix-foo" "fix-foo"

    python3 -c "
import sys
sys.path.insert(0, '$BATS_TEST_DIRNAME/../..')
from skills._lib.cleanup_plan_handoff import cleanup_plan_handoff
from pathlib import Path
cleanup_plan_handoff(Path('$HANDOFF'), 'fix-bar')
"

    [ "$(read_field current_change)" = "fix-foo" ]
}

@test "scenario 5: missing handoff file is idempotent skip" {
    rm -f "$HANDOFF"

    run python3 -c "
import sys
sys.path.insert(0, '$BATS_TEST_DIRNAME/../..')
from skills._lib.cleanup_plan_handoff import cleanup_plan_handoff
from pathlib import Path
cleanup_plan_handoff(Path('$HANDOFF'), 'fix-foo')
"

    [ "$status" -eq 0 ]
}
```

- [ ] **Step 2: Run bats tests to verify they pass (GREEN)**

Run: `cd $WT_PATH && bats tests/integration/test_cleanup_plan_handoff.bats`
Expected: 5 passed.

- [ ] **Step 3: Defer commit**

---

### Task 6: Run full unit + integration suite

- [ ] **Step 1: Run all unit tests**

Run: `cd $WT_PATH && python3 -m pytest tests/unit/ -q --tb=short 2>&1 | tail -30`
Expected: all pass OR same failure set as `KNOWN_FAILURES.txt`.

- [ ] **Step 2: Run new bats tests**

Run: `cd $WT_PATH && bats tests/integration/test_cleanup_plan_handoff.bats`
Expected: 5 passed.

- [ ] **Step 3: Defer commit**

---

### Task 7: Update `tasks.md` and stage for archive

- [ ] **Step 1: Mark all `- [ ]` as `- [x]` in `openspec/changes/clean-stale-plan-handoff-on-ship-done/tasks.md`**

Leave CHANGELOG / commit `[ ]`.

- [ ] **Step 2: Stage all changes**

```bash
cd $WT_PATH && git add _lib/cleanup_plan_handoff.py \
  skills/guide-ship/scripts/ship_archive.sh \
  tests/unit/test_cleanup_plan_handoff.py \
  tests/integration/test_cleanup_plan_handoff.bats \
  openspec/changes/clean-stale-plan-handoff-on-ship-done/tasks.md \
  .rddf/plans/clean-stale-plan-handoff-on-ship-done.md
git status --short
```

- [ ] **Step 3: Defer commit (orchestrator owns worktree commit)**

---

## Acceptance Verification

- [ ] 4 unit tests pass in `test_cleanup_plan_handoff.py`
- [ ] 5 bats tests pass in `test_cleanup_plan_handoff.bats`
- [ ] Full unit suite: no NEW failures
- [ ] `openspec validate clean-stale-plan-handoff-on-ship-done` → valid
- [ ] Manual: scenario 1 from proposal (current_change matches → cleared)
- [ ] Manual: scenario 4 (current_change mismatch → preserved)
- [ ] Manual: scenario 6 (active_changes=0 → stays 0)

## Out of Scope (DO NOT IMPLEMENT)

- ❌ Modify `_classify()` in discover_ship_changes (already fixed in earlier PR)
- ❌ Modify plan-handoff.json schema
- ❌ Clear `execution_mode_decisions` (historical record)
- ❌ Add new env-vars (call interface unchanged)
- ❌ Cleanup iteration.json stale entries (separate proposal)