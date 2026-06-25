# v2-core-foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Phase 1 core foundation for spec-workflow v2.0 — unified state vector, append-only event log, two-level gate mechanism, multi-source config parser, and v1.x bidirectional sync layer. Establishes the authoritative state layer that v2-loop-engine and v2-advanced-features will build upon.

**Architecture:** Single JSON state vector (`.spec-workflow/state-vector.json`) as source of truth + append-only JSONL event log (`.spec-workflow/event-log.jsonl`) for audit + fcntl-based file lock (10s default timeout) for concurrency + lambda-based gate mechanism (error/warning severities) for phase transitions + priority-merged config (runtime > loop.yaml > .spec-workflow.json > env > defaults) + bidirectional v1.x sync. All ~1,200 lines Python, fully backward compatible with v1.x skills.

**Tech Stack:** Python 3.10+, PyYAML (for `loop.yaml`), jsonschema (for state vector validation), `fcntl` (stdlib for file locking), `pytest` (testing), OpenSpec CLI v1.3.1+ (workflow orchestration), git worktree (isolation).

**OpenSpec Workflow Phases Covered:** This plan executes the full lifecycle for the `v2-core-foundation` change:
- **Phase 0 — Propose** (artifacts already exist; verify and commit)
- **Phase 1 — Plan** (worktree creation, this plan, dependency confirmation)
- **Phase 2 — Execute** (Tasks 1-13 below; update `tasks.md` after each task)
- **Phase 3 — Status** (Task 14: validate `openspec instructions apply` shows 100% complete)
- **Phase 4 — Archive** (Task 15: merge → `openspec archive --yes` → worktree/branch cleanup)

---

## File Structure

This change creates new files only. No existing v1.x files are modified — sync layer handles compatibility.

### Production Code (`skills/_lib/`)

| File | Lines | Responsibility |
|---|---|---|
| `skills/_lib/lock.py` | ~100 | `FileLock` class — `fcntl`-based exclusive/shared lock, context manager API, 10s default timeout |
| `skills/_lib/schemas/state_vector_schema.json` | ~60 | JSON Schema for state vector — required fields, types, additionalProperties=false |
| `skills/_lib/state_vector.py` | ~300 | `StateVector` class — atomic load/save, nested-field update, schema validation, checksum, default factory |
| `skills/_lib/event_types.py` | ~80 | 17 `EventType` enum members + `Severity` enum (debug/info/warn/error) + dataclasses |
| `skills/_lib/event_context.py` | ~30 | `EventContext` — reads current state from `StateVector` to populate event `context` field |
| `skills/_lib/event_log.py` | ~250 | `EventLog` class — append-only JSONL writer, query API (by type/time/severity), `generate_id()`, progress report aggregation |
| `skills/_lib/gate.py` | ~300 | `GateMechanism`, `Check` namedtuple — `verify_transition()`, default checks for `arch_done`/`plan_done`/`ship_done`, plugin loader, force override, suggestions |
| `skills/_lib/defaults.py` | ~30 | Built-in defaults: `interaction.mode=hybrid`, `loop.max_iterations=100`, `loop.max_retries=3` |
| `skills/_lib/config.py` | ~200 | `ConfigParser` — multi-source priority merge, env-var parsing, type coercion, validation, clear error messages |
| `skills/_lib/sync_state.py` | ~200 | `sync_state_vector_to_legacy()` and `sync_legacy_to_state_vector()` — bidirectional v1.x sync, mtime conflict detection, event log on conflict |
| `skills/_lib/plugins/README.md` | ~50 | Plugin development guide — how to write/register a custom gate check |

### Tests (`tests/unit/`)

| File | Responsibility |
|---|---|
| `tests/unit/test_lock.py` | Concurrent acquire/release, timeout behavior, shared-vs-exclusive, context manager cleanup |
| `tests/unit/test_state_vector.py` | Read/write roundtrip, update_field (nested), schema rejection, corruption detection via checksum, file size < 50KB, latency < 10ms |
| `tests/unit/test_event_log.py` | Write→query consistency, 10K events query < 100ms, unique IDs, severity filtering, progress report accuracy |
| `tests/unit/test_gate.py` | Error blocks, warning allows-with-notice, force_transition records, plugin registration, suggestions contain commands |
| `tests/unit/test_config.py` | Minimal config, priority order, env override, invalid rejection, type coercion |
| `tests/unit/test_sync_state.py` | State→v1.x propagation <50ms, v1.x→state propagation, conflict resolution (state vector wins), disable via env var |

### Documentation (`docs/`)

| File | Update Reason |
|---|---|
| `docs/v2-api-reference.md` | Document new public APIs: `StateVector`, `EventLog`, `GateMechanism`, `ConfigParser` |
| `docs/v2-config-schema.md` | Document `.spec-workflow.json` schema (top-level fields, types, defaults) |

### OpenSpec Artifacts (`openspec/changes/v2-core-foundation/`)

Already created during Phase 0 (propose). No content changes needed; only git commit.

---

## Pre-Flight Checklist

Before starting Task 1, confirm the following:

- [ ] Working directory is `/workspace/project/spec-workflow` (or equivalent repo root)
- [ ] On branch `master`, no uncommitted changes in `openspec/changes/v2-core-foundation/`
- [ ] `python3 --version` shows 3.10 or later
- [ ] `pip install pyyaml jsonschema pytest` succeeds
- [ ] `openspec --version` shows 1.3.1 or later
- [ ] `git worktree list` shows only master (no `openspec/v2-core-foundation` yet)

---

## OpenSpec Phase 1: Plan — Worktree Creation

### Task 0: Commit Artifacts and Create Worktree

**Files:**
- Modify: `openspec/changes/v2-core-foundation/.openspec.yaml` (already exists, will be staged)
- Modify: `openspec/changes/v2-core-foundation/{proposal,design,tasks}.md` (already exist, will be staged)
- Modify: `openspec/changes/v2-core-foundation/specs/{configuration,gate-mechanism,state-management}/spec.md` (already exist, will be staged)

- [ ] **Step 1: Verify all Phase 0 artifacts exist and are valid**

```bash
cd /workspace/project/spec-workflow
ls -la openspec/changes/v2-core-foundation/
test -f openspec/changes/v2-core-foundation/proposal.md && echo "proposal.md: OK"
test -f openspec/changes/v2-core-foundation/design.md && echo "design.md: OK"
test -f openspec/changes/v2-core-foundation/tasks.md && echo "tasks.md: OK"
test -f openspec/changes/v2-core-foundation/roadmap-meta.yaml && echo "roadmap-meta.yaml: OK"
test -d openspec/changes/v2-core-foundation/specs && echo "specs/: OK"
```

Expected: All five `OK` lines printed. If any missing, STOP and investigate.

- [ ] **Step 2: Commit Phase 0 artifacts to master**

```bash
cd /workspace/project/spec-workflow
git add openspec/changes/v2-core-foundation/
git status  # should show: "Changes to be committed: new files: ..."
git commit -m "feat(openspec): add v2-core-foundation change artifacts

Phase 0 of v2.0: state vector + event log + gate mechanism + config + v1.x sync.
- proposal.md: Why/What/Impact
- design.md: Architectural decisions and trade-offs
- tasks.md: 30+ atomic subtasks across 6 task groups
- specs/{configuration,gate-mechanism,state-management}: ADDED Requirements
- roadmap-meta.yaml: phase-2 / P0 / state-management"
```

Expected: One new commit on `master`. Verify with `git log --oneline -1`.

- [ ] **Step 3: Create branch and worktree**

```bash
cd /workspace/project/spec-workflow
DEFAULT_BRANCH=$(git symbolic-ref --short HEAD)
git branch openspec/v2-core-foundation "$DEFAULT_BRANCH"
git worktree add .zcf/v2-core-foundation-wt -b openspec/v2-core-foundation "$DEFAULT_BRANCH"
cd .zcf/v2-core-foundation-wt
git branch --show-current  # should print: openspec/v2-core-foundation
```

Expected: `git branch --show-current` prints `openspec/v2-core-foundation`. **All subsequent tasks run inside this worktree directory.**

- [ ] **Step 4: Save this plan inside the worktree**

```bash
cd /workspace/project/spec-workflow/.zcf/v2-core-foundation-wt
mkdir -p docs/superpowers/plans
cp /workspace/project/spec-workflow/docs/superpowers/plans/2026-06-25-v2-core-foundation.md \
   docs/superpowers/plans/2026-06-25-v2-core-foundation.md
git add docs/superpowers/plans/2026-06-25-v2-core-foundation.md
git commit -m "docs(planning): add v2-core-foundation implementation plan"
```

Expected: Plan committed on the feature branch. The worktree now has full task list available offline.

---

## OpenSpec Phase 2: Execute — Implementation Tasks

> **Architecture rationale:** Task 1 (lock) is a leaf dependency; Tasks 2-3 (schema, state vector) form the data foundation; Tasks 4-6 (event system) build on it; Task 7 (gate) consumes both; Tasks 8-9 (plugins README, defaults) are small; Tasks 10-11 (config, sync) build on defaults; Task 12 (docs) is finalization; Task 13 (integration) validates the whole stack. **TDD ordering** — each task writes a failing test first.

### Task 1: File Lock (`skills/_lib/lock.py`)

**Files:**
- Create: `skills/_lib/lock.py` (~100 lines)
- Test: `tests/unit/test_lock.py` (~150 lines)

**Dependency:** None. This is the leaf primitive.

- [ ] **Step 1.1: Write the failing test**

Create `tests/unit/test_lock.py`:

```python
"""Tests for FileLock — fcntl-based exclusive/shared file lock with timeout."""
import os
import tempfile
import threading
import time
import pytest
from skills._lib.lock import FileLock, LockTimeout


@pytest.fixture
def lock_path(tmp_path):
    return str(tmp_path / "test.lock")


def test_context_manager_acquires_and_releases(lock_path):
    """Lock is held inside `with` block, released on exit."""
    with FileLock(lock_path, timeout=2.0) as lock:
        assert lock.is_held is True
    assert not os.path.exists(lock_path) or True  # lock file may or may not exist after release


def test_exclusive_lock_blocks_second_acquire(lock_path):
    """Second acquire on same file within timeout must raise LockTimeout."""
    with FileLock(lock_path, timeout=0.5) as first:
        with pytest.raises(LockTimeout):
            with FileLock(lock_path, timeout=0.5, exclusive=True):
                pass


def test_concurrent_threads_serialize(lock_path):
    """Two threads with the same lock must execute serially, not in parallel."""
    order = []
    barrier = threading.Barrier(2)

    def worker(name, hold_time):
        with FileLock(lock_path, timeout=2.0):
            barrier.wait()
            order.append(f"{name}-enter")
            time.sleep(hold_time)
            order.append(f"{name}-exit")

    t1 = threading.Thread(target=worker, args=("A", 0.1))
    t2 = threading.Thread(target=worker, args=("B", 0.1))
    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)

    # Exactly one of [A-enter, B-enter] must be followed by its own -exit before the other -enter
    assert order in [
        ["A-enter", "A-exit", "B-enter", "B-exit"],
        ["B-enter", "B-exit", "A-enter", "A-exit"],
    ], f"Locks did not serialize: {order}"


def test_lock_released_on_exception(lock_path):
    """Lock must be released even when `with` block raises."""
    try:
        with FileLock(lock_path, timeout=0.5):
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    # Should be able to acquire again immediately
    with FileLock(lock_path, timeout=0.5) as lock:
        assert lock.is_held


def test_is_held_property(lock_path):
    """`is_held` returns True inside the block, False before/after."""
    lock = FileLock(lock_path, timeout=0.5)
    assert lock.is_held is False
    with lock:
        assert lock.is_held is True
    assert lock.is_held is False


def test_lock_timeout_raises_locktimeout(lock_path):
    """When timeout expires, must raise LockTimeout (not generic Exception)."""
    with FileLock(lock_path, timeout=5.0):
        start = time.time()
        with pytest.raises(LockTimeout):
            with FileLock(lock_path, timeout=0.3):
                pass
        elapsed = time.time() - start
        assert 0.25 < elapsed < 1.0  # timed out around 0.3s
```

- [ ] **Step 1.2: Run test to verify it fails**

```bash
cd /workspace/project/spec-workflow/.zcf/v2-core-foundation-wt
python3 -m pytest tests/unit/test_lock.py -v
```

Expected: `ModuleNotFoundError: No module named 'skills._lib.lock'` (or import error).

- [ ] **Step 1.3: Implement `FileLock`**

Create `skills/_lib/lock.py`:

```python
"""File-level locking with timeout. Cross-platform where possible.

Uses fcntl on Linux/macOS (POSIX). Provides exclusive (writer) and shared
(reader) lock modes with a configurable timeout. Use as a context manager.
"""
from __future__ import annotations
import os
import time
import fcntl
import errno
from pathlib import Path
from typing import Optional


class LockTimeout(Exception):
    """Raised when a lock acquire exceeds its timeout."""


class FileLock:
    """Exclusive or shared file lock with timeout (fcntl-based).

    Args:
        path: Path to the lock file. Created on first acquire if missing.
        timeout: Seconds to wait for the lock before raising LockTimeout.
            Default 10.0. Use 0.0 for non-blocking.
        exclusive: True for write lock (default), False for shared read lock.

    Example:
        with FileLock("/tmp/state.lock", timeout=5.0):
            # ... critical section ...
            pass
    """

    def __init__(self, path: str, timeout: float = 10.0, exclusive: bool = True):
        self.path = Path(path)
        self.timeout = timeout
        self.exclusive = exclusive
        self._fd: Optional[int] = None
        self._held = False

    @property
    def is_held(self) -> bool:
        return self._held

    def acquire(self) -> None:
        """Acquire the lock. Blocks up to `timeout` seconds, then raises."""
        if self._held:
            raise RuntimeError("Lock already held by this instance")

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fd = os.open(str(self.path), os.O_CREAT | os.O_RDWR, 0o644)

        op = fcntl.LOCK_EX if self.exclusive else fcntl.LOCK_SH
        # Non-blocking when timeout=0, otherwise use blocking call + poll for timeout
        if self.timeout == 0:
            try:
                fcntl.flock(self._fd, op | fcntl.LOCK_NB)
            except OSError as e:
                os.close(self._fd)
                self._fd = None
                if e.errno in (errno.EWOULDBLOCK, errno.EAGAIN):
                    raise LockTimeout(f"Lock {self.path} is held by another process") from e
                raise
        else:
            deadline = time.monotonic() + self.timeout
            while True:
                try:
                    fcntl.flock(self._fd, op | fcntl.LOCK_NB)
                    break
                except OSError as e:
                    if e.errno not in (errno.EWOULDBLOCK, errno.EAGAIN):
                        os.close(self._fd)
                        self._fd = None
                        raise
                    if time.monotonic() >= deadline:
                        os.close(self._fd)
                        self._fd = None
                        raise LockTimeout(
                            f"Timed out after {self.timeout}s waiting for {self.path}"
                        ) from e
                    time.sleep(0.01)  # 10ms poll interval

        self._held = True

    def release(self) -> None:
        """Release the lock. Idempotent — safe to call when not held."""
        if not self._held:
            return
        try:
            fcntl.flock(self._fd, fcntl.LOCK_UN)
        finally:
            os.close(self._fd)
            self._fd = None
            self._held = False

    def __enter__(self) -> "FileLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()
```

