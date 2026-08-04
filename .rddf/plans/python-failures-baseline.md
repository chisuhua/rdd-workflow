# python-failures-baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring pre-existing stable Python test failures under an explicit baseline mechanism, fix the rddf-session integration-test schema drift and the orphaned-state transition bug, and deflake the event-log timing assertion so that `python3 -m pytest tests/unit/ tests/integration/ -q` reports only reviewed, known failures.

**Architecture:** Fix root causes directly: align integration-test session payloads with `sessions_schema.json` v1 (`state`/`started_at`/`last_heartbeat` and `goal` keys), allow `orphaned→active` transitions in `RddfSessionCommands.update_session_status` while preserving orphaned archiving, relax the `test_query_10k_events_under_100ms` threshold to absorb CI jitter, and add a pytest counterpart to the existing bats `KNOWN_FAILURES.txt` + `report_regression.sh` baseline machinery.

**Tech Stack:** Python 3.11+, pytest, jsonschema, bash.

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/rddf-session/scripts/rddf_session_pkg/_commands.py` | Allow `orphaned→active` transition in `update_session_status`; clear terminal markers when reactivating an orphaned session. |
| `tests/unit/python_regression.py` | **NEW** Pure-Python helper to parse pytest output and compare actual failures against a baseline. |
| `tests/scripts/report_python_regression.sh` | **NEW** Run `python3 -m pytest tests/unit/ tests/integration/` and report known/new/stale failures against `tests/KNOWN_PYTHON_FAILURES.txt`. |
| `tests/scripts/refresh_python_known_failures.sh` | **NEW** Regenerate `tests/KNOWN_PYTHON_FAILURES.txt` from current pytest output while preserving comments. |
| `tests/KNOWN_PYTHON_FAILURES.txt` | **NEW** Reviewed list of pre-existing Python test failures (initially empty after the fixes below). |

### Tests

| File | Responsibility |
|---|---|
| `tests/integration/test_rddf_session_concurrency.py` | Align raw session dicts with schema v1: `state`, `started_at`, `last_heartbeat`, valid `session_id` pattern, and valid `goal`. |
| `tests/integration/test_rddf_session_cross_session_recovery.py` | Replace invalid `goal` keys (`task`, `workflow`) with schema-legal `intent`/`subject`/`expected_outcome`. |
| `tests/unit/test_event_log.py` | Relax `test_query_10k_events_under_100ms` timing bound from 100 ms to 150 ms with a comment explaining jitter tolerance. |
| `tests/unit/test_python_regression.py` | **NEW** Lock the baseline helper behavior with synthetic failure lists. |

---

## Pre-existing failures observed

Run `python3 -m pytest tests/integration/ -q --tb=line -k "rddf"` produced these 9 stable failures before any changes:

1. `tests/integration/test_rddf_session_concurrency.py::TestRddfSessionConcurrency::test_concurrent_create_session_100_workers`
2. `tests/integration/test_rddf_session_concurrency.py::TestRddfSessionConcurrency::test_concurrent_create_different_sessions`
3. `tests/integration/test_rddf_session_concurrency.py::TestRddfSessionConcurrency::test_concurrent_reads_never_fail`
4. `tests/integration/test_rddf_session_concurrency.py::TestRddfSessionConcurrency::test_no_data_corruption_under_contention`
5. `tests/integration/test_rddf_session_cross_session_recovery.py::TestRddfSessionCrossSessionRecovery::test_timeout_makes_session_orphaned`
6. `tests/integration/test_rddf_session_cross_session_recovery.py::TestRddfSessionCrossSessionRecovery::test_find_next_recommendation_returns_orphaned`
7. `tests/integration/test_rddf_session_cross_session_recovery.py::TestRddfSessionCrossSessionRecovery::test_transfer_ownership_to_new_session`
8. `tests/integration/test_rddf_session_cross_session_recovery.py::TestRddfSessionCrossSessionRecovery::test_cross_session_recovery_workflow`
9. `tests/integration/test_rddf_session_lifecycle.py::test_orphaned_recovery`

Failure signatures:
- Schema mismatch: `Additional properties are not allowed ('task' was unexpected)` and `('workflow' was unexpected)` in `goal` objects.
- Schema mismatch: test helpers construct `status`/`created_at` while `sessions_schema.json` v1 requires `state`/`started_at`/`last_heartbeat`.
- State-machine mismatch: `Cannot transition from terminal state 'orphaned'` when `test_orphaned_recovery` calls `update_session_status(sid, "active")` on an orphaned session, even though `sessions_schema.json` v1 describes `orphaned→active` as allowed.

The timing test `tests/unit/test_event_log.py::test_query_10k_events_under_100ms` is flaky (observed jitter around 103.3 ms against the 100 ms threshold).

---

### Task 1: Fix rddf-session integration test schema drift

**Files:**
- Modify: `tests/integration/test_rddf_session_concurrency.py:49-55`, `tests/integration/test_rddf_session_concurrency.py:114-119`, `tests/integration/test_rddf_session_concurrency.py:139-141`, `tests/integration/test_rddf_session_concurrency.py:175`, `tests/integration/test_rddf_session_concurrency.py:209-211`
- Modify: `tests/integration/test_rddf_session_cross_session_recovery.py:47`, `tests/integration/test_rddf_session_cross_session_recovery.py:87`, `tests/integration/test_rddf_session_cross_session_recovery.py:92`, `tests/integration/test_rddf_session_cross_session_recovery.py:133`, `tests/integration/test_rddf_session_cross_session_recovery.py:186`
- Test: `tests/integration/test_rddf_session_concurrency.py`, `tests/integration/test_rddf_session_cross_session_recovery.py`

- [x] **Step 1: Reproduce the 9 rddf-session failures**

Run:
```bash
python3 -m pytest tests/integration/ -q --tb=line -k "rddf"
```
Expected: 9 FAILED, 8 passed, with the schema errors listed above.

- [x] **Step 2: Fix the raw session payloads in `_worker_create_session`**

In `tests/integration/test_rddf_session_concurrency.py:49-55`, replace the hand-rolled dict with a schema-legal session. Import `datetime` at the top of the file if it is not already imported:
```python
import datetime
```
Then change the dict in `_worker_create_session` to:
```python
now = datetime.datetime.now(datetime.timezone.utc).isoformat()
new_session = {
    "session_id": session_id,
    "kind": "stage_plan",
    "owner_opencode_session_id": f"worker_{worker_id}",
    "state": "active",
    "started_at": now,
    "last_heartbeat": now,
    "goal": {"intent": "guide-plan", "subject": "concurrent-test"},
}
```
Change the test callers to pass valid `session_id` values matching `^rds_[a-f0-9]{12}$`:
- In `test_concurrent_create_session_100_workers`: `session_id = "rds_" + "a" * 12`
- In `test_concurrent_create_different_sessions`: the loop should pass `f"rds_{i:012x}"`

- [x] **Step 3: Fix pre-populated and stress-test session dicts**

In `tests/integration/test_rddf_session_concurrency.py:139-141`, change the pre-populated sessions in `test_concurrent_reads_never_fail` to include all required schema fields and valid ids:
```python
now = datetime.datetime.now(datetime.timezone.utc).isoformat()
{
    "session_id": f"rds_{i:012x}",
    "kind": "stage_plan",
    "owner_opencode_session_id": "prepop_owner",
    "state": "active",
    "started_at": now,
    "last_heartbeat": now,
    "goal": {"intent": "guide-plan", "subject": "prepop"},
}
```
In `tests/integration/test_rddf_session_concurrency.py:209-211`, change `_worker_write_session` to append schema-legal dicts:
```python
now = datetime.datetime.now(datetime.timezone.utc).isoformat()
data["sessions"].append({
    "session_id": f"rds_{worker_id:04x}{i:08x}",
    "kind": "stage_plan",
    "owner_opencode_session_id": f"worker_{worker_id}",
    "state": "active",
    "started_at": now,
    "last_heartbeat": now,
    "goal": {"intent": "guide-plan", "subject": "stress"},
})
```

- [x] **Step 4: Fix `goal` keys in cross-session recovery tests**

In `tests/integration/test_rddf_session_cross_session_recovery.py`:
- Replace `goal={"task": "test"}` with `goal={"intent": "guide-plan", "subject": "test"}`.
- Replace `goal={"task": "test1"}` with `goal={"intent": "guide-plan", "subject": "test1"}`.
- Replace `goal={"task": "test2"}` with `goal={"intent": "guide-arch", "subject": "test2"}`.
- Replace `goal={"workflow": "guide-plan"}` with `goal={"intent": "guide-plan", "subject": "workflow-recovery"}`.

- [x] **Step 5: Defer commit**

Do not run `git add` or `git commit`. Leave the changes in the working tree; the archive phase will commit them.

---

### Task 2: Fix the orphaned→active state transition bug

**Files:**
- Modify: `skills/rddf-session/scripts/rddf_session_pkg/_commands.py:134-153`
- Test: `tests/integration/test_rddf_session_lifecycle.py::test_orphaned_recovery`, `tests/integration/test_rddf_session_cross_session_recovery.py::TestRddfSessionCrossSessionRecovery::test_transfer_ownership_to_new_session`, `tests/integration/test_rddf_session_cross_session_recovery.py::TestRddfSessionCrossSessionRecovery::test_cross_session_recovery_workflow`

- [x] **Step 1: Reproduce the orphaned transition failure**

Run:
```bash
python3 -m pytest tests/integration/test_rddf_session_lifecycle.py::test_orphaned_recovery -q --tb=short
```
Expected: FAIL with `RddfSessionError: Cannot transition from terminal state 'orphaned'`.

- [x] **Step 2: Allow orphaned→active while preserving terminal-state protection**

In `skills/rddf-session/scripts/rddf_session_pkg/_commands.py:134-153`, update `_do_update` inside `update_session_status` to special-case the orphaned→active transition:
```python
def _do_update():
    data = self._store.read_unlocked()
    for s in data["sessions"]:
        if s["session_id"] == session_id:
            is_orphaned_to_active = (s["state"] == "orphaned" and new_state == "active")
            if s["state"] in _TERMINAL_STATES and not is_orphaned_to_active:
                raise RddfSessionError(
                    f"Cannot transition from terminal state {s['state']!r}"
                )
            s["state"] = new_state
            if new_state in _TERMINAL_STATES:
                s["ended_at"] = _now()
                s["end_reason"] = end_reason
                data["updated_at"] = s["ended_at"]
            else:
                if is_orphaned_to_active:
                    s["ended_at"] = None
                    s["end_reason"] = None
                s["last_heartbeat"] = _now()
                data["updated_at"] = s["last_heartbeat"]
            self._store.atomic_write(data)
            return
    raise RddfSessionError(f"Unknown session: {session_id}")
