# split-rddf-god-class Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the 507-line `RddfSessionCoordinator` god class in `skills/rddf-session/scripts/rddf_session.py` into 5 focused modules (types, store, commands, binding, facade) that preserve every public method signature and existing import path.

**Architecture:** The file already documents its own 3 responsibilities (Persistence, Commands, Binding) at lines 17-30. We extract each responsibility into its own module under a new `rddf_session/` subdirectory, then rewrite the original `rddf_session.py` as a thin facade that re-exports `RddfSessionCoordinator` and all public symbols from the submodules.

**Tech Stack:** Python 3.11+, fcntl (POSIX-only), json, pathlib

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/rddf-session/scripts/rddf_session/_types.py` | Enums (`RddfSessionState`), exceptions (`RddfSessionError`, `SchemaValidationError`, `ConflictError`), dataclass (`RddfSession`), constants, `_new_id()`/`_now()` helpers |
| `skills/rddf-session/scripts/rddf_session/_store.py` | `_read_unlocked()`, `_atomic_write()`, `_with_file_lock()` — file I/O + POSIX advisory locking |
| `skills/rddf-session/scripts/rddf_session/_commands.py` | `create_session`, `find_session`, `update_session_status`, `list_sessions`, `attach_change`, `detach_change`, `refresh_heartbeat`, `check_heartbeat_timeouts`, `archive_history`, `abandon`, `transfer_ownership` |
| `skills/rddf-session/scripts/rddf_session/_binding.py` | `find_current_binding`, `find_next_recommendation`, `detect_conflict` |
| `skills/rddf-session/scripts/rddf_session.py` (facade) | Rewrite: import from submodules, declare `RddfSessionCoordinator` delegating to each, re-export all public names |

### Tests

No new test files needed. The existing 24+10 tests must pass with zero modification since all public APIs are preserved.

---

### Task 1: Extract `_types.py`

**Files:**
- Create: `skills/rddf-session/scripts/rddf_session/_types.py`
- Modify: (none yet)

- [ ] **Step 1: Write the failing test — run existing tests after creating empty module**

Run: `python3 -m pytest tests/unit/test_rddf_session.py -x -q --tb=short`
Expected: PASS (import path unchanged, no new types yet)

- [ ] **Step 2: Create `rddf_session/` package + `_types.py`**

Create directory `skills/rddf-session/scripts/rddf_session/` and write `_types.py` with these contents from the original file:

```python
"""Type definitions and constants for rddf-session."""
from __future__ import annotations
import datetime
import enum
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

SCHEMA_PATH = ...  # (same relative path logic)
DEFAULT_HEARTBEAT_TIMEOUT_SECONDS = 30 * 60
HEARTBEAT_REFRESH_THRESHOLD_SECONDS = 5 * 60
LOCK_TIMEOUT_SECONDS = 5.0
_VALID_KINDS = ("stage_arch", "stage_plan", "stage_ship")
_VALID_STATES = ("active", "completed", "failed", "orphaned", "abandoned")
_TERMINAL_STATES = frozenset(("completed", "failed", "abandoned"))

class RddfSessionState(str, enum.Enum): ...
class RddfSessionError(Exception): ...
class SchemaValidationError(RddfSessionError): ...
class ConflictError(RddfSessionError): ...

def _new_id() -> str: ...
def _now() -> str: ...

@dataclass
class RddfSession: ...
```

Copy verbatim from lines 45-106 of the original file. Use `Path(__file__).resolve().parent.parent / "schemas" / ...` for `SCHEMA_PATH` (two levels up from `_types.py`).

- [ ] **Step 3: Run existing tests to verify no regression**

Run: `python3 -m pytest tests/ -x -q --tb=short -k "rddf_session" 2>&1 | tail -5`
Expected: all pass (nothing imports from `_types` yet)

- [ ] **Step 4: Commit**

```bash
git add skills/rddf-session/scripts/rddf_session/__init__.py skills/rddf-session/scripts/rddf_session/_types.py
git commit -m "extract(rddf-session): create _types.py with enums, exceptions, dataclass, constants"
```

---

### Task 2: Extract `_store.py`

**Files:**
- Create: `skills/rddf-session/scripts/rddf_session/_store.py`
- Test: existing tests (import path unchanged yet)

- [ ] **Step 1: Write the failing test**

Run: `python3 -m pytest tests/unit/test_rddf_session.py -x -q --tb=short`
Expected: PASS (no behavioral change yet)

- [ ] **Step 2: Create `_store.py` — implement `RddfSessionStore` class with file I/O**

```python
"""File-backed session persistence with advisory locking."""
from __future__ import annotations
import fcntl
import json
import pathlib
from typing import Any, Callable