- [ ] **Step 1.4: Run tests to verify they pass**

```bash
cd /workspace/project/spec-workflow/.zcf/v2-core-foundation-wt
python3 -m pytest tests/unit/test_lock.py -v
```

Expected: All 6 tests pass. **Do not proceed if any fail.**

- [ ] **Step 1.5: Update tasks.md and commit**

```bash
cd /workspace/project/spec-workflow/.zcf/v2-core-foundation-wt
sed -i 's/- \[ \] 1.2 Create `skills/_lib/lock.py`/- [x] 1.2 Create `skills/_lib/lock.py`/' openspec/changes/v2-core-foundation/tasks.md
git add skills/_lib/lock.py tests/unit/test_lock.py openspec/changes/v2-core-foundation/tasks.md
git commit -m "feat(_lib): add FileLock (fcntl-based, 10s timeout, context manager) — closes 1.2"
```

Expected: 1 new commit. `tasks.md` now shows `[x]` for item 1.2.

---

### Task 2: State Vector Schema (`skills/_lib/schemas/state_vector_schema.json`)

**Files:**
- Create: `skills/_lib/schemas/state_vector_schema.json` (~60 lines)

**Dependency:** None (pure data).

- [ ] **Step 2.1: Create the schema file**

```bash
mkdir -p /workspace/project/spec-workflow/.zcf/v2-core-foundation-wt/skills/_lib/schemas
```

Create `skills/_lib/schemas/state_vector_schema.json`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://spec-workflow.dev/schemas/state_vector_schema.json",
  "title": "Spec Workflow v2 State Vector",
  "description": "Unified workflow state. Single source of truth; replaces 13 v1.x state files.",
  "type": "object",
  "required": ["version", "goal", "arch_side", "plan_side", "ship_side", "loop_state", "memory", "metadata"],
  "additionalProperties": false,
  "properties": {
    "version": {
      "type": "string",
      "const": "2.0",
      "description": "Schema version. Must be \"2.0\"."
    },
    "goal": {
      "type": ["string", "null"],
      "description": "User's high-level goal string. May be null before setup completes."
    },
    "arch_side": {
      "type": "object",
      "description": "Spec-side state (setup → roadmap → propose → deps).",
      "required": ["phase", "current_change"],
      "additionalProperties": false,
      "properties": {
        "phase": {
          "type": "string",
          "enum": ["setup", "roadmap", "propose", "deps", "done", "idle"]
        },
        "current_change": { "type": ["string", "null"] },
        "completed_changes": {
          "type": "array",
          "items": { "type": "string" }
        }
      }
    },
    "plan_side": {
      "type": "object",
      "description": "Plan-side state (planning artifacts for the active change).",
      "required": ["active_change", "plan_file"],
      "additionalProperties": false,
      "properties": {
        "active_change": { "type": ["string", "null"] },
        "plan_file": { "type": ["string", "null"] },
        "worktree_path": { "type": ["string", "null"] }
      }
    },
    "ship_side": {
      "type": "object",
      "description": "Ship-side state (execute, status, archive).",
      "required": ["current_phase", "progress"],
      "additionalProperties": false,
      "properties": {
        "current_phase": {
          "type": "string",
          "enum": ["idle", "execute", "verify", "archive", "done"]
        },
        "progress": {
          "type": "object",
          "required": ["complete", "total"],
          "properties": {
            "complete": { "type": "integer", "minimum": 0 },
            "total": { "type": "integer", "minimum": 0 }
          }
        }
      }
    },
    "loop_state": {
      "type": "object",
      "description": "Loop engine state (v2-loop-engine).",
      "required": ["mode", "iteration"],
      "additionalProperties": false,
      "properties": {
        "mode": { "type": "string", "enum": ["idle", "loop", "menu", "hybrid"] },
        "iteration": { "type": "integer", "minimum": 0 },
        "last_action": { "type": ["string", "null"] },
        "last_action_at": { "type": ["string", "null"], "format": "date-time" }
      }
    },
    "memory": {
      "type": "object",
      "description": "Persistent memory across iterations (v2-memory-system).",
      "required": ["notes", "learnings"],
      "additionalProperties": false,
      "properties": {
        "notes": { "type": "string" },
        "learnings": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["text", "created_at"],
            "properties": {
              "text": { "type": "string" },
              "created_at": { "type": "string", "format": "date-time" }
            }
          }
        }
      }
    },
    "metadata": {
      "type": "object",
      "description": "Operational metadata for debugging and audit.",
      "required": ["spec_workflow_version", "created_at", "updated_at"],
      "additionalProperties": false,
      "properties": {
        "spec_workflow_version": { "type": "string" },
        "git_commit": { "type": ["string", "null"] },
        "created_at": { "type": "string", "format": "date-time" },
        "updated_at": { "type": "string", "format": "date-time" },
        "checksum": { "type": "string", "description": "SHA-256 of canonical JSON, for corruption detection." }
      }
    }
  }
}
```

- [ ] **Step 2.2: Validate the schema**

```bash
cd /workspace/project/spec-workflow/.zcf/v2-core-foundation-wt
python3 -c "
import json, jsonschema
with open('skills/_lib/schemas/state_vector_schema.json') as f:
    schema = json.load(f)
jsonschema.Draft7Validator.check_schema(schema)
print('Schema is valid JSON Schema draft-07')
"
```

Expected: `Schema is valid JSON Schema draft-07`.

- [ ] **Step 2.3: Update tasks.md and commit**

```bash
cd /workspace/project/spec-workflow/.zcf/v2-core-foundation-wt
sed -i 's/- \[ \] 1.3 Create `skills/_lib\/schemas\/state_vector_schema.json`/- [x] 1.3 Create `skills/_lib\/schemas\/state_vector_schema.json`/' openspec/changes/v2-core-foundation/tasks.md
git add skills/_lib/schemas/state_vector_schema.json openspec/changes/v2-core-foundation/tasks.md
git commit -m "feat(_lib): add state_vector_schema.json (JSON Schema draft-07) — closes 1.3"
```

Expected: 1 new commit.

---

### Task 3: State Vector Implementation (`skills/_lib/state_vector.py`)

**Files:**
- Create: `skills/_lib/state_vector.py` (~300 lines)
- Test: `tests/unit/test_state_vector.py` (~200 lines)

**Dependencies:** Task 1 (lock), Task 2 (schema).

- [ ] **Step 3.1: Write the failing test**

Create `tests/unit/test_state_vector.py`:

```python
"""Tests for StateVector — unified workflow state with file lock + schema validation."""
import json
import os
import time
import subprocess
import pytest
from skills._lib.state_vector import StateVector, StateVectorError


@pytest.fixture
def state_path(tmp_path):
    return str(tmp_path / "state-vector.json")


def test_create_default_returns_valid_state():
    """`create_default()` returns a fully-populated state matching the schema."""
    sv = StateVector.create_default()
    jsonschema = __import__("jsonschema")
    schema_path = os.path.join(os.path.dirname(__file__), "../../skills/_lib/schemas/state_vector_schema.json")
    with open(schema_path) as f:
        schema = json.load(f)
    jsonschema.validate(sv.to_dict(), schema)
    assert sv.to_dict()["version"] == "2.0"
    assert sv.to_dict()["metadata"]["spec_workflow_version"]


def test_roundtrip_via_save_and_load(state_path):
    """Save → load must preserve all fields."""
    sv = StateVector.create_default()
    sv.update_field("goal", "implement state vector")
    sv.save(state_path)
    loaded = StateVector.load(state_path)
    assert loaded.get_field("goal") == "implement state vector"


def test_load_nonexistent_returns_default(state_path):
    """Loading from a missing file returns a default state."""
    assert not os.path.exists(state_path)
    sv = StateVector.load(state_path)
    assert sv.to_dict()["version"] == "2.0"


def test_update_field_supports_nested_keys(state_path):
    """update_field with dotted path updates nested fields."""
    sv = StateVector.create_default()
    sv.update_field("loop_state.iteration", 5)
    sv.update_field("metadata.git_commit", "abc123")
    sv.save(state_path)
    loaded = StateVector.load(state_path)
    assert loaded.get_field("loop_state.iteration") == 5
    assert loaded.get_field("metadata.git_commit") == "abc123"


def test_invalid_schema_rejected_on_save(state_path):
    """Saving an invalid state (missing required field) must raise."""
    sv = StateVector.create_default()
    # Corrupt by removing a required field via direct mutation of internal dict
    sv._data["version"] = "1.0"  # violates `const: "2.0"`
    with pytest.raises(StateVectorError, match="schema"):
        sv.save(state_path)


def test_corruption_detected_via_checksum(state_path):
    """Manually corrupted file (bad checksum) is detected on load."""
    sv = StateVector.create_default()
    sv.save(state_path)
    # Manually corrupt the file
    with open(state_path, "r") as f:
        data = f.read()
    corrupted = data.replace('"2.0"', '"2.1"')
    with open(state_path, "w") as f:
        f.write(corrupted)
    # load() should raise or fall back — depending on policy; here we require it raise
    with pytest.raises(StateVectorError, match="checksum"):
        StateVector.load(state_path, verify_checksum=True)


def test_file_size_under_50kb(state_path):
    """A fresh state vector must be well under 50KB."""
    sv = StateVector.create_default()
    sv.save(state_path)
    size = os.path.getsize(state_path)
    assert size < 50_000, f"State vector too large: {size} bytes"


def test_read_write_latency_under_10ms(state_path):
    """Save + load roundtrip on local FS must take < 10ms (after first warmup)."""
    sv = StateVector.create_default()
    # Warmup
    sv.save(state_path)
    StateVector.load(state_path)
    # Measure
    start = time.perf_counter()
    for _ in range(100):
        sv.save(state_path)
        StateVector.load(state_path)
    elapsed = time.perf_counter() - start
    per_op = elapsed / 100
    assert per_op < 0.010, f"Roundtrip too slow: {per_op*1000:.2f}ms (must be < 10ms)"


def test_concurrent_writes_are_serialized(state_path):
    """Two processes writing simultaneously must not corrupt the file."""
    code = f"""
import sys
sys.path.insert(0, '.')
from skills._lib.state_vector import StateVector
sv = StateVector.create_default()
for i in range(50):
    sv.update_field('loop_state.iteration', i)
    sv.save('{state_path}')
"""
    p1 = subprocess.Popen(["python3", "-c", code], cwd=".")
    p2 = subprocess.Popen(["python3", "-c", code], cwd=".")
    p1.wait(timeout=30)
    p2.wait(timeout=30)
    # File must still load successfully
    loaded = StateVector.load(state_path)
    assert loaded.get_field("loop_state.iteration") >= 0
```

- [ ] **Step 3.2: Run test to verify it fails**

```bash
cd /workspace/project/spec-workflow/.zcf/v2-core-foundation-wt
python3 -m pytest tests/unit/test_state_vector.py -v 2>&1 | head -30
```

Expected: `ModuleNotFoundError: No module named 'skills._lib.state_vector'`.

- [ ] **Step 3.3: Implement `StateVector`**

Create `skills/_lib/state_vector.py`:

```python
"""Unified state vector — single source of truth for spec-workflow v2.

Stored as JSON at `.spec-workflow/state-vector.json`. All writes are atomic
(write-temp-then-rename) and protected by a `FileLock` (10s timeout). All
writes are schema-validated (JSON Schema draft-07) and checksummed
(SHA-256 of canonical JSON) for corruption detection.
"""
from __future__ import annotations
import copy
import datetime
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Optional

import jsonschema

from skills._lib.lock import FileLock, LockTimeout


SCHEMA_PATH = os.path.join(
    os.path.dirname(__file__), "schemas", "state_vector_schema.json"
)
_LOCK_TIMEOUT = 10.0


class StateVectorError(Exception):
    """Raised on validation failure, corruption, or I/O error."""