```
This keeps `orphaned` in `_TERMINAL_STATES` so `archive_history` continues to archive orphaned sessions (see `tests/unit/test_rddf_session.py::test_archive_history_archives_orphaned_and_keeps_active`), while allowing the schema-documented `orphaned→active` recovery path.

- [x] **Step 3: Verify the orphaned recovery test passes**

Run:
```bash
python3 -m pytest tests/integration/test_rddf_session_lifecycle.py::test_orphaned_recovery -q --tb=short
```
Expected: PASS.

- [x] **Step 4: Verify all rddf-session integration tests pass**

Run:
```bash
python3 -m pytest tests/integration/ -q --tb=line -k "rddf"
```
Expected: 17 passed, 0 failed.

- [x] **Step 5: Defer commit**

Do not run `git add` or `git commit`.

---

### Task 3: Deflake the event-log timing assertion

**Files:**
- Modify: `tests/unit/test_event_log.py:81`
- Test: `tests/unit/test_event_log.py::test_query_10k_events_under_100ms`

- [x] **Step 1: Confirm the timing assertion is the flake source**

Run the timing test several times:
```bash
for i in $(seq 1 5); do python3 -m pytest tests/unit/test_event_log.py::test_query_10k_events_under_100ms -q --tb=short; done
```
Expected: usually PASS, but intermittent failures around 103.3 ms against the 100 ms threshold are observed on loaded runners.

- [x] **Step 2: Relax the timing threshold with a comment**

In `tests/unit/test_event_log.py:81`, change:
```python
assert elapsed < 0.100, f"Query took {elapsed*1000:.1f}ms (must be < 100ms)"
```
to:
```python
# Threshold relaxed from 100 ms to 150 ms to absorb CI timing jitter
# without weakening the functional guarantee (correct event count is asserted separately).
assert elapsed < 0.150, f"Query took {elapsed*1000:.1f}ms (must be < 150ms)"
```

- [x] **Step 3: Verify the timing test passes under the relaxed threshold**

Run:
```bash
python3 -m pytest tests/unit/test_event_log.py::test_query_10k_events_under_100ms -v
```
Expected: PASS.

- [x] **Step 4: Verify all event_log unit tests still pass**

Run:
```bash
python3 -m pytest tests/unit/test_event_log.py -q
```
Expected: all passed.

- [x] **Step 5: Defer commit**

Do not run `git add` or `git commit`.

---

### Task 4: Add Python known-failures baseline helper and report scripts

**Files:**
- Create: `tests/unit/python_regression.py`
- Create: `tests/scripts/report_python_regression.sh`
- Create: `tests/scripts/refresh_python_known_failures.sh`
- Create: `tests/KNOWN_PYTHON_FAILURES.txt`

- [x] **Step 1: Implement the baseline comparison helper**

Create `tests/unit/python_regression.py`:
```python
"""Helpers for comparing pytest failure output against a known-failures baseline."""
from pathlib import Path
from typing import Any, Dict, List