from ._types import RddfSessionError, SCHEMA_PATH

class RddfSessionStore:
    def __init__(self, sessions_file: str):
        self._sessions_file = pathlib.Path(sessions_file)
        self._lock_file = self._sessions_file.with_suffix(".lock")

    def read_unlocked(self) -> dict: ...   # was _read_unlocked
    def atomic_write(self, data: dict) -> None: ...  # was _atomic_write
    def with_file_lock(self, fn: Callable) -> Any: ...  # was _with_file_lock
```

Copy the bodies of `_read_unlocked` (lines 117-122), `_atomic_write` (lines 124-128), and `_with_file_lock` (lines 130-148) from the original. Make them public methods (no underscore prefix) since they're the store's API.

The `_atomic_write` body delegates to `skills._lib.core.atomic_write.atomic_write_json` — keep that import.

- [ ] **Step 3: Run existing tests**

Run: `python3 -m pytest tests/unit/test_rddf_session.py -x -q --tb=short`
Expected: PASS (store exists but isn't imported by any test yet)

- [ ] **Step 4: Commit**

```bash
git add skills/rddf-session/scripts/rddf_session/_store.py
git commit -m "extract(rddf-session): create _store.py with file I/O and advisory locking"
```

---

### Task 3: Extract `_commands.py`

**Files:**
- Create: `skills/rddf-session/scripts/rddf_session/_commands.py`
- Test: existing tests (no import change yet)

- [ ] **Step 1: Write the failing test**

Run: `python3 -m pytest tests/unit/test_rddf_session.py -x -q --tb=short`
Expected: PASS

- [ ] **Step 2: Create `_commands.py` — implement `RddfSessionCommands` class**

```python
"""Session lifecycle commands (CRUD + transitions)."""
from __future__ import annotations
from typing import Any, Dict, List, Optional

from ._types import RddfSession, RddfSessionError, _new_id, _now, _VALID_KINDS, _VALID_STATES, _TERMINAL_STATES
from ._store import RddfSessionStore

class RddfSessionCommands:
    def __init__(self, store: RddfSessionStore):
        self._store = store

    def create_session(self, kind, owner, goal, parent_session_id=None, context_pointer=None) -> str: ...
    def find_session(self, session_id) -> Optional[RddfSession]: ...
    def update_session_status(self, session_id, new_state, end_reason=None) -> None: ...
    def list_sessions(self, kind=None) -> List[RddfSession]: ...
    def attach_change(self, session_id, change_name) -> None: ...
    def detach_change(self, session_id, change_name) -> None: ...
    def refresh_heartbeat(self, session_id) -> None: ...
    def check_heartbeat_timeouts(self) -> List[str]: ...
    def abandon(self, session_id) -> None: ...
    def transfer_ownership(self, session_id, new_owner) -> None: ...
    def archive_history(self, keep=20) -> int: ...
```

Copy each method body from the original file (lines 152-506), replacing `self._read_unlocked()` with `self._store.read_unlocked()`, `self._atomic_write(data)` with `self._store.atomic_write(data)`, and `self._with_file_lock(fn)` with `self._store.with_file_lock(fn)`.

- [ ] **Step 3: Run existing tests**

Run: `python3 -m pytest tests/unit/test_rddf_session.py -x -q --tb=short`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add skills/rddf-session/scripts/rddf_session/_commands.py
git commit -m "extract(rddf-session): create _commands.py with lifecycle operations"
```