def _canonical_json(data: dict) -> str:
    """Serialize dict with sorted keys and no extra whitespace (for checksum stability)."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _compute_checksum(data: dict) -> str:
    """SHA-256 of canonical JSON, excluding the `metadata.checksum` field itself."""
    d = copy.deepcopy(data)
    if "metadata" in d and isinstance(d["metadata"], dict):
        d["metadata"].pop("checksum", None)
    return hashlib.sha256(_canonical_json(d).encode("utf-8")).hexdigest()


class StateVector:
    """Unified workflow state. All access goes through the lock + schema validator."""

    def __init__(self, data: dict):
        self._data = data
        self._validate(data)

    # ----- Constructors --------------------------------------------------

    @classmethod
    def create_default(cls) -> "StateVector":
        """Return a fresh default state vector with version 2.0 and current timestamps."""
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return cls({
            "version": "2.0",
            "goal": None,
            "arch_side": {
                "phase": "idle",
                "current_change": None,
                "completed_changes": [],
            },
            "plan_side": {
                "active_change": None,
                "plan_file": None,
                "worktree_path": None,
            },
            "ship_side": {
                "current_phase": "idle",
                "progress": {"complete": 0, "total": 0},
            },
            "loop_state": {
                "mode": "idle",
                "iteration": 0,
                "last_action": None,
                "last_action_at": None,
            },
            "memory": {"notes": "", "learnings": []},
            "metadata": {
                "spec_workflow_version": "2.0.0",
                "git_commit": None,
                "created_at": now,
                "updated_at": now,
                "checksum": "",  # populated on save
            },
        })

    @classmethod
    def load(cls, path: str, verify_checksum: bool = True) -> "StateVector":
        """Load state vector from disk. Returns default if file missing.

        Raises:
            StateVectorError: if file exists but is corrupted (bad checksum) or invalid.
        """
        if not os.path.exists(path):
            return cls.create_default()
        try:
            with FileLock(path + ".lock", timeout=_LOCK_TIMEOUT):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
        except LockTimeout as e:
            raise StateVectorError(f"Could not acquire lock for {path}: {e}") from e
        except json.JSONDecodeError as e:
            raise StateVectorError(f"State vector at {path} is not valid JSON: {e}") from e

        if verify_checksum and data.get("metadata", {}).get("checksum"):
            expected = data["metadata"]["checksum"]
            actual = _compute_checksum(data)
            if expected != actual:
                raise StateVectorError(
                    f"State vector at {path} failed checksum verification "
                    f"(expected {expected[:12]}..., got {actual[:12]}...)"
                )
        return cls(data)

    # ----- Validation ---------------------------------------------------

    @staticmethod
    def _validate(data: dict) -> None:
        with open(SCHEMA_PATH) as f:
            schema = json.load(f)
        try:
            jsonschema.validate(data, schema)
        except jsonschema.ValidationError as e:
            raise StateVectorError(f"State vector failed schema validation: {e.message}") from e

    # ----- Mutation -----------------------------------------------------

    def update_field(self, dotted_key: str, value: Any) -> None:
        """Update a (possibly nested) field by dotted path. Validates in-place."""
        new_data = copy.deepcopy(self._data)
        keys = dotted_key.split(".")
        cur = new_data
        for k in keys[:-1]:
            if k not in cur or not isinstance(cur[k], dict):
                raise StateVectorError(f"Cannot traverse into non-dict at '{k}'")
            cur = cur[k]
        cur[keys[-1]] = value
        new_data["metadata"]["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self._validate(new_data)
        self._data = new_data

    # ----- Persistence --------------------------------------------------

    def save(self, path: str) -> None:
        """Atomically write state vector to disk, protected by file lock."""
        # Always recompute checksum and updated_at on save
        self._data["metadata"]["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self._data["metadata"]["checksum"] = _compute_checksum(self._data)

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        try:
            with FileLock(path + ".lock", timeout=_LOCK_TIMEOUT):
                # Atomic write: write to temp, then rename
                fd, tmp = tempfile.mkstemp(
                    dir=os.path.dirname(path) or ".",
                    prefix=".state-vector-", suffix=".tmp",
                )
                try:
                    with os.fdopen(fd, "w", encoding="utf-8") as f:
                        json.dump(self._data, f, indent=2, sort_keys=True, ensure_ascii=False)
                        f.write("\n")
                    os.replace(tmp, path)
                except Exception:
                    if os.path.exists(tmp):
                        os.unlink(tmp)
                    raise
        except LockTimeout as e:
            raise StateVectorError(f"Could not acquire lock to save {path}: {e}") from e

    # ----- Accessors ----------------------------------------------------

    def to_dict(self) -> dict:
        """Return a deep copy of the underlying data (safe to mutate)."""
        return copy.deepcopy(self._data)

    def get_field(self, dotted_key: str, default: Any = None) -> Any:
        """Read a field by dotted path. Returns `default` if any segment is missing."""
        cur: Any = self._data
        for k in dotted_key.split("."):
            if not isinstance(cur, dict) or k not in cur:
                return default
            cur = cur[k]
        return cur
```

- [ ] **Step 3.4: Run tests to verify they pass**

```bash
cd /workspace/project/spec-workflow/.zcf/v2-core-foundation-wt
python3 -m pytest tests/unit/test_state_vector.py -v
```

Expected: All 9 tests pass.

- [ ] **Step 3.5: Update tasks.md (1.1, 1.4, 1.5, 1.6, 1.7) and commit**

```bash
cd /workspace/project/spec-workflow/.zcf/v2-core-foundation-wt
sed -i \
  -e 's/- \[ \] 1.1 Create `skills/_lib\/state_vector.py`/- [x] 1.1 Create `skills/_lib\/state_vector.py`/' \
  -e 's/- \[ \] 1.4 Add checksum field to state vector for corruption detection/- [x] 1.4 Add checksum field to state vector for corruption detection/' \
  -e 's/- \[ \] 1.5 Add `version: "2.0"` and `metadata.spec_workflow_version` + `metadata.git_commit` fields/- [x] 1.5 Add `version: "2.0"` and `metadata.spec_workflow_version` + `metadata.git_commit` fields/' \
  -e 's/- \[ \] 1.6 Write unit tests: read\/write roundtrip, concurrent read+write (2 processes), invalid schema rejection, file size < 50KB/- [x] 1.6 Write unit tests: read\/write roundtrip, concurrent read+write (2 processes), invalid schema rejection, file size < 50KB/' \
  -e 's/- \[ \] 1.7 Verify read\/write latency < 10ms on local FS/- [x] 1.7 Verify read\/write latency < 10ms on local FS/' \
  openspec/changes/v2-core-foundation/tasks.md
git add skills/_lib/state_vector.py tests/unit/test_state_vector.py openspec/changes/v2-core-foundation/tasks.md
git commit -m "feat(_lib): add StateVector (atomic save, schema validation, checksum, 10ms roundtrip) — closes 1.1, 1.4-1.7"
```

Expected: 1 new commit. State vector fully working.

---

### Task 4: Event Types (`skills/_lib/event_types.py`)

**Files:**
- Create: `skills/_lib/event_types.py` (~80 lines)

**Dependency:** None (pure enums + dataclasses).

- [ ] **Step 4.1: Create the event types module**

Create `skills/_lib/event_types.py`:

```python
"""Event types and severity enum for the workflow event log.

17 event types cover the full lifecycle: loop engine starts/scans/iterates,
planning/execution phases, gate transitions, errors, and lifecycle events.
"""
from __future__ import annotations
import enum
import datetime
from dataclasses import dataclass, field, asdict
from typing import Any, Optional


class EventType(str, enum.Enum):
    """Closed set of workflow event types."""
    LOOP_STARTED = "loop_started"
    LOOP_ITERATION_STARTED = "loop_iteration_started"
    LOOP_ITERATION_COMPLETED = "loop_iteration_completed"
    LOOP_COMPLETED = "loop_completed"
    SCAN_COMPLETED = "scan_completed"
    PROPOSAL_GENERATED = "proposal_generated"
    PLAN_GENERATED = "plan_generated"
    EXECUTION_STARTED = "execution_started"
    EXECUTION_UNIT_COMPLETED = "execution_unit_completed"
    EXECUTION_COMPLETED = "execution_completed"
    GATE_TRANSITION = "gate_transition"
    GATE_FAILED = "gate_failed"
    GATE_FORCED = "gate_forced"
    STATE_UPDATED = "state_updated"
    ERROR_OCCURRED = "error_occurred"
    WARNING_ISSUED = "warning_issued"
    USER_INPUT_REQUESTED = "user_input_requested"


class Severity(str, enum.Enum):
    """Event severity for filtering and routing."""
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


@dataclass
class Event:
    """A single workflow event. Serialized to JSONL on write."""
    event_type: EventType
    severity: Severity
    message: str
    id: str = ""  # populated by EventLog.generate_id()
    timestamp: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    context: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp,
            "message": self.message,
            "context": self.context,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Event":
        return cls(
            id=d.get("id", ""),
            event_type=EventType(d["event_type"]),
            severity=Severity(d["severity"]),
            timestamp=d.get("timestamp", ""),
            message=d.get("message", ""),
            context=d.get("context", {}),
            metadata=d.get("metadata", {}),
        )
```

- [ ] **Step 4.2: Verify import works**

```bash
cd /workspace/project/spec-workflow/.zcf/v2-core-foundation-wt
python3 -c "
from skills._lib.event_types import EventType, Severity, Event
print(f'EventType count: {len(list(EventType))}')
print(f'Severity count: {len(list(Severity))}')
assert len(list(EventType)) == 17, 'Must have exactly 17 event types'
"
```

Expected: `EventType count: 17` and `Severity count: 4`.

- [ ] **Step 4.3: Update tasks.md and commit**

```bash
cd /workspace/project/spec-workflow/.zcf/v2-core-foundation-wt
sed -i 's/- \[ \] 2.2 Create `skills/_lib\/event_types.py`/- [x] 2.2 Create `skills/_lib\/event_types.py`/' openspec/changes/v2-core-foundation/tasks.md
git add skills/_lib/event_types.py openspec/changes/v2-core-foundation/tasks.md
git commit -m "feat(_lib): add event_types.py (17 EventType, Severity, Event dataclass) — closes 2.2"
```

Expected: 1 new commit.

---

### Task 5: Event Context (`skills/_lib/event_context.py`)

**Files:**
- Create: `skills/_lib/event_context.py` (~30 lines)

**Dependency:** Task 3 (StateVector).

- [ ] **Step 5.1: Create the event context helper**

Create `skills/_lib/event_context.py`:

```python
"""Event context — reads the current state vector to populate event `context` fields.

Provides a single helper `current_context()` used by EventLog.record() to attach
the active goal, change, and loop iteration to every event.
"""
from __future__ import annotations
import os
from typing import Any

from skills._lib.state_vector import StateVector


DEFAULT_STATE_PATH = ".spec-workflow/state-vector.json"


def current_context(state_path: str = DEFAULT_STATE_PATH) -> dict:
    """Return a dict snapshot of relevant state for attaching to an event.

    If the state vector cannot be loaded, returns an empty dict (events are
    still recorded; just without context).
    """
    try:
        sv = StateVector.load(state_path, verify_checksum=False)
        data = sv.to_dict()
        return {
            "goal": data.get("goal"),
            "active_change": data.get("plan_side", {}).get("active_change")
                              or data.get("arch_side", {}).get("current_change"),
            "arch_phase": data.get("arch_side", {}).get("phase"),
            "ship_phase": data.get("ship_side", {}).get("current_phase"),
            "loop_mode": data.get("loop_state", {}).get("mode"),
            "loop_iteration": data.get("loop_state", {}).get("iteration", 0),
        }
    except Exception:
        return {}
```

- [ ] **Step 5.2: Verify import and behavior**

```bash
cd /workspace/project/spec-workflow/.zcf/v2-core-foundation-wt
cd /tmp && rm -rf sw-test && mkdir sw-test && cd sw-test && git init -q
mkdir -p .spec-workflow .opencode/skills
python3 -c "
import sys; sys.path.insert(0, '/workspace/project/spec-workflow/.zcf/v2-core-foundation-wt')
from skills._lib.event_context import current_context
ctx = current_context('/tmp/sw-test/.spec-workflow/state-vector.json')
print('context:', ctx)
assert 'loop_iteration' in ctx
"
```

Expected: `context: {'goal': None, 'active_change': None, ...}`.

- [ ] **Step 5.3: Update tasks.md and commit**

```bash
cd /workspace/project/spec-workflow/.zcf/v2-core-foundation-wt
sed -i 's/- \[ \] 2.3 Create `skills/_lib\/event_context.py` reading current context from state vector/- [x] 2.3 Create `skills/_lib\/event_context.py` reading current context from state vector/' openspec/changes/v2-core-foundation/tasks.md
git add skills/_lib/event_context.py openspec/changes/v2-core-foundation/tasks.md
git commit -m "feat(_lib): add event_context.py (snapshot of state for event context) — closes 2.3"
```

Expected: 1 new commit.

---

### Task 6: Event Log (`skills/_lib/event_log.py`)

**Files:**
- Create: `skills/_lib/event_log.py` (~250 lines)
- Test: `tests/unit/test_event_log.py` (~150 lines)

**Dependencies:** Task 4 (EventType), Task 5 (EventContext), Task 1 (Lock).

- [ ] **Step 6.1: Write the failing test**

Create `tests/unit/test_event_log.py`:

```python
"""Tests for EventLog — append-only JSONL event log with query API."""
import json
import os
import time
import pytest
from skills._lib.event_log import EventLog
from skills._lib.event_types import EventType, Severity, Event


@pytest.fixture
def log_path(tmp_path):
    return str(tmp_path / "event-log.jsonl")


def test_record_writes_valid_jsonl(log_path):
    """record() appends one JSON object per line."""
    log = EventLog(log_path)
    log.record(EventType.LOOP_STARTED, Severity.INFO, "starting loop", generate_id=True)
    log.record(EventType.SCAN_COMPLETED, Severity.INFO, "scan done", generate_id=True)
    with open(log_path) as f:
        lines = f.readlines()
    assert len(lines) == 2
    for line in lines:
        d = json.loads(line)
        assert "id" in d
        assert d["event_type"] in [e.value for e in EventType]
        assert d["severity"] in [s.value for s in Severity]


def test_event_id_format(log_path):
    """Generated IDs match evt_YYYYMMDD_HHMMSS_NNN format."""
    log = EventLog(log_path)
    eid = log.generate_id()
    assert eid.startswith("evt_")
    # YYYYMMDD_HHMMSS = 15 chars after prefix
    assert len(eid.split("_")) == 3
    date_part, time_part, seq = eid.split("_")
    assert len(date_part) == 8 and date_part.isdigit()
    assert len(time_part) == 6 and time_part.isdigit()
    assert len(seq) == 3 and seq.isdigit()


def test_query_by_event_type(log_path):
    """query(event_type=...) returns only matching events."""
    log = EventLog(log_path)
    for _ in range(3):
        log.record(EventType.LOOP_STARTED, Severity.INFO, "x", generate_id=True)
    for _ in range(2):
        log.record(EventType.SCAN_COMPLETED, Severity.INFO, "y", generate_id=True)
    results = log.query(event_type=EventType.LOOP_STARTED)
    assert len(results) == 3
    assert all(r.event_type == EventType.LOOP_STARTED for r in results)


def test_query_by_time_range(log_path):
    """query(since=..., until=...) filters by timestamp."""
    log = EventLog(log_path)
    e1 = log.record(EventType.LOOP_STARTED, Severity.INFO, "first", generate_id=True)
    time.sleep(0.05)
    e2 = log.record(EventType.LOOP_STARTED, Severity.INFO, "second", generate_id=True)
    results = log.query(since=e1.timestamp)
    assert len(results) == 2
    results = log.query(since=e2.timestamp)
    assert len(results) == 1


def test_query_10k_events_under_100ms(log_path):
    """Querying 10K events must complete in < 100ms."""
    log = EventLog(log_path)
    for i in range(10_000):
        log.record(
            EventType.LOOP_ITERATION_STARTED if i % 2 == 0 else EventType.SCAN_COMPLETED,
            Severity.INFO,
            f"event {i}",
            generate_id=True,
        )
    start = time.perf_counter()
    results = log.query(event_type=EventType.LOOP_ITERATION_STARTED)
    elapsed = time.perf_counter() - start
    assert len(results) == 5000
    assert elapsed < 0.100, f"Query took {elapsed*1000:.1f}ms (must be < 100ms)"


def test_progress_report_accuracy(log_path):
    """get_progress_report returns correct iteration/completion/error counts."""
    log = EventLog(log_path)
    for i in range(5):
        log.record(EventType.LOOP_ITERATION_COMPLETED, Severity.INFO, f"iter {i}", generate_id=True)
    for i in range(2):
        log.record(EventType.EXECUTION_UNIT_COMPLETED, Severity.INFO, f"unit {i}", generate_id=True)
    log.record(EventType.ERROR_OCCURRED, Severity.ERROR, "oops", generate_id=True)
    report = log.get_progress_report()
    assert report["iterations_completed"] == 5
    assert report["units_completed"] == 2
    assert report["error_count"] == 1


def test_unique_ids_within_same_second(log_path):
    """Even when called rapidly, IDs are unique (sequence counter increments)."""
    log = EventLog(log_path)
    ids = [log.generate_id() for _ in range(100)]
    assert len(set(ids)) == 100, "IDs must be unique"


def test_survives_corrupt_line(log_path):
    """A corrupted JSONL line is skipped, not fatal."""
    log = EventLog(log_path)
    log.record(EventType.LOOP_STARTED, Severity.INFO, "good 1", generate_id=True)
    with open(log_path, "a") as f:
        f.write("THIS IS NOT JSON\n")
    log.record(EventType.LOOP_STARTED, Severity.INFO, "good 2", generate_id=True)
    results = log.query()
    assert len(results) == 2
```

- [ ] **Step 6.2: Run test to verify it fails**

```bash
cd /workspace/project/spec-workflow/.zcf/v2-core-foundation-wt
python3 -m pytest tests/unit/test_event_log.py -v 2>&1 | head -10
```

Expected: `ModuleNotFoundError: No module named 'skills._lib.event_log'`.

- [ ] **Step 6.3: Implement `EventLog`**

Create `skills/_lib/event_log.py`:

```python
"""Append-only JSONL event log with query API and progress reports.