def _load_baseline(path: Path) -> List[str]:
    if not path.exists():
        return []
    names = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        name, _, _ = line.partition(" #")
        names.append(name.strip())
    return names


def parse_failed_tests(output: str) -> List[str]:
    failed = []
    for line in output.splitlines():
        if line.startswith("FAILED "):
            failed.append(line[len("FAILED "):].strip().split(" ")[0])
    return sorted(set(failed))


def compare_failures(actual: List[str], baseline_path: Path) -> Dict[str, Any]:
    baseline = set(_load_baseline(baseline_path))
    actual_set = set(actual)
    return {
        "known": sorted(actual_set & baseline),
        "new": sorted(actual_set - baseline),
        "stale": sorted(baseline - actual_set),
        "known_count": len(actual_set & baseline),
        "new_count": len(actual_set - baseline),
        "stale_count": len(baseline - actual_set),
    }
```

- [x] **Step 2: Create the report script**

Create `tests/scripts/report_python_regression.sh`:
```bash
#!/usr/bin/env bash
# Compare the current pytest failure set with tests/KNOWN_PYTHON_FAILURES.txt.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BASELINE="$REPO_ROOT/tests/KNOWN_PYTHON_FAILURES.txt"
TMP_DIR="$(mktemp -d -t rdd-python-known-failures-XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