---

### Task 4: Extract `_binding.py`

**Files:**
- Create: `skills/rddf-session/scripts/rddf_session/_binding.py`
- Test: existing tests

- [ ] **Step 1: Run tests to confirm baseline**

Run: `python3 -m pytest tests/unit/test_rddf_session.py -x -q --tb=short`
Expected: PASS

- [ ] **Step 2: Create `_binding.py` — implement `RddfSessionBinding` class**

```python
"""Session-to-OpenCode-session binding (ADR-0017 §3)."""
from __future__ import annotations
from typing import Dict, Any, List, Optional, Callable

from ._types import RddfSession, RddfSessionError, _VALID_KINDS, _VALID_STATES, _now
from ._store import RddfSessionStore

class RddfSessionBinding:
    def __init__(self, store: RddfSessionStore):
        self._store = store

    def find_current_binding(self, owner_opencode_session_id: str) -> Optional[RddfSession]: ...
    def find_next_recommendation(self, owner_opencode_session_id=None) -> Optional[RddfSession]: ...
    def detect_conflict(self, kind, owner_opencode_session_id) -> Optional[RddfSession]: ...
```

Copy method bodies from the original file: `find_current_binding` (lines 220-240), `find_next_recommendation` (lines 244-268), `detect_conflict` (lines 408-429). Replace `self._read_unlocked()` with `self._store.read_unlocked()` and `self._with_file_lock(fn)` with `self._store.with_file_lock(fn)`.

- [ ] **Step 3: Run tests**