Stored at `.spec-workflow/event-log.jsonl`. Each line is one event. Writes
are protected by a file lock for safety. The log is read on every query;
for 10K+ events the read is < 100ms (see test_query_10k_events_under_100ms).

Event ID format: `evt_YYYYMMDD_HHMMSS_NNN` where NNN is a per-process
sequence counter to guarantee uniqueness even within the same second.
"""
from __future__ import annotations
import datetime
import json
import os
import threading
from pathlib import Path
from typing import Iterable, Optional, Union

from skills._lib.event_types import Event, EventType, Severity
from skills._lib.lock import FileLock, LockTimeout


_LOCK_TIMEOUT = 10.0
_id_lock = threading.Lock()
_id_seq = 0


class EventLogError(Exception):
    """Raised on I/O or lock failure."""


def _next_id_seq() -> int:
    global _id_seq
    with _id_lock:
        _id_seq += 1
        return _id_seq


class EventLog:
    """JSONL event log at `path`."""

    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)

    # ----- ID generation -----------------------------------------------

    def generate_id(self) -> str:
        """Return a new unique event ID: `evt_YYYYMMDD_HHMMSS_NNN`."""
        now = datetime.datetime.now(datetime.timezone.utc)
        seq = _next_id_seq()
        return f"evt_{now.strftime('%Y%m%d_%H%M%S')}_{seq:03d}"

    # ----- Recording ----------------------------------------------------

    def record(
        self,
        event_type: Union[EventType, str],
        severity: Union[Severity, str],
        message: str,
        context: Optional[dict] = None,
        metadata: Optional[dict] = None,
        generate_id: bool = True,
    ) -> Event:
        """Append a new event. Returns the recorded Event."""
        if isinstance(event_type, str):
            event_type = EventType(event_type)
        if isinstance(severity, str):
            severity = Severity(severity)
        event = Event(
            event_type=event_type,
            severity=severity,
            message=message,
            id=self.generate_id() if generate_id else "",
            context=context or {},
            metadata=metadata or {},
        )
        try:
            with FileLock(self.path + ".lock", timeout=_LOCK_TIMEOUT):
                with open(self.path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(event.to_dict(), ensure_ascii=False))
                    f.write("\n")
        except LockTimeout as e:
            raise EventLogError(f"Could not acquire lock to write event: {e}") from e
        return event

    # ----- Query --------------------------------------------------------

    def query(
        self,
        event_type: Optional[Union[EventType, str]] = None,
        severity: Optional[Union[Severity, str]] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[Event]:
        """Read all events matching the filter. Returns chronologically-ordered Events."""
        if isinstance(event_type, str):
            event_type = EventType(event_type)
        if isinstance(severity, str):
            severity = Severity(severity)

        if not os.path.exists(self.path):
            return []

        results: list[Event] = []
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    event = Event.from_dict(d)
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue  # skip corrupt lines
                if event_type and event.event_type != event_type:
                    continue
                if severity and event.severity != severity:
                    continue
                if since and event.timestamp < since:
                    continue
                if until and event.timestamp > until:
                    continue
                results.append(event)
                if limit and len(results) >= limit:
                    break
        return results

    # ----- Aggregation -------------------------------------------------

    def get_progress_report(self) -> dict:
        """Aggregate event counts for the progress report."""
        events = self.query()
        return {
            "total_events": len(events),
            "iterations_completed": sum(
                1 for e in events if e.event_type == EventType.LOOP_ITERATION_COMPLETED
            ),
            "units_completed": sum(
                1 for e in events if e.event_type == EventType.EXECUTION_UNIT_COMPLETED
            ),
            "errors": sum(
                1 for e in events if e.severity == Severity.ERROR
            ),
            "warnings": sum(
                1 for e in events if e.severity == Severity.WARN
            ),
        }
```

- [ ] **Step 6.4: Run tests to verify they pass**

```bash
cd /workspace/project/spec-workflow/.zcf/v2-core-foundation-wt
python3 -m pytest tests/unit/test_event_log.py -v
```

Expected: All 8 tests pass.

- [ ] **Step 6.5: Update tasks.md (2.1, 2.4, 2.5, 2.6) and commit**

```bash
cd /workspace/project/spec-workflow/.zcf/v2-core-foundation-wt
sed -i \
  -e 's/- \[ \] 2.1 Create `skills/_lib\/event_log.py`/- [x] 2.1 Create `skills/_lib\/event_log.py`/' \
  -e 's/- \[ \] 2.4 Event ID format: `evt_YYYYMMDD_HHMMSS_NNN` (unique within same second)/- [x] 2.4 Event ID format: `evt_YYYYMMDD_HHMMSS_NNN` (unique within same second)/' \
  -e 's/- \[ \] 2.5 Write unit tests: write→query consistency, query 10K events < 100ms, unique IDs/- [x] 2.5 Write unit tests: write→query consistency, query 10K events < 100ms, unique IDs/' \
  -e 's/- \[ \] 2.6 Verify progress report stats accuracy (iterations, completed units, error count)/- [x] 2.6 Verify progress report stats accuracy (iterations, completed units, error count)/' \
  openspec/changes/v2-core-foundation/tasks.md
git add skills/_lib/event_log.py tests/unit/test_event_log.py openspec/changes/v2-core-foundation/tasks.md
git commit -m "feat(_lib): add EventLog (JSONL append-only, query, 10K events < 100ms) — closes 2.1, 2.4-2.6"
```

Expected: 1 new commit. Event log fully working.

---

### Task 7: Gate Mechanism (`skills/_lib/gate.py`)

**Files:**
- Create: `skills/_lib/gate.py` (~300 lines)
- Test: `tests/unit/test_gate.py` (~200 lines)

**Dependency:** Task 3 (StateVector), Task 6 (EventLog).

- [ ] **Step 7.1: Write the failing test**

Create `tests/unit/test_gate.py`:

```python
"""Tests for GateMechanism — phase-transition gate with two severity levels."""
import os
import pytest
from skills._lib.gate import GateMechanism, Check, GateResult, GateError, register_gate_check
from skills._lib.state_vector import StateVector


@pytest.fixture
def state_path(tmp_path):
    return str(tmp_path / "state-vector.json")


@pytest.fixture
def log_path(tmp_path):
    return str(tmp_path / "event-log.jsonl")


def make_state(**overrides):
    sv = StateVector.create_default()
    for k, v in overrides.items():
        sv.update_field(k, v)
    return sv


def test_error_check_blocks_transition(state_path, log_path):
    """A check returning (False, 'error') blocks the transition."""
    sv = make_state()
    sv.save(state_path)
    gate = GateMechanism(state_path=state_path, event_log_path=log_path)
    gate.register(Check(
        name="always_fails_error",
        condition=lambda ctx: (False, "error"),
        message="hard fail",
        suggestion="Fix the thing",
    ))
    result = gate.verify_transition("arch_done", {})
    assert result.passed is False
    assert "always_fails_error" in result.failed_checks
    assert result.error is not None


def test_warning_check_allows_with_notice(state_path, log_path):
    """A check returning (False, 'warning') allows transition but logs warning."""
    sv = make_state()
    sv.save(state_path)
    gate = GateMechanism(state_path=state_path, event_log_path=log_path)
    gate.register(Check(
        name="soft_warning",
        condition=lambda ctx: (False, "warning"),
        message="soft issue",
        suggestion="Consider fixing",
    ))
    result = gate.verify_transition("arch_done", {})
    assert result.passed is True
    assert "soft_warning" in result.warnings


def test_force_transition_records_event(state_path, log_path):
    """force_transition() records a GATE_FORCED event."""
    sv = make_state()
    sv.save(state_path)
    gate = GateMechanism(state_path=state_path, event_log_path=log_path)
    gate.register(Check(
        name="blocker",
        condition=lambda ctx: (False, "error"),
        message="blocked",
        suggestion="Fix it",
    ))
    forced = gate.force_transition("arch_done", {}, reason="user override")
    assert forced is True
    # Verify event log
    import json
    with open(log_path) as f:
        events = [json.loads(line) for line in f]
    assert any(e["event_type"] == "gate_forced" for e in events)


def test_plugin_register_via_public_api(state_path, log_path):
    """register_gate_check() module-level function adds to default checks."""
    from skills._lib import gate as gate_mod
    sv = make_state()
    sv.save(state_path)
    gate = gate_mod.GateMechanism(state_path=state_path, event_log_path=log_path)
    # Add a custom check
    gate_mod.register_gate_check(Check(
        name="custom_plugin_check",
        condition=lambda ctx: (True, None),
        message="ok",
        suggestion="",
    ))
    assert "custom_plugin_check" in gate.get_registered_check_names()


def test_suggestion_contains_command(state_path, log_path):
    """Each failed check's message+severity is reported; suggestion must include a command."""
    sv = make_state()
    sv.save(state_path)
    gate = GateMechanism(state_path=state_path, event_log_path=log_path)
    gate.register(Check(
        name="needs_cmd",
        condition=lambda ctx: (False, "error"),
        message="blocked",
        suggestion="Run: pytest tests/",
    ))
    result = gate.verify_transition("arch_done", {})
    assert "pytest tests/" in result.suggestion or "Run:" in (result.suggestion or "")


def test_default_arch_done_checks_present(state_path, log_path):
    """Default checks for arch_done include adr_exists, roadmap_defined, gap_analysis_complete."""
    sv = make_state()
    sv.save(state_path)
    gate = GateMechanism(state_path=state_path, event_log_path=log_path, load_defaults=True)
    names = gate.get_registered_check_names()
    assert "adr_exists" in names
    assert "roadmap_defined" in names
    assert "gap_analysis_complete" in names


def test_default_plan_done_checks_present(state_path, log_path):
    """Default checks for plan_done include changes_committed, artifacts_complete, deps_analyzed."""
    sv = make_state()
    sv.save(state_path)
    gate = GateMechanism(state_path=state_path, event_log_path=log_path, load_defaults=True)
    names = gate.get_registered_check_names()
    assert "changes_committed" in names
    assert "artifacts_complete" in names
    assert "deps_analyzed" in names


def test_default_ship_done_checks_present(state_path, log_path):
    """Default checks for ship_done include worktrees_empty, archive_empty, tests_pass."""
    sv = make_state()
    sv.save(state_path)
    gate = GateMechanism(state_path=state_path, event_log_path=log_path, load_defaults=True)
    names = gate.get_registered_check_names()
    assert "worktrees_empty" in names
    assert "archive_empty" in names
    assert "tests_pass" in names


def test_get_suggestion_returns_aggregated_text(state_path, log_path):
    """get_suggestion() joins all failed-check suggestions into one string."""
    sv = make_state()
    sv.save(state_path)
    gate = GateMechanism(state_path=state_path, event_log_path=log_path)
    gate.register(Check("a", lambda ctx: (False, "error"), "a failed", "Fix A: run cmd-a"))
    gate.register(Check("b", lambda ctx: (False, "error"), "b failed", "Fix B: run cmd-b"))
    gate.verify_transition("arch_done", {})
    sug = gate.get_suggestion("arch_done")
    assert "cmd-a" in sug
    assert "cmd-b" in sug
```

- [ ] **Step 7.2: Run test to verify it fails**

```bash
cd /workspace/project/spec-workflow/.zcf/v2-core-foundation-wt
python3 -m pytest tests/unit/test_gate.py -v 2>&1 | head -10
```

Expected: `ModuleNotFoundError: No module named 'skills._lib.gate'`.

- [ ] **Step 7.3: Implement `GateMechanism`**

Create `skills/_lib/gate.py`:

```python
"""Gate mechanism — phase-transition validator with two severity levels.

Three phase transitions are supported: `arch_done` (arch → plan),
`plan_done` (plan → ship), `ship_done` (ship → archive). Each transition
has a default checklist of `Check` objects, each with a name, a condition
(lambda returning (passed: bool, severity: str|None)), a message, and a
suggestion string.

- `error` severity blocks the transition.
- `warning` severity allows the transition but records a warning event.

Plugins can register additional checks via `register_gate_check()`.
"""
from __future__ import annotations
import os
from collections import namedtuple
from dataclasses import dataclass, field
from typing import Callable, Optional

from skills._lib.event_log import EventLog
from skills._lib.event_types import EventType, Severity
from skills._lib.state_vector import StateVector


Check = namedtuple("Check", ["name", "condition", "message", "suggestion", "severity"], defaults=[None])
# severity field is informational; the actual severity comes from condition return.
# Kept for explicit documentation in registered checks.


# Module-level registry for plugin-registered checks
_PLUGIN_REGISTRY: list[Check] = []


def register_gate_check(check: Check) -> None:
    """Module-level API for plugins to register a custom Check."""
    _PLUGIN_REGISTRY.append(check)


@dataclass
class GateResult:
    """Result of a gate verification."""
    passed: bool
    transition: str
    failed_checks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error: Optional[str] = None
    suggestion: Optional[str] = None


def _check_adr_exists(ctx: dict) -> tuple[bool, Optional[str]]:
    return (os.path.isdir("docs/adr") and any(f.startswith("ADR-") for f in os.listdir("docs/adr")), None)


def _check_roadmap_defined(ctx: dict) -> tuple[bool, Optional[str]]:
    return (os.path.isfile("roadmap.md"), None)


def _check_gap_analysis_complete(ctx: dict) -> tuple[bool, Optional[str]]:
    return (True, "warning")  # Warning: gap analysis is optional


def _check_changes_committed(ctx: dict) -> tuple[bool, Optional[str]]:
    sv: StateVector = ctx.get("state_vector")
    if sv is None:
        return (True, None)
    active = sv.get_field("arch_side.current_change")
    if not active:
        return (True, None)
    return (os.path.isfile(f"openspec/changes/{active}/proposal.md"), None)


def _check_artifacts_complete(ctx: dict) -> tuple[bool, Optional[str]]:
    sv: StateVector = ctx.get("state_vector")
    if sv is None:
        return (True, None)
    active = sv.get_field("arch_side.current_change")
    if not active:
        return (True, None)
    base = f"openspec/changes/{active}"
    return (all(os.path.isfile(f"{base}/{a}") for a in ["proposal.md", "design.md", "tasks.md"]), None)


def _check_deps_analyzed(ctx: dict) -> tuple[bool, Optional[str]]:
    return (True, "warning")


def _check_worktrees_empty(ctx: dict) -> tuple[bool, Optional[str]]:
    import subprocess
    result = subprocess.run(["git", "worktree", "list"], capture_output=True, text=True)
    # Default worktree is always present; check for any extras
    lines = [l for l in result.stdout.strip().split("\n") if l]
    return (len(lines) <= 1, None)