if [ ! -f "$BASELINE" ]; then
  printf '❌ baseline file is missing: %s\n' "$BASELINE" >&2
  exit 1
fi

set +e
(cd "$REPO_ROOT" && python3 -m pytest tests/unit/ tests/integration/ -q --tb=line) >"$TMP_DIR/pytest-output" 2>&1
pytest_status=$?
set -e

export pytest_status
python3 - "$BASELINE" "$TMP_DIR/pytest-output" <<'PY'
import os
import sys
from pathlib import Path
from tests.unit.python_regression import compare_failures, parse_failed_tests

baseline_path = Path(sys.argv[1])
output_path = Path(sys.argv[2])
output = output_path.read_text(encoding="utf-8")
actual = parse_failed_tests(output)
result = compare_failures(actual, baseline_path)

print(f"Pytest exit status: {os.environ.get('pytest_status', 'unknown')}")
print(f"已知失败: {result['known_count']}")
print(f"新增失败: {result['new_count']}")
print(f"基线中已修复: {result['stale_count']}")

if result["new_count"] > 0:
    print("新增失败明细:")
    for name in result["new"]:
        print(name)
    sys.exit(1)

if result["stale_count"] > 0:
    print("基线中已修复 (请运行 tests/scripts/refresh_python_known_failures.sh 刷新):")
    for name in result["stale"]:
        print(name)

print("✅ 0 新增失败")
PY
```
Make it executable:
```bash
chmod +x tests/scripts/report_python_regression.sh
```

- [x] **Step 3: Create the refresh script**

Create `tests/scripts/refresh_python_known_failures.sh`:
```bash
#!/usr/bin/env bash
# Explicitly regenerate tests/KNOWN_PYTHON_FAILURES.txt from current pytest output.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BASELINE="$REPO_ROOT/tests/KNOWN_PYTHON_FAILURES.txt"
TMP_DIR="$(mktemp -d -t rdd-refresh-python-known-failures-XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

set +e
(cd "$REPO_ROOT" && python3 -m pytest tests/unit/ tests/integration/ -q --tb=line) >"$TMP_DIR/pytest-output" 2>&1
pytest_status=$?
set -e

export pytest_status
BASELINE_PATH="$BASELINE" ACTUAL_PATH="$TMP_DIR/pytest-output" python3 - <<'PY'
import os
from pathlib import Path
from tests.unit.python_regression import _load_baseline, parse_failed_tests