Run: `python3 -m pytest tests/unit/test_rddf_session.py -x -q --tb=short`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add skills/rddf-session/scripts/rddf_session/_binding.py
git commit -m "extract(rddf-session): create _binding.py with session binding and conflict detection"
```

---

### Task 5: Rewrite `rddf_session.py` as facade

**Files:**
- Modify: `skills/rddf-session/scripts/rddf_session.py` — rewrite as facade that delegates to submodules
- Test: all 24+10 tests

- [ ] **Step 1: Verify baseline tests pass**

Run: `python3 -m pytest tests/ -x -q --tb=short -k "rddf" 2>&1 | tail -5`
Expected: all pass (current state)

- [ ] **Step 2: Rewrite `rddf_session.py` as a thin facade**

```python
"""RddfSessionCoordinator — facade over internal modules.

This file is now the public API surface. All implementation lives in
rddf_session/ submodules (types, store, commands, binding).
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

from .rddf_session._types import (
    RddfSession,
    RddfSessionError,
    SchemaValidationError,
    ConflictError,
    RddfSessionState,
    SCHEMA_PATH,
    DEFAULT_HEARTBEAT_TIMEOUT_SECONDS,
    HEARTBEAT_REFRESH_THRESHOLD_SECONDS,
    _VALID_KINDS,
    _VALID_STATES,
    _TERMINAL_STATES,
    _new_id,
    _now,
)
from .rddf_session._store import RddfSessionStore
from .rddf_session._commands import RddfSessionCommands
from .rddf_session._binding import RddfSessionBinding


class RddfSessionCoordinator:
    """Persist rddf-session lifecycle to .rddf/state/sessions.json."""

    def __init__(self, sessions_file: str):
        self._store = RddfSessionStore(sessions_file)
        self._commands = RddfSessionCommands(self._store)
        self._binding = RddfSessionBinding(self._store)

    # File I/O (delegated)
    @property
    def _sessions_file(self):
        return self._store._sessions_file

    def _with_file_lock(self, fn):
        return self._store.with_file_lock(fn)

    def _read_unlocked(self) -> dict:
        return self._store.read_unlocked()

    def _atomic_write(self, data: dict) -> None:
        self._store.atomic_write(data)

    # Commands (delegated)
    def create_session(self, kind, owner, goal, parent_session_id=None, context_pointer=None):
        return self._commands.create_session(kind, owner, goal, parent_session_id, context_pointer)

    def find_session(self, session_id):
        return self._commands.find_session(session_id)

    def update_session_status(self, session_id, new_state, end_reason=None):
        self._commands.update_session_status(session_id, new_state, end_reason)

    def list_sessions(self, kind=None):
        return self._commands.list_sessions(kind)

    def attach_change(self, session_id, change_name):
        self._commands.attach_change(session_id, change_name)

    def detach_change(self, session_id, change_name):
        self._commands.detach_change(session_id, change_name)

    def refresh_heartbeat(self, session_id):
        self._commands.refresh_heartbeat(session_id)

    def check_heartbeat_timeouts(self):
        return self._commands.check_heartbeat_timeouts()

    def abandon(self, session_id):
        self._commands.abandon(session_id)

    def transfer_ownership(self, session_id, new_owner):
        self._commands.transfer_ownership(session_id, new_owner)

    def archive_history(self, keep=20):
        return self._commands.archive_history(keep)

    # Binding (delegated)
    def find_current_binding(self, owner_opencode_session_id):
        return self._binding.find_current_binding(owner_opencode_session_id)

    def find_next_recommendation(self, owner_opencode_session_id=None):
        return self._binding.find_next_recommendation(owner_opencode_session_id)

    def detect_conflict(self, kind, owner_opencode_session_id):
        return self._binding.detect_conflict(kind, owner_opencode_session_id)
```

**Check**: Every public method from the original `RddfSessionCoordinator` is preserved:
- `create_session` ✓ `find_session` ✓ `update_session_status` ✓ `list_sessions` ✓
- `attach_change` ✓ `detach_change` ✓ `refresh_heartbeat` ✓
- `check_heartbeat_timeouts` ✓ `abandon` ✓ `transfer_ownership` ✓ `archive_history` ✓
- `find_current_binding` ✓ `find_next_recommendation` ✓ `detect_conflict` ✓

The private methods `_with_file_lock`, `_read_unlocked`, `_atomic_write`, `_sessions_file` are kept as delegation properties for backward compatibility (some importers may reference them).

- [ ] **Step 3: Run all tests**

Run: `python3 -m pytest tests/ -x -q --tb=short 2>&1 | tail -10`
Expected: all tests pass (24+10)

If any test fails:
1. Check if the test accesses a private method that changed
2. Add the missing delegation property
3. Re-run

- [ ] **Step 4: Import verification — scan for direct internal imports**

Run: `GIT_MASTER=1 grep -rn "rddf_session.RddfSession\|from skills.*rddf_session import" skills/ tests/`

Expected: all imports reference `RddfSessionCoordinator` from `rddf_session.py` (the facade), or `from skills.rddf_session.scripts.rddf_session import ...` (which resolves to the facade). No imports from the submodules.

- [ ] **Step 5: Commit**

```bash
git add skills/rddf-session/scripts/rddf_session.py skills/rddf-session/scripts/rddf_session/_commands.py skills/rddf-session/scripts/rddf_session/_binding.py skills/rddf-session/scripts/rddf_session/_store.py skills/rddf-session/scripts/rddf_session/_types.py
git commit -m "refactor(rddf-session): rewrite rddf_session.py as facade over 4 submodules"
```

---

### Task 6: Verify Regression

**Files:**
- (none — run tests and check)

- [ ] **Step 1: Run full test suite**

Run: `python3 -m pytest tests/ -q --tb=short 2>&1 | tail -20`
Expected: all tests pass (0 failed, 0 errors). If any pre-existing failures are detected, note them but do NOT fix unrelated tests.

- [ ] **Step 2: LSP reference check**

Run: `GIT_MASTER=1 grep -rn "RddfSessionCoordinator" skills/ tests/` and confirm the import paths still work. Expected pattern: `from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator` or equivalent via dash-bridge.

- [ ] **Step 3: Update tasks.md**

```bash
sed -i 's/- \[ \]/- [x]/g' openspec/changes/split-rddf-god-class/tasks.md
```

- [ ] **Step 4: Final commit**

```bash
git add openspec/changes/split-rddf-god-class/tasks.md
git commit -m "chore(split-rddf-god-class): mark all tasks complete"
```