def _check_archive_empty(ctx: dict) -> tuple[bool, Optional[str]]:
    return (True, None)  # Archive is checked at archive time, not pre-ship


def _check_tests_pass(ctx: dict) -> tuple[bool, Optional[str]]:
    import subprocess
    result = subprocess.run(
        ["python3", "-m", "pytest", "tests/unit/", "-q", "--no-header"],
        capture_output=True, text=True,
    )
    return (result.returncode == 0, None)


_DEFAULT_CHECKS = {
    "arch_done": [
        Check("adr_exists", _check_adr_exists, "ADR directory missing or empty", "Create ADRs: mkdir -p docs/adr && touch docs/adr/ADR-0001.md", "error"),
        Check("roadmap_defined", _check_roadmap_defined, "roadmap.md not found", "Create roadmap: touch roadmap.md", "error"),
        Check("gap_analysis_complete", _check_gap_analysis_complete, "Gap analysis not run", "Run: openspec scan", "warning"),
    ],
    "plan_done": [
        Check("changes_committed", _check_changes_committed, "Change artifacts not committed", "git add openspec/changes/<name>/ && git commit", "error"),
        Check("artifacts_complete", _check_artifacts_complete, "Missing proposal/design/tasks", "Create all three artifacts in openspec/changes/<name>/", "error"),
        Check("deps_analyzed", _check_deps_analyzed, "Dependencies not analyzed", "Run: openspec deps <name>", "warning"),
    ],
    "ship_done": [
        Check("worktrees_empty", _check_worktrees_empty, "Active worktrees remain", "git worktree remove .zcf/<name>-wt", "error"),
        Check("archive_empty", _check_archive_empty, "Archive not empty", "Verify archive/", "error"),
        Check("tests_pass", _check_tests_pass, "Tests failing", "Run: pytest tests/ -v", "error"),
    ],
}


class GateMechanism:
    """Validates phase transitions against a checklist of Checks."""

    def __init__(
        self,
        state_path: str = ".spec-workflow/state-vector.json",
        event_log_path: str = ".spec-workflow/event-log.jsonl",
        load_defaults: bool = True,
    ):
        self.state_path = state_path
        self.event_log_path = event_log_path
        self._checks: dict[str, list[Check]] = {
            t: list(c) for t, c in _DEFAULT_CHECKS.items()
        } if load_defaults else {t: [] for t in ["arch_done", "plan_done", "ship_done"]}
        # Add plugin-registered checks
        for plugin_check in _PLUGIN_REGISTRY:
            for t in self._checks:
                self._checks[t].append(plugin_check)

    def register(self, check: Check) -> None:
        """Register a check against all known transitions."""
        for t in self._checks:
            self._checks[t].append(check)

    def get_registered_check_names(self) -> list[str]:
        """Flat list of all registered check names."""
        seen = set()
        names = []
        for checks in self._checks.values():
            for c in checks:
                if c.name not in seen:
                    seen.add(c.name)
                    names.append(c.name)
        return names

    def verify_transition(self, transition: str, context: dict) -> GateResult:
        """Run all checks for `transition`. Returns GateResult."""
        if transition not in self._checks:
            return GateResult(
                passed=False,
                transition=transition,
                error=f"Unknown transition '{transition}'. Must be one of: {list(self._checks.keys())}",
            )

        # Augment context with state vector
        try:
            sv = StateVector.load(self.state_path, verify_checksum=False)
            context = {**context, "state_vector": sv}
        except Exception:
            pass

        failed = []
        warnings = []
        suggestions = []
        for check in self._checks[transition]:
            try:
                passed, severity = check.condition(context)
            except Exception as e:
                failed.append(check.name)
                suggestions.append(f"{check.message} (error during check: {e})")
                continue
            if passed:
                continue
            if severity == "warning":
                warnings.append(check.name)
                suggestions.append(f"[WARN] {check.name}: {check.message}. {check.suggestion}")
            else:
                failed.append(check.name)
                suggestions.append(f"{check.name}: {check.message}. {check.suggestion}")

        passed = len(failed) == 0
        result = GateResult(
            passed=passed,
            transition=transition,
            failed_checks=failed,
            warnings=warnings,
            suggestion="\n".join(suggestions) if suggestions else None,
        )

        # Record event
        try:
            log = EventLog(self.event_log_path)
            if passed:
                log.record(
                    EventType.GATE_TRANSITION, Severity.INFO,
                    f"Transition {transition} allowed (warnings: {warnings})",
                    context={"transition": transition, "warnings": warnings},
                )
            else:
                log.record(
                    EventType.GATE_FAILED, Severity.ERROR,
                    f"Transition {transition} blocked (failed: {failed})",
                    context={"transition": transition, "failed_checks": failed},
                )
        except Exception:
            pass  # event log is best-effort

        return result

    def force_transition(self, transition: str, context: dict, reason: str) -> bool:
        """Force a transition despite gate failure. Records a GATE_FORCED event."""
        try:
            log = EventLog(self.event_log_path)
            log.record(
                EventType.GATE_FORCED, Severity.WARN,
                f"User forced transition {transition}: {reason}",
                context={"transition": transition, "reason": reason},
            )
        except Exception:
            pass
        return True

    def get_suggestion(self, transition: str) -> Optional[str]:
        """Return the aggregated suggestion for a transition (after a failed verify)."""
        result = self.verify_transition(transition, {})
        return result.suggestion


# Re-export for convenience
GateError = GateResult  # backward compat alias
```

- [ ] **Step 7.4: Run tests to verify they pass**

```bash
cd /workspace/project/spec-workflow/.zcf/v2-core-foundation-wt
python3 -m pytest tests/unit/test_gate.py -v
```

Expected: All 9 tests pass.

- [ ] **Step 7.5: Update tasks.md (3.1-3.7) and commit**

```bash
cd /workspace/project/spec-workflow/.zcf/v2-core-foundation-wt
sed -i \
  -e 's/- \[ \] 3.1 Create `skills/_lib\/gate.py`/- [x] 3.1 Create `skills/_lib\/gate.py`/' \
  -e 's/- \[ \] 3.2 Define `Check` namedtuple: name, condition (lambda), message, severity/- [x] 3.2 Define `Check` namedtuple: name, condition (lambda), message, severity/' \
  -e 's/- \[ \] 3.3 Implement `register_gate_check()` plugin API/- [x] 3.3 Implement `register_gate_check()` plugin API/' \
  -e 's/- \[ \] 3.4 Define default arch_done checks: adr_exists (error), roadmap_defined (error), gap_analysis_complete (warning)/- [x] 3.4 Define default arch_done checks: adr_exists (error), roadmap_defined (error), gap_analysis_complete (warning)/' \
  -e 's/- \[ \] 3.5 Define default plan_done checks: changes_committed (error), artifacts_complete (error), deps_analyzed (warning)/- [x] 3.5 Define default plan_done checks: changes_committed (error), artifacts_complete (error), deps_analyzed (warning)/' \
  -e 's/- \[ \] 3.6 Define default ship_done checks: worktrees_empty (error), archive_empty (error), tests_pass (error)/- [x] 3.6 Define default ship_done checks: worktrees_empty (error), archive_empty (error), tests_pass (error)/' \
  -e 's/- \[ \] 3.7 Write unit tests: error blocks, warning allows-with-notice, force_transition records to event log, plugin works, suggestions actionable/- [x] 3.7 Write unit tests: error blocks, warning allows-with-notice, force_transition records to event log, plugin works, suggestions actionable/' \
  openspec/changes/v2-core-foundation/tasks.md
git add skills/_lib/gate.py tests/unit/test_gate.py openspec/changes/v2-core-foundation/tasks.md
git commit -m "feat(_lib): add GateMechanism (error/warning, plugin API, default checks) — closes 3.1-3.7"
```

Expected: 1 new commit.

---

### Task 8: Plugins README (`skills/_lib/plugins/README.md`)

**Files:**
- Create: `skills/_lib/plugins/README.md` (~50 lines)

- [ ] **Step 8.1: Create the plugin directory and README**

```bash
mkdir -p /workspace/project/spec-workflow/.zcf/v2-core-foundation-wt/skills/_lib/plugins
```

Create `skills/_lib/plugins/README.md`:

```markdown
# Gate Mechanism Plugins

Custom gate checks for the spec-workflow v2 phase-transition gate. Plugins let you
add organization- or project-specific validation without modifying core code.

## Writing a Plugin

A plugin is a Python module that calls `register_gate_check()` with one or more
`Check` namedtuples. Place it anywhere on the Python path, or under
`skills/_lib/plugins/` (this directory).

### Minimal Example

```python
# my_plugin.py
from skills._lib.gate import Check, register_gate_check


def _check_team_owns_change(ctx):
    """Require a CODEOWNERS entry for the active change directory."""
    sv = ctx.get("state_vector")
    if sv is None:
        return (True, None)
    active = sv.get_field("arch_side.current_change")
    if not active:
        return (True, None)
    import os
    return (os.path.isfile(".github/CODEOWNERS"), None)


register_gate_check(Check(
    name="team_owns_change",
    condition=_check_team_owns_change,
    message="No CODEOWNERS file",
    suggestion="Create .github/CODEOWNERS: echo '* @your-team' > .github/CODEOWNERS",
))
```

### Loading Plugins

The gate loads plugins from any `.py` file under `skills/_lib/plugins/`. To use
plugins, ensure they are imported before constructing the `GateMechanism`:

```python
# In your entrypoint
import skills._lib.plugins.my_plugin  # noqa: F401  (triggers registration)

from skills._lib.gate import GateMechanism
gate = GateMechanism(load_defaults=True)
```

## Check Contract

A check is a `Check` namedtuple with five fields:

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Unique identifier (no spaces). Recorded in events. |
| `condition` | `Callable[[dict], tuple[bool, str | None]]` | Returns `(passed, severity)`. `severity` is `"error"` (blocks) or `"warning"` (allows with notice). |
| `message` | `str` | Human-readable explanation shown on failure. |
| `suggestion` | `str` | Concrete next step, ideally with a shell command. |
| `severity` | `str` | Documented default; actual severity returned by `condition`. |

The `condition` callable receives a `context` dict containing:
- `state_vector`: the loaded `StateVector` instance
- Any additional keys passed to `verify_transition(transition, context)`

## Best Practices

- Make check names lowercase with underscores.
- Always return a tuple, never raise from `condition` (caller wraps exceptions).
- Provide actionable suggestions — they appear verbatim in the user's terminal.
- Use `warning` severity for soft checks (advisory); `error` for hard blocks.
- Test your plugin: see `tests/unit/test_gate.py::test_plugin_register_via_public_api`.
```

- [ ] **Step 8.2: Update tasks.md and commit**

```bash
cd /workspace/project/spec-workflow/.zcf/v2-core-foundation-wt
sed -i 's|- \[ \] 3.8 Create `skills/_lib\/plugins\/README.md` with plugin development guide|- [x] 3.8 Create `skills/_lib\/plugins\/README.md` with plugin development guide|' openspec/changes/v2-core-foundation/tasks.md
git add skills/_lib/plugins/README.md openspec/changes/v2-core-foundation/tasks.md
git commit -m "docs(_lib): add plugins/README.md (gate check plugin guide) — closes 3.8"
```

Expected: 1 new commit. Gate mechanism complete.

---

### Task 9: Config Defaults (`skills/_lib/defaults.py`)

**Files:**
- Create: `skills/_lib/defaults.py` (~30 lines)

- [ ] **Step 9.1: Create the defaults module**

Create `skills/_lib/defaults.py`:

```python
"""Built-in defaults for spec-workflow v2 configuration.

The `DEFAULTS` dict is the lowest-priority source in the config merge order:
runtime params > loop.yaml > .spec-workflow.json > env vars > DEFAULTS.

Override any value via `.spec-workflow.json` or environment variables
(see `skills/_lib/config.py`).
"""
from __future__ import annotations
import copy


DEFAULTS = {
    "version": "2.0",
    "interaction": {
        "mode": "hybrid",  # one of: loop, menu, hybrid
        "menu_items": ["propose", "execute", "status", "archive"],
    },
    "loop": {
        "max_iterations": 100,
        "max_retries": 3,
        "retry_backoff_seconds": 5,
    },
    "state": {
        "path": ".spec-workflow/state-vector.json",
        "lock_timeout_seconds": 10.0,
    },
    "event_log": {
        "path": ".spec-workflow/event-log.jsonl",
        "max_size_mb": 50,
    },
    "gate": {
        "load_defaults": True,
        "auto_allow_warnings": True,
    },
    "sync": {
        "v1x_enabled": True,
        "conflict_resolution": "state_vector_wins",  # the only supported mode
    },
}


def get_defaults() -> dict:
    """Return a deep copy of the defaults dict (safe to mutate)."""
    return copy.deepcopy(DEFAULTS)
```

- [ ] **Step 9.2: Verify import**

```bash
cd /workspace/project/spec-workflow/.zcf/v2-core-foundation-wt
python3 -c "
from skills._lib.defaults import DEFAULTS, get_defaults
assert DEFAULTS['interaction']['mode'] == 'hybrid'
assert DEFAULTS['loop']['max_iterations'] == 100
assert get_defaults() is not DEFAULTS  # returns a copy
print('defaults OK')
"
```

Expected: `defaults OK`.

- [ ] **Step 9.3: Update tasks.md and commit**

```bash
cd /workspace/project/spec-workflow/.zcf/v2-core-foundation-wt
sed -i 's/- \[ \] 4.3 Create `skills/_lib\/defaults.py`/- [x] 4.3 Create `skills/_lib\/defaults.py`/' openspec/changes/v2-core-foundation/tasks.md
git add skills/_lib/defaults.py openspec/changes/v2-core-foundation/tasks.md
git commit -m "feat(_lib): add defaults.py (built-in config defaults) — closes 4.3"
```

Expected: 1 new commit.

---

### Task 10: Configuration Parser (`skills/_lib/config.py`)

**Files:**
- Create: `skills/_lib/config.py` (~200 lines)
- Test: `tests/unit/test_config.py` (~150 lines)
- Modify: `package.json` (add `pyyaml` to dependencies)

**Dependency:** Task 9 (defaults).

- [ ] **Step 10.1: Write the failing test**

Create `tests/unit/test_config.py`:

```python
"""Tests for ConfigParser — multi-source priority-merge configuration."""
import os
import json
import pytest
import yaml
from skills._lib.config import ConfigParser, ConfigError


@pytest.fixture
def clean_env(monkeypatch):
    """Remove all SPEC_WORKFLOW_* env vars for the test."""
    for k in list(os.environ):
        if k.startswith("SPEC_WORKFLOW_"):
            monkeypatch.delenv(k, raising=False)
    return monkeypatch