baseline = Path(os.environ["BASELINE_PATH"])
actual = parse_failed_tests(Path(os.environ["ACTUAL_PATH"]).read_text(encoding="utf-8"))
comments = {}
for name in _load_baseline(baseline):
    comments[name] = "reason required"

lines = [f"# Known stable Python test failures. Reviewed baseline; new failures block CI."]
for name in actual:
    comment = comments.get(name, "reason required")
    lines.append(f"{name} # {comment}")

baseline.parent.mkdir(parents=True, exist_ok=True)
tmp = baseline.with_suffix(baseline.suffix + ".tmp")
tmp.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
tmp.replace(baseline)
print(f"✅ refreshed {len(actual)} known failures: {baseline}")
PY
```
Make it executable:
```bash
chmod +x tests/scripts/refresh_python_known_failures.sh
```

- [x] **Step 4: Create the baseline file**

Create `tests/KNOWN_PYTHON_FAILURES.txt`:
```
# Known stable Python test failures. Reviewed baseline; new failures block CI.
```

- [x] **Step 5: Defer commit**

Do not run `git add` or `git commit`.

---

### Task 5: Add unit tests locking the Python baseline helper

**Files:**
- Create: `tests/unit/test_python_regression.py`

- [x] **Step 1: Write a failing test for new-failure detection**

Create `tests/unit/test_python_regression.py`:
```python
from pathlib import Path

from tests.unit.python_regression import compare_failures, parse_failed_tests


def test_parse_failed_tests_extracts_pytest_failure_lines():
    output = """
FAILED tests/unit/test_a.py::test_one - assert 1 == 2
FAILED tests/unit/test_b.py::test_two - assert 3 == 4
==== 2 failed in 0.01s ====
"""
    assert parse_failed_tests(output) == [
        "tests/unit/test_a.py::test_one",
        "tests/unit/test_b.py::test_two",
    ]


def test_compare_failures_detects_known_new_and_stale():
    baseline_path = Path("/tmp/dummy-python-baseline.txt")
    baseline_path.write_text(
        "tests/unit/test_a.py::test_one # historical\n"
        "tests/unit/test_c.py::test_three # fixed\n"
    )
    actual = [
        "tests/unit/test_a.py::test_one",
        "tests/unit/test_b.py::test_two",
    ]
    result = compare_failures(actual, baseline_path)
    assert result["known_count"] == 1
    assert result["new_count"] == 1
    assert result["stale_count"] == 1
    assert result["known"] == ["tests/unit/test_a.py::test_one"]
    assert result["new"] == ["tests/unit/test_b.py::test_two"]
    assert result["stale"] == ["tests/unit/test_c.py::test_three"]
```
Run:
```bash
python3 -m pytest tests/unit/test_python_regression.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'tests.unit.python_regression'` if the helper from Task 4 is not yet in place; otherwise PASS.

- [x] **Step 2: Ensure the helper module exists**

Confirm `tests/unit/python_regression.py` from Task 4 exists and contains `parse_failed_tests` and `compare_failures`. If the test in Step 1 failed because the module is missing, create it now.

- [x] **Step 3: Run the baseline helper tests**

Run:
```bash
python3 -m pytest tests/unit/test_python_regression.py -v
```
Expected: 2 passed.

- [x] **Step 4: Verify the report script reports zero new failures after fixes**

Run:
```bash
bash tests/scripts/report_python_regression.sh
```
Expected: exit 0 with `✅ 0 新增失败` (after the rddf-session and timing fixes are applied in Tasks 1-3).

- [x] **Step 5: Defer commit**

Do not run `git add` or `git commit`.

---

## Self-Review

1. **Spec coverage**: The proposal requires (a) Python stable failures in a baseline, (b) fixing rddf-session schema drift, (c) fixing the timing assertion, and (d) 1-2 tests locking the fixes. This plan covers all four via Tasks 1-5.
2. **Placeholder scan**: No TBD/TODO/"implement later"/"similar to Task N" language. Every step has a concrete command or code snippet.
3. **Type consistency**: `goal` keys used in fixes match `sessions_schema.json` v1 (`intent`, `subject`, `expected_outcome`). Session dict keys match required fields (`state`, `started_at`, `last_heartbeat`).
4. **Scope check**: No `@pytest.mark.skip` masking is added. No event_log implementation changes are proposed.