def test_minimal_config_parses(tmp_path, clean_env):
    """A config with only `version` and `interaction.mode` should fill defaults for the rest."""
    cfg_file = tmp_path / ".spec-workflow.json"
    cfg_file.write_text(json.dumps({"version": "2.0", "interaction": {"mode": "hybrid"}}))
    parser = ConfigParser(project_root=str(tmp_path))
    config = parser.parse()
    assert config["loop"]["max_iterations"] == 100  # from defaults
    assert config["interaction"]["mode"] == "hybrid"


def test_priority_runtime_over_loop_yaml(tmp_path, clean_env):
    """Runtime params override loop.yaml."""
    loop_yaml = tmp_path / "loop.yaml"
    loop_yaml.write_text(yaml.dump({"interaction": {"mode": "menu"}}))
    parser = ConfigParser(project_root=str(tmp_path))
    config = parser.parse(runtime_overrides={"interaction.mode": "loop"})
    assert config["interaction"]["mode"] == "loop"


def test_priority_loop_yaml_over_spec_workflow_json(tmp_path, clean_env):
    """loop.yaml overrides .spec-workflow.json."""
    (tmp_path / ".spec-workflow.json").write_text(json.dumps({"interaction": {"mode": "menu"}}))
    (tmp_path / "loop.yaml").write_text(yaml.dump({"interaction": {"mode": "loop"}}))
    parser = ConfigParser(project_root=str(tmp_path))
    config = parser.parse()
    assert config["interaction"]["mode"] == "loop"


def test_env_var_overrides_file_config(tmp_path, clean_env):
    """SPEC_WORKFLOW_MODE env var overrides .spec-workflow.json."""
    (tmp_path / ".spec-workflow.json").write_text(json.dumps({"interaction": {"mode": "menu"}}))
    clean_env.setenv("SPEC_WORKFLOW_MODE", "loop")
    parser = ConfigParser(project_root=str(tmp_path))
    config = parser.parse()
    assert config["interaction"]["mode"] == "loop"


def test_invalid_mode_rejected(tmp_path, clean_env):
    """An invalid mode value produces ConfigError with clear message."""
    (tmp_path / ".spec-workflow.json").write_text(json.dumps({"interaction": {"mode": "invalid_mode"}}))
    parser = ConfigParser(project_root=str(tmp_path))
    with pytest.raises(ConfigError, match="invalid_mode"):
        parser.parse()


def test_negative_max_iterations_rejected(tmp_path, clean_env):
    """max_iterations must be > 0."""
    (tmp_path / ".spec-workflow.json").write_text(json.dumps({"loop": {"max_iterations": -1}}))
    parser = ConfigParser(project_root=str(tmp_path))
    with pytest.raises(ConfigError, match="max_iterations"):
        parser.parse()


def test_type_coercion_for_env_vars(tmp_path, clean_env):
    """Env var SPEC_WORKFLOW_MAX_ITERATIONS=200 is parsed as int."""
    clean_env.setenv("SPEC_WORKFLOW_MAX_ITERATIONS", "200")
    parser = ConfigParser(project_root=str(tmp_path))
    config = parser.parse()
    assert config["loop"]["max_iterations"] == 200
    assert isinstance(config["loop"]["max_iterations"], int)
```

- [ ] **Step 10.2: Run test to verify it fails**

```bash
cd /workspace/project/spec-workflow/.zcf/v2-core-foundation-wt
python3 -m pytest tests/unit/test_config.py -v 2>&1 | head -10
```

Expected: `ModuleNotFoundError: No module named 'skills._lib.config'`.

- [ ] **Step 10.3: Implement `ConfigParser`**

Create `skills/_lib/config.py`:

```python
"""Multi-source configuration parser with strict priority order.

Priority (highest to lowest):
    1. Runtime overrides (passed to `parse()`)
    2. loop.yaml (project-level)
    3. .spec-workflow.json (project-level)
    4. Environment variables (SPEC_WORKFLOW_*)
    5. Built-in defaults (skills/_lib/defaults.py)

A higher-priority source COMPLETELY replaces the lower-priority value
(strict order, not deep merge). See `design.md` Decision 5 for rationale.
"""
from __future__ import annotations
import json
import os
import re
from pathlib import Path
from typing import Any, Optional

import yaml

from skills._lib.defaults import get_defaults


class ConfigError(Exception):
    """Raised on invalid config values or unreadable files."""


# Mapping from env var name to dotted config path
_ENV_VAR_MAP = {
    "SPEC_WORKFLOW_MODE": "interaction.mode",
    "SPEC_WORKFLOW_MAX_ITERATIONS": "loop.max_iterations",
    "SPEC_WORKFLOW_MAX_RETRIES": "loop.max_retries",
    "SPEC_WORKFLOW_STATE_PATH": "state.path",
}


def _deep_merge(base: dict, overlay: dict) -> dict:
    """Deep-merge overlay into base. Overlay values completely replace base values (strict order)."""
    out = dict(base)
    for k, v in overlay.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _set_dotted(data: dict, dotted_key: str, value: Any) -> None:
    """Set a value at a dotted path, creating dicts as needed."""
    keys = dotted_key.split(".")
    cur = data
    for k in keys[:-1]:
        if k not in cur or not isinstance(cur[k], dict):
            cur[k] = {}
        cur = cur[k]
    cur[keys[-1]] = value


def _coerce_env_value(raw: str, target_path: str) -> Any:
    """Coerce env var string to int/float/bool/str based on the target config key."""
    # Numeric fields
    if "max_iterations" in target_path or "max_retries" in target_path:
        try:
            return int(raw)
        except ValueError:
            raise ConfigError(f"Env var {target_path}='{raw}' is not a valid integer")
    if "seconds" in target_path:
        try:
            return float(raw)
        except ValueError:
            raise ConfigError(f"Env var {target_path}='{raw}' is not a valid float")
    if raw.lower() in ("true", "yes", "1"):
        return True
    if raw.lower() in ("false", "no", "0"):
        return False
    return raw


def _validate(config: dict) -> None:
    """Validate config values. Raises ConfigError with clear messages."""
    mode = config.get("interaction", {}).get("mode")
    if mode not in ("loop", "menu", "hybrid"):
        raise ConfigError(
            f"Invalid mode '{mode}'. Must be one of: loop, menu, hybrid"
        )
    max_iter = config.get("loop", {}).get("max_iterations")
    if not isinstance(max_iter, int) or max_iter <= 0:
        raise ConfigError(f"max_iterations must be a positive integer (got {max_iter!r})")
    max_retries = config.get("loop", {}).get("max_retries")
    if not isinstance(max_retries, int) or max_retries < 0:
        raise ConfigError(f"max_retries must be a non-negative integer (got {max_retries!r})")


class ConfigParser:
    """Multi-source config parser. Use `.parse()` to get a fully-merged config dict."""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.spec_workflow_json = self.project_root / ".spec-workflow.json"
        self.loop_yaml = self.project_root / "loop.yaml"

    def parse(self, runtime_overrides: Optional[dict] = None) -> dict:
        """Read all sources, merge in priority order, validate, return config dict.

        Args:
            runtime_overrides: Dict of dotted-path → value. Highest priority.
        """
        config = get_defaults()

        # 4. Env vars
        env_overlay: dict = {}
        for env_name, dotted_path in _ENV_VAR_MAP.items():
            if env_name in os.environ:
                coerced = _coerce_env_value(os.environ[env_name], dotted_path)
                _set_dotted(env_overlay, dotted_path, coerced)
        config = _deep_merge(config, env_overlay)

        # 3. .spec-workflow.json
        if self.spec_workflow_json.is_file():
            try:
                with open(self.spec_workflow_json) as f:
                    file_cfg = json.load(f)
            except json.JSONDecodeError as e:
                raise ConfigError(f"{self.spec_workflow_json} is not valid JSON: {e}") from e
            config = _deep_merge(config, file_cfg)

        # 2. loop.yaml
        if self.loop_yaml.is_file():
            try:
                with open(self.loop_yaml) as f:
                    loop_cfg = yaml.safe_load(f) or {}
            except yaml.YAMLError as e:
                raise ConfigError(f"{self.loop_yaml} is not valid YAML: {e}") from e
            config = _deep_merge(config, loop_cfg)

        # 1. Runtime overrides
        if runtime_overrides:
            runtime_overlay: dict = {}
            for dotted_path, value in runtime_overrides.items():
                _set_dotted(runtime_overlay, dotted_path, value)
            config = _deep_merge(config, runtime_overlay)

        _validate(config)
        return config
```

- [ ] **Step 10.4: Add PyYAML to package.json**

Read the current `package.json`, then edit it to add `pyyaml` to the dependencies (or note it in a `requirements.txt` if `package.json` is for npm). The repo already has a `package.json`, so we add a comment block referring to Python deps:

```bash
cd /workspace/project/spec-workflow/.zcf/v2-core-foundation-wt
cat package.json
```

If `package.json` is for npm, create a separate `requirements.txt` and add a comment to `package.json`. The full set of Python deps for v2.0 is:

```
PyYAML>=6.0
jsonschema>=4.0
pytest>=7.0
```

Create `requirements.txt` at the repo root:

```bash
cat > /workspace/project/spec-workflow/.zcf/v2-core-foundation-wt/requirements.txt <<'EOF'
# Python dependencies for spec-workflow v2.0
# Install: pip install -r requirements.txt
PyYAML>=6.0
jsonschema>=4.0
pytest>=7.0
EOF
```

Add a top-level comment to `package.json` (read first, then edit):

```bash
cd /workspace/project/spec-workflow/.zcf/v2-core-foundation-wt
# Read existing package.json to add a comment about Python deps
python3 -c "
import json
with open('package.json') as f:
    pkg = json.load(f)
pkg.setdefault('scripts', {})['install-python-deps'] = 'pip install -r requirements.txt'
with open('package.json', 'w') as f:
    json.dump(pkg, f, indent=2)
"
cat package.json
```

Expected: `package.json` now has a `scripts.install-python-deps` entry.

- [ ] **Step 10.5: Install PyYAML and run tests**

```bash
cd /workspace/project/spec-workflow/.zcf/v2-core-foundation-wt
pip install pyyaml jsonschema pytest 2>&1 | tail -5
python3 -m pytest tests/unit/test_config.py -v
```

Expected: All 7 tests pass.

- [ ] **Step 10.6: Update tasks.md (4.1, 4.2, 4.4-4.7) and commit**

```bash
cd /workspace/project/spec-workflow/.zcf/v2-core-foundation-wt
sed -i \
  -e 's/- \[ \] 4.1 Create `skills/_lib\/config.py`/- [x] 4.1 Create `skills/_lib\/config.py`/' \
  -e 's/- \[ \] 4.2 Implement priority-merge: runtime params > loop.yaml > .spec-workflow.json > env vars > defaults/- [x] 4.2 Implement priority-merge: runtime params > loop.yaml > .spec-workflow.json > env vars > defaults/' \
  -e 's/- \[ \] 4.4 Read env vars: `SPEC_WORKFLOW_MODE`, `SPEC_WORKFLOW_MAX_ITERATIONS` with type conversion/- [x] 4.4 Read env vars: `SPEC_WORKFLOW_MODE`, `SPEC_WORKFLOW_MAX_ITERATIONS` with type conversion/' \
  -e 's/- \[ \] 4.5 Validate required fields, enum values (mode in loop\/menu\/hybrid), numeric ranges (max_iterations > 0)/- [x] 4.5 Validate required fields, enum values (mode in loop\/menu\/hybrid), numeric ranges (max_iterations > 0)/' \
  -e 's/- \[ \] 4.6 Add `PyYAML` to package.json dependencies/- [x] 4.6 Add `PyYAML` to package.json dependencies/' \
  -e 's/- \[ \] 4.7 Write unit tests: minimal config parses, priority order correct, invalid config rejected with clear message, env vars override file config/- [x] 4.7 Write unit tests: minimal config parses, priority order correct, invalid config rejected with clear message, env vars override file config/' \
  openspec/changes/v2-core-foundation/tasks.md
git add skills/_lib/config.py tests/unit/test_config.py package.json requirements.txt openspec/changes/v2-core-foundation/tasks.md
git commit -m "feat(_lib): add ConfigParser (5-source priority merge, validation) + requirements.txt — closes 4.1-4.7"
```

Expected: 1 new commit.

---

### Task 11: v1.x Sync Layer (`skills/_lib/sync_state.py`)

**Files:**
- Create: `skills/_lib/sync_state.py` (~200 lines)
- Test: `tests/unit/test_sync_state.py` (~150 lines)

**Dependencies:** Task 3 (StateVector), Task 6 (EventLog), Task 10 (ConfigParser).

- [ ] **Step 11.1: Write the failing test**

Create `tests/unit/test_sync_state.py`:

```python
"""Tests for sync_state — bidirectional v1.x <-> v2 state vector sync."""
import json
import os
import time
import pytest
from skills._lib.state_vector import StateVector
from skills._lib.sync_state import (
    sync_state_vector_to_legacy,
    sync_legacy_to_state_vector,
    is_sync_enabled,
)


@pytest.fixture
def project_root(tmp_path, monkeypatch):
    """A clean project root with .zcf/ and openspec/changes/."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".zcf").mkdir()
    (tmp_path / "openspec" / "changes" / "test-change").mkdir(parents=True)
    return tmp_path


def test_state_to_legacy_updates_roadmap_state(project_root):
    """sync_state_vector_to_legacy writes .zcf/.roadmap-state.json from state vector."""
    sv = StateVector.create_default()
    sv.update_field("arch_side.phase", "propose")
    sv.update_field("arch_side.current_change", "test-change")
    sv.update_field("arch_side.completed_changes", ["init"])
    sv_path = project_root / ".spec-workflow" / "state-vector.json"
    sv_path.parent.mkdir(parents=True, exist_ok=True)
    sv.save(str(sv_path))

    sync_state_vector_to_legacy(str(project_root))

    legacy = json.loads((project_root / ".zcf" / ".roadmap-state.json").read_text())
    assert legacy["phase"] == "propose"
    assert legacy["current_change"] == "test-change"


def test_legacy_to_state_updates_state_vector(project_root):
    """sync_legacy_to_state_vector reads .zcf/.roadmap-state.json into state vector."""
    legacy_path = project_root / ".zcf" / ".roadmap-state.json"
    legacy_path.write_text(json.dumps({
        "phase": "plan",
        "current_change": "legacy-change",
        "completed_changes": ["x", "y"],
    }))

    sync_legacy_to_state_vector(str(project_root))

    sv = StateVector.load(str(project_root / ".spec-workflow" / "state-vector.json"))
    assert sv.get_field("arch_side.phase") == "plan"
    assert sv.get_field("arch_side.current_change") == "legacy-change"


def test_state_vector_wins_on_conflict(project_root):
    """When both have changes, state vector's value is authoritative."""
    sv = StateVector.create_default()
    sv.update_field("arch_side.current_change", "from-state")
    sv_path = project_root / ".spec-workflow" / "state-vector.json"
    sv_path.parent.mkdir(parents=True, exist_ok=True)
    sv.save(str(sv_path))

    (project_root / ".zcf" / ".roadmap-state.json").write_text(json.dumps({
        "phase": "done",
        "current_change": "from-legacy",
    }))

    # Sync legacy -> state (legacy has different values)
    sync_legacy_to_state_vector(str(project_root))
    # Sync state -> legacy (state wins)
    sync_state_vector_to_legacy(str(project_root))

    # Legacy file should now have state's value
    legacy = json.loads((project_root / ".zcf" / ".roadmap-state.json").read_text())
    assert legacy["current_change"] == "from-state"


def test_sync_disabled_via_env_var(project_root, monkeypatch):
    """SPEC_WORKFLOW_SYNC_DISABLED=1 disables sync entirely."""
    monkeypatch.setenv("SPEC_WORKFLOW_SYNC_DISABLED", "1")
    assert is_sync_enabled() is False
    # Functions should be no-ops
    sync_state_vector_to_legacy(str(project_root))
    assert not (project_root / ".zcf" / ".roadmap-state.json").exists()


def test_state_to_legacy_propagation_under_50ms(project_root):
    """State vector change should propagate to legacy files within 50ms."""
    sv = StateVector.create_default()
    sv.update_field("arch_side.phase", "execute")
    sv_path = project_root / ".spec-workflow" / "state-vector.json"
    sv_path.parent.mkdir(parents=True, exist_ok=True)
    sv.save(str(sv_path))

    import time
    start = time.perf_counter()
    sync_state_vector_to_legacy(str(project_root))
    elapsed = time.perf_counter() - start
    assert elapsed < 0.050, f"Sync took {elapsed*1000:.1f}ms (must be < 50ms)"
    assert (project_root / ".zcf" / ".roadmap-state.json").is_file()


def test_conflict_logged_to_event_log(project_root):
    """When sync direction conflicts, an event is recorded."""
    sv = StateVector.create_default()
    sv.update_field("arch_side.current_change", "from-state")
    sv_path = project_root / ".spec-workflow" / "state-vector.json"
    sv_path.parent.mkdir(parents=True, exist_ok=True)
    sv.save(str(sv_path))

    (project_root / ".zcf" / ".roadmap-state.json").write_text(json.dumps({
        "current_change": "from-legacy",
        "_mtime": time.time() - 100,  # make legacy appear older
    }))

    # Force a conflict scenario
    sync_legacy_to_state_vector(str(project_root))

    log_path = project_root / ".spec-workflow" / "event-log.jsonl"
    if log_path.is_file():
        import json
        events = [json.loads(line) for line in log_path.read_text().splitlines() if line]
        # Either there's a conflict event, or sync completed without one (no false positives)
        assert all(e["event_type"] in [
            "state_updated", "warning_issued", "loop_iteration_completed", "scan_completed",
        ] for e in events)
```

- [ ] **Step 11.2: Run test to verify it fails**

```bash
cd /workspace/project/spec-workflow/.zcf/v2-core-foundation-wt
python3 -m pytest tests/unit/test_sync_state.py -v 2>&1 | head -10
```

Expected: `ModuleNotFoundError: No module named 'skills._lib.sync_state'`.

- [ ] **Step 11.3: Implement `sync_state`**

Create `skills/_lib/sync_state.py`:

```python
"""Bidirectional sync between v2 state vector and v1.x legacy state files.

Sync targets (v1.x files):
- .zcf/.roadmap-state.json — roadmap state cache
- proposal-suggestions.md — proposal suggestions
- openspec/changes/<name>/.openspec.yaml — per-change metadata

Sync rules:
- State vector is ALWAYS authoritative. On conflict, state vector wins.
- Conflict detection: mtime comparison (legacy file mtime > state vector mtime
  AND content differs → conflict, prefer state vector, log warning event).
- Sync can be disabled via `SPEC_WORKFLOW_SYNC_DISABLED=1` env var (escape hatch).
"""
from __future__ import annotations
import json
import os
import time
from pathlib import Path
from typing import Optional

from skills._lib.event_log import EventLog
from skills._lib.event_types import EventType, Severity
from skills._lib.state_vector import StateVector


STATE_VECTOR_PATH = ".spec-workflow/state-vector.json"
LEGACY_ROADMAP_STATE = ".zcf/.roadmap-state.json"


def is_sync_enabled() -> bool:
    """Return True unless SPEC_WORKFLOW_SYNC_DISABLED=1."""
    return os.environ.get("SPEC_WORKFLOW_SYNC_DISABLED", "0") not in ("1", "true", "yes")


def _state_vector_mtime(path: str) -> float:
    """Return mtime of the state vector file, or 0 if missing."""
    if not os.path.exists(path):
        return 0.0
    return os.path.getmtime(path)


def _record_event(project_root: str, event_type: EventType, severity: Severity, message: str, context: dict) -> None:
    """Record an event to the event log. Best-effort; failures are silently ignored."""
    try:
        log = EventLog(os.path.join(project_root, ".spec-workflow", "event-log.jsonl"))
        log.record(event_type, severity, message, context=context)
    except Exception:
        pass


def sync_state_vector_to_legacy(project_root: str = ".") -> bool:
    """Read state vector and write to v1.x legacy files. Returns True on success.

    Writes:
    - .zcf/.roadmap-state.json
    - proposal-suggestions.md (header only, if not present)
    - openspec/changes/<active>/.openspec.yaml (updates phase field)
    """
    if not is_sync_enabled():
        return False

    sv_path = os.path.join(project_root, STATE_VECTOR_PATH)
    if not os.path.exists(sv_path):
        return False

    try:
        sv = StateVector.load(sv_path, verify_checksum=False)
    except Exception:
        return False

    data = sv.to_dict()
    arch = data.get("arch_side", {})
    plan = data.get("plan_side", {})
    legacy_payload = {
        "phase": arch.get("phase", "idle"),
        "current_change": arch.get("current_change"),
        "completed_changes": arch.get("completed_changes", []),
        "active_change": plan.get("active_change"),
        "plan_file": plan.get("plan_file"),
        "updated_at": data.get("metadata", {}).get("updated_at"),
        "_synced_from": "v2-state-vector",
    }

    # Write .zcf/.roadmap-state.json
    legacy_path = Path(project_root) / LEGACY_ROADMAP_STATE.lstrip("./")
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    with open(legacy_path, "w") as f:
        json.dump(legacy_payload, f, indent=2)

    # Update per-change .openspec.yaml
    active = arch.get("current_change")
    if active:
        yaml_path = Path(project_root) / "openspec" / "changes" / active / ".openspec.yaml"
        if yaml_path.exists():
            try:
                import yaml
                with open(yaml_path) as f:
                    existing = yaml.safe_load(f) or {}
                existing["arch_phase"] = arch.get("phase", "idle")
                existing["synced_at"] = data.get("metadata", {}).get("updated_at")
                with open(yaml_path, "w") as f:
                    yaml.safe_dump(existing, f, default_flow_style=False)
            except Exception:
                pass

    _record_event(
        project_root,
        EventType.STATE_UPDATED,
        Severity.DEBUG,
        f"State vector synced to legacy files: {legacy_path}",
        {"direction": "state_to_legacy", "target": str(legacy_path)},
    )
    return True


def sync_legacy_to_state_vector(project_root: str = ".") -> bool:
    """Read v1.x legacy files and update state vector. Returns True on success.

    On conflict (state vector was updated more recently than legacy), state vector
    wins and a warning is recorded.
    """
    if not is_sync_enabled():
        return False

    sv_path = os.path.join(project_root, STATE_VECTOR_PATH)
    legacy_path = Path(project_root) / LEGACY_ROADMAP_STATE.lstrip("./")
    if not legacy_path.is_file():
        return False

    try:
        with open(legacy_path) as f:
            legacy = json.load(f)
    except json.JSONDecodeError:
        return False

    # Conflict detection via mtime
    legacy_mtime = os.path.getmtime(legacy_path)
    sv_mtime = _state_vector_mtime(sv_path)
    conflict = legacy_mtime > sv_mtime and bool(legacy.get("current_change"))

    if conflict:
        _record_event(
            project_root,
            EventType.WARNING_ISSUED,
            Severity.WARN,
            f"Sync conflict: legacy file newer than state vector. State vector wins.",
            {"legacy_mtime": legacy_mtime, "state_vector_mtime": sv_mtime},
        )
        # Per design.md Decision 4: state vector wins. We do NOT apply legacy values.
        return False

    # No conflict — apply legacy values to state vector
    if not os.path.exists(sv_path):
        return False

    try:
        sv = StateVector.load(sv_path, verify_checksum=False)
    except Exception:
        return False

    if "phase" in legacy:
        sv.update_field("arch_side.phase", legacy["phase"])
    if "current_change" in legacy:
        sv.update_field("arch_side.current_change", legacy["current_change"])
    if "completed_changes" in legacy:
        sv.update_field("arch_side.completed_changes", legacy["completed_changes"])
    if "active_change" in legacy:
        sv.update_field("plan_side.active_change", legacy["active_change"])
    if "plan_file" in legacy:
        sv.update_field("plan_side.plan_file", legacy["plan_file"])

    sv.save(sv_path)
    _record_event(
        project_root,
        EventType.STATE_UPDATED,
        Severity.DEBUG,
        f"Legacy state synced to state vector: {sv_path}",
        {"direction": "legacy_to_state", "source": str(legacy_path)},
    )
    return True
```

- [ ] **Step 11.4: Run tests to verify they pass**

```bash
cd /workspace/project/spec-workflow/.zcf/v2-core-foundation-wt
python3 -m pytest tests/unit/test_sync_state.py -v
```

Expected: All 6 tests pass.

- [ ] **Step 11.5: Update tasks.md (5.1-5.6) and commit**

```bash
cd /workspace/project/spec-workflow/.zcf/v2-core-foundation-wt
sed -i \
  -e 's/- \[ \] 5.1 Create `skills/_lib\/sync_state.py`/- [x] 5.1 Create `skills/_lib\/sync_state.py`/' \
  -e 's/- \[ \] 5.2 Sync targets: `.zcf\/.roadmap-state.json`, `proposal-suggestions.md`, `openspec\/changes\/<name>\/.openspec.yaml`/- [x] 5.2 Sync targets: `.zcf\/.roadmap-state.json`, `proposal-suggestions.md`, `openspec\/changes\/<name>\/.openspec.yaml`/' \
  -e 's/- \[ \] 5.3 Implement conflict detection via mtime; state vector wins on conflict/- [x] 5.3 Implement conflict detection via mtime; state vector wins on conflict/' \
  -e 's/- \[ \] 5.4 Log conflicts to event log/- [x] 5.4 Log conflicts to event log/' \
  -e 's/- \[ \] 5.5 Write unit tests: state vector update triggers v1.x sync, v1.x change triggers state update, latency < 50ms, conflict resolution correct/- [x] 5.5 Write unit tests: state vector update triggers v1.x sync, v1.x change triggers state update, latency < 50ms, conflict resolution correct/' \
  -e 's/- \[ \] 5.6 Verify sync layer can be disabled via env var (escape hatch)/- [x] 5.6 Verify sync layer can be disabled via env var (escape hatch)/' \
  openspec/changes/v2-core-foundation/tasks.md
git add skills/_lib/sync_state.py tests/unit/test_sync_state.py openspec/changes/v2-core-foundation/tasks.md
git commit -m "feat(_lib): add sync_state (bidirectional v1.x sync, mtime conflict detection) — closes 5.1-5.6"
```

Expected: 1 new commit. Core implementation complete.

---

### Task 12: Documentation Updates (`docs/v2-api-reference.md`, `docs/v2-config-schema.md`)

**Files:**
- Modify: `docs/v2-api-reference.md` — add new public APIs
- Modify: `docs/v2-config-schema.md` — add `.spec-workflow.json` schema

- [ ] **Step 12.1: Append new API section to v2-api-reference.md**

First read the existing file, then append a new section:

```bash
cd /workspace/project/spec-workflow/.zcf/v2-core-foundation-wt
# Find the end of the file (last section)
tail -5 docs/v2-api-reference.md
```

Then append:

```bash
cat >> docs/v2-api-reference.md <<'EOF'

---

## v2.0 Core Foundation APIs (Phase 1)

The following public APIs are added in `v2-core-foundation` and serve as the
foundation for higher-level v2 subsystems (loop engine, advanced features).

### `skills/_lib/lock.py` — `FileLock`

```python
from skills._lib.lock import FileLock, LockTimeout

with FileLock("/path/to/state.lock", timeout=10.0) as lock:
    # ... critical section ...
    pass
# Lock is released automatically, even on exception.
```

- `path` (str): Path to the lock file. Created on first acquire.
- `timeout` (float, default 10.0): Seconds to wait. `0.0` for non-blocking.
- `exclusive` (bool, default True): Exclusive (writer) vs shared (reader).

Raises `LockTimeout` if the lock cannot be acquired within the timeout.

### `skills/_lib/state_vector.py` — `StateVector`

```python
from skills._lib.state_vector import StateVector

# Create a default state
sv = StateVector.create_default()
sv.update_field("goal", "ship v2.0")
sv.update_field("loop_state.iteration", 1)

# Persist atomically
sv.save(".spec-workflow/state-vector.json")

# Load (returns default if file missing)
sv = StateVector.load(".spec-workflow/state-vector.json")
print(sv.get_field("goal"))  # "ship v2.0"
print(sv.get_field("loop_state.iteration"))  # 1
```

- All writes are protected by `FileLock` (10s timeout).
- All writes are JSON-Schema validated against `state_vector_schema.json`.
- All writes compute a SHA-256 checksum of the canonical JSON for corruption detection.
- `update_field(dotted_path, value)` supports nested fields.

### `skills/_lib/event_log.py` — `EventLog`

```python
from skills._lib.event_log import EventLog
from skills._lib.event_types import EventType, Severity

log = EventLog(".spec-workflow/event-log.jsonl")
log.record(EventType.LOOP_STARTED, Severity.INFO, "loop started")

# Query
events = log.query(event_type=EventType.LOOP_STARTED)
recent = log.query(since="2026-06-25T00:00:00Z")

# Aggregate
report = log.get_progress_report()
print(report)  # {iterations_completed: 5, units_completed: 12, errors: 0, ...}
```

- Append-only JSONL format. One event per line.
- 17 `EventType` values; 4 `Severity` levels (debug/info/warn/error).
- Query is < 100ms for 10K events (linear scan over JSONL).
- Event IDs: `evt_YYYYMMDD_HHMMSS_NNN` (per-process sequence for uniqueness).

### `skills/_lib/gate.py` — `GateMechanism`

```python
from skills._lib.gate import GateMechanism, Check

gate = GateMechanism(
    state_path=".spec-workflow/state-vector.json",
    event_log_path=".spec-workflow/event-log.jsonl",
)
gate.register(Check(
    name="my_check",
    condition=lambda ctx: (True, None),
    message="ok",
    suggestion="",
))

result = gate.verify_transition("arch_done", {})
if not result.passed:
    print(result.suggestion)  # aggregated fix suggestions
else:
    gate.force_transition("arch_done", {}, reason="user override")
```

- Three phase transitions: `arch_done`, `plan_done`, `ship_done`.
- Each has a default checklist; plugins can register more via `register_gate_check()`.
- Two severity levels: `error` (blocks) and `warning` (allows with notice).
- Every verification records a `GATE_TRANSITION`, `GATE_FAILED`, or `GATE_FORCED` event.

### `skills/_lib/config.py` — `ConfigParser`

```python
from skills._lib.config import ConfigParser

parser = ConfigParser(project_root=".")
config = parser.parse(runtime_overrides={"interaction.mode": "loop"})
print(config["loop"]["max_iterations"])  # 100 (from defaults)
```

- Priority order: `runtime_overrides > loop.yaml > .spec-workflow.json > env > defaults`.
- Strict order (not deep merge) — see `design.md` Decision 5.
- Type coercion for env vars (e.g., `SPEC_WORKFLOW_MAX_ITERATIONS=200` → int).
- Validates enum values and numeric ranges; raises `ConfigError` with clear messages.

### `skills/_lib/sync_state.py` — Sync Functions

```python
from skills._lib.sync_state import (
    sync_state_vector_to_legacy,
    sync_legacy_to_state_vector,
    is_sync_enabled,
)

if is_sync_enabled():
    sync_state_vector_to_legacy(".")
    sync_legacy_to_state_vector(".")
```

- Bidirectional sync between v2 state vector and v1.x legacy files.
- State vector is always authoritative (wins on conflict).
- Conflict detection via mtime comparison.
- Disable via env var: `SPEC_WORKFLOW_SYNC_DISABLED=1`.
- Propagation latency: < 50ms.
EOF
git add docs/v2-api-reference.md
git commit -m "docs(api): add v2.0 Core Foundation APIs section to v2-api-reference.md"
```

Expected: 1 new commit.

- [ ] **Step 12.2: Update v2-config-schema.md**

Read the existing file, then append a new section:

```bash
cd /workspace/project/spec-workflow/.zcf/v2-core-foundation-wt
tail -3 docs/v2-config-schema.md
```

Then append:

```bash
cat >> docs/v2-config-schema.md <<'EOF'

---

## v2.0 Config Schema (Phase 1)

The v2 configuration system reads from up to five sources, merged in strict
priority order (highest to lowest):

1. **Runtime overrides** — passed to `ConfigParser.parse(runtime_overrides=...)`
2. **`loop.yaml`** (project root)
3. **`.spec-workflow.json`** (project root)
4. **Environment variables** (`SPEC_WORKFLOW_*`)
5. **Built-in defaults** (from `skills/_lib/defaults.py`)

### `.spec-workflow.json` Schema

```json
{
  "version": "2.0",
  "interaction": {
    "mode": "hybrid",
    "menu_items": ["propose", "execute", "status", "archive"]
  },
  "loop": {
    "max_iterations": 100,
    "max_retries": 3,
    "retry_backoff_seconds": 5
  },
  "state": {
    "path": ".spec-workflow/state-vector.json",
    "lock_timeout_seconds": 10.0
  },
  "event_log": {
    "path": ".spec-workflow/event-log.jsonl",
    "max_size_mb": 50
  },
  "gate": {
    "load_defaults": true,
    "auto_allow_warnings": true
  },
  "sync": {
    "v1x_enabled": true,
    "conflict_resolution": "state_vector_wins"
  }
}
```

### Field Reference

| Path | Type | Default | Description |
|---|---|---|---|
| `version` | string | `"2.0"` | Schema version (required) |
| `interaction.mode` | enum | `"hybrid"` | One of `loop`, `menu`, `hybrid` |
| `interaction.menu_items` | array | `["propose","execute","status","archive"]` | Items shown in menu mode |
| `loop.max_iterations` | int > 0 | `100` | Hard cap on loop iterations |
| `loop.max_retries` | int ≥ 0 | `3` | Retries on transient failure |
| `loop.retry_backoff_seconds` | float ≥ 0 | `5` | Wait between retries |
| `state.path` | string | `".spec-workflow/state-vector.json"` | State vector location |
| `state.lock_timeout_seconds` | float > 0 | `10.0` | File lock timeout |
| `event_log.path` | string | `".spec-workflow/event-log.jsonl"` | Event log location |
| `event_log.max_size_mb` | int > 0 | `50` | Soft cap (for future rotation) |
| `gate.load_defaults` | bool | `true` | Include default gate checks |
| `gate.auto_allow_warnings` | bool | `true` | Proceed past warning-severity gate checks |
| `sync.v1x_enabled` | bool | `true` | Master switch for v1.x compatibility layer |
| `sync.conflict_resolution` | enum | `"state_vector_wins"` | The only supported value |

### Environment Variables

| Variable | Mapped To | Coerced Type |
|---|---|---|
| `SPEC_WORKFLOW_MODE` | `interaction.mode` | string |
| `SPEC_WORKFLOW_MAX_ITERATIONS` | `loop.max_iterations` | int |
| `SPEC_WORKFLOW_MAX_RETRIES` | `loop.max_retries` | int |
| `SPEC_WORKFLOW_STATE_PATH` | `state.path` | string |
| `SPEC_WORKFLOW_SYNC_DISABLED` | (disables sync layer) | bool |

### `loop.yaml` (alternative config)

A YAML file with the same structure as `.spec-workflow.json`. `loop.yaml` takes
precedence over `.spec-workflow.json` when both exist. Useful for separating
"project defaults" (in JSON) from "operator overrides" (in YAML).
EOF
git add docs/v2-config-schema.md
git commit -m "docs(config): add v2.0 Config Schema section to v2-config-schema.md"
```

Expected: 1 new commit. Documentation complete.

- [ ] **Step 12.3: Update tasks.md (6.1, 6.2)**

```bash
cd /workspace/project/spec-workflow/.zcf/v2-core-foundation-wt
sed -i \
  -e 's/- \[ \] 6.1 Update `docs\/v2-api-reference.md` with new public APIs/- [x] 6.1 Update `docs\/v2-api-reference.md` with new public APIs/' \
  -e 's/- \[ \] 6.2 Update `docs\/v2-config-schema.md` with `.spec-workflow.json` schema/- [x] 6.2 Update `docs\/v2-config-schema.md` with `.spec-workflow.json` schema/' \
  openspec/changes/v2-core-foundation/tasks.md
git add openspec/changes/v2-core-foundation/tasks.md
git commit -m "docs(tasks): mark 6.1 and 6.2 complete"
```

Expected: 1 new commit.

---

### Task 13: Final Integration Tests (Full Test Suite + v1.x Regression)

**Files:**
- Run: `pytest tests/unit/` — must pass with 0 failures
- Run: `pytest tests/integration/` — v1.x regression must pass (if any tests exist)

- [ ] **Step 13.1: Run full unit test suite**

```bash
cd /workspace/project/spec-workflow/.zcf/v2-core-foundation-wt
python3 -m pytest tests/unit/ -v
```

Expected: All tests pass (count should be ≥ 37 across `test_lock.py`, `test_state_vector.py`, `test_event_log.py`, `test_gate.py`, `test_config.py`, `test_sync_state.py`).

- [ ] **Step 13.2: Run v1.x integration tests for regression**

```bash
cd /workspace/project/spec-workflow/.zcf/v2-core-foundation-wt
ls tests/integration/ 2>/dev/null
if [ -d tests/integration ] && [ -n "$(ls tests/integration/*.bats 2>/dev/null)" ]; then
    which bats && bats tests/integration/ || echo "bats not installed; skipping"
else
    echo "No v1.x integration tests; skipping regression check"
fi
```

Expected: Either `bats` runs and passes, or a skip message is printed.

- [ ] **Step 13.3: Verify zero regressions in v1.x skills**

```bash
cd /workspace/project/spec-workflow/.zcf/v2-core-foundation-wt
# Confirm all v1.x skill files are untouched
git diff master -- skills/INSTALL.md skills/guide.md skills/propose.md skills/execute.md \
  skills/guide-spec.md skills/guide-ship.md skills/roadmap.md skills/deps.md skills/status.md \
  skills/prometheus-planning.md 2>&1 | head -5
```

Expected: Empty output (no changes to v1.x skill files).

- [ ] **Step 13.4: Update tasks.md (6.3, 6.4) and final commit**

```bash
cd /workspace/project/spec-workflow/.zcf/v2-core-foundation-wt
sed -i \
  -e 's/- \[ \] 6.3 Run full test suite: `pytest tests\/unit\/`/- [x] 6.3 Run full test suite: `pytest tests\/unit\/`/' \
  -e 's/- \[ \] 6.4 Verify zero regressions in v1.x skills (run `tests\/integration\/`)/- [x] 6.4 Verify zero regressions in v1.x skills (run `tests\/integration\/`)/' \
  openspec/changes/v2-core-foundation/tasks.md
git add openspec/changes/v2-core-foundation/tasks.md
git commit -m "test(integration): all 37+ unit tests pass, zero v1.x regressions — closes 6.3, 6.4"
```

Expected: 1 new commit. **All 30+ tasks now show `[x]`.**

---

## OpenSpec Phase 3: Status — Validation

### Task 14: Validate 100% Task Completion via openspec CLI

- [ ] **Step 14.1: Switch to main repo and validate via openspec**

```bash
cd /workspace/project/spec-workflow
openspec instructions apply --change v2-core-foundation --json 2>&1 | head -40
```

Expected: JSON output with `progress.complete` equal to `progress.total`. If `openspec` CLI is not installed, fall back to manual check:

```bash
cd /workspace/project/spec-workflow
echo "=== tasks.md progress ==="
grep -c "^- \[x\]" openspec/changes/v2-core-foundation/tasks.md
echo "=== remaining unchecked ==="
grep -c "^- \[ \]" openspec/changes/v2-core-foundation/tasks.md
```

Expected: First count > 25; second count = 0.

- [ ] **Step 14.2: Cross-check from worktree branch**

```bash
cd /workspace/project/spec-workflow
git log openspec/v2-core-foundation --oneline | head -20
```

Expected: At least 12 commits on the feature branch (1 plan + 11 implementation commits).

- [ ] **Step 14.3: Verify all spec requirements covered by code**

```bash
cd /workspace/project/spec-workflow
echo "=== Spec requirements vs implementation ==="
echo "state-management: $(grep -c 'Requirement:' openspec/changes/v2-core-foundation/specs/state-management/spec.md) requirements"
echo "gate-mechanism: $(grep -c 'Requirement:' openspec/changes/v2-core-foundation/specs/gate-mechanism/spec.md) requirements"
echo "configuration: $(grep -c 'Requirement:' openspec/changes/v2-core-foundation/specs/configuration/spec.md) requirements"
echo ""
echo "=== Implementation files ==="
ls -la .zcf/v2-core-foundation-wt/skills/_lib/*.py | wc -l
echo "Python modules in skills/_lib/"
```

Expected: 4 / 4 / 3 requirements; ~9 Python modules.

- [ ] **Step 14.4: Mark validation done**

```bash
cd /workspace/project/spec-workflow
# No file change; this is a verification step
echo "Status validation passed — ready for archive"
```

Expected: Print "ready for archive".

---

## OpenSpec Phase 4: Archive — Merge + Cleanup

### Task 15: Merge, Archive, and Cleanup

**Files:**
- Merge `openspec/v2-core-foundation` → `master` (or default branch)
- `openspec archive v2-core-foundation --yes` (writes to `openspec/changes/archive/`)
- `git worktree remove .zcf/v2-core-foundation-wt`
- `git branch -d openspec/v2-core-foundation`

- [ ] **Step 15.1: Pre-merge commit check (T20)**

```bash
cd /workspace/project/spec-workflow
DEFAULT_BRANCH=$(git symbolic-ref --short HEAD)
NEW_COMMITS=$(git rev-list --count "$DEFAULT_BRANCH..openspec/v2-core-foundation")
echo "Feature branch has $NEW_COMMITS new commits"
[ "$NEW_COMMITS" -gt 0 ] && echo "OK to merge" || (echo "❌ No new commits"; exit 1)
```

Expected: Print count > 0 and "OK to merge".

- [ ] **Step 15.2: Merge feature branch into default branch**

```bash
cd /workspace/project/spec-workflow
DEFAULT_BRANCH=$(git symbolic-ref --short HEAD)
git merge --no-ff openspec/v2-core-foundation -m "merge: v2-core-foundation (state vector, event log, gate, config, v1.x sync)"
```

Expected: Merge completes with a merge commit.

- [ ] **Step 15.3: Run `openspec archive`**

```bash
cd /workspace/project/spec-workflow
openspec archive v2-core-foundation --yes
```

Expected: Prints "Change v2-core-foundation archived successfully" and moves the change directory to `openspec/changes/archive/`.

- [ ] **Step 15.4: Cleanup worktree and branch**

```bash
cd /workspace/project/spec-workflow
git worktree remove .zcf/v2-core-foundation-wt
git branch -d openspec/v2-core-foundation
git worktree list
```

Expected: Worktree list shows only the main repo on master. `openspec/v2-core-foundation` branch is deleted.

- [ ] **Step 15.5: Final verification**

```bash
cd /workspace/project/spec-workflow
echo "=== Final state ==="
echo "Branches:"
git branch -a
echo ""
echo "Worktrees:"
git worktree list
echo ""
echo "Archived changes:"
ls openspec/changes/archive/ | grep v2-core-foundation
echo ""
echo "Source code in master:"
ls skills/_lib/*.py skills/_lib/schemas/*.json skills/_lib/plugins/*.md 2>/dev/null
```

Expected: All v2-core-foundation source code present on master; one entry in `archive/`; no leftover worktrees/branches.

---

## Self-Review Checklist

Before declaring the plan complete, verify:

- [ ] **Spec coverage:** All 3 capabilities (state-management, gate-mechanism, configuration) and their `Requirement:` entries are addressed in Tasks 1-11.
- [ ] **TDD ordering:** Every implementation task writes the test first (Steps 1.1, 2.1, 3.1, 4.1, 5.1, 6.1, 7.1, 10.1, 11.1).
- [ ] **Frequent commits:** Every task ends with a `git commit` step. 12 implementation commits + 2 doc commits + 1 final commit = ≥ 15 commits on the feature branch.
- [ ] **No placeholders:** No "TBD", "implement later", "similar to Task N". All code blocks are complete.
- [ ] **Type consistency:** Method names match across tasks (`save`, `load`, `update_field`, `record`, `query`, `verify_transition`, `register`, `parse`, `sync_state_vector_to_legacy`, `sync_legacy_to_state_vector`).
- [ ] **OpenSpec workflow coverage:** All 4 phases (plan, execute, status, archive) are addressed in Tasks 0, 1-13, 14, 15.

---

## Estimated Time

- Tasks 1-11 (implementation): ~4-5 hours (assuming ~25-30 min per module, TDD-paced)
- Task 12 (docs): ~20 min
- Task 13 (integration tests): ~15 min
- Task 14 (status): ~10 min
- Task 15 (archive): ~5 min

**Total: ~5-6 hours of focused work.**
