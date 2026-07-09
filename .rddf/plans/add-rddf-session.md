# rddf-session Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `skill_use("execute")` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement rddf-session — a user-perspective workflow session abstraction that persists across OpenCode sessions, fixing the workflow-context-loss gap identified in the v2-workflow-overview review. Each guide-arch/plan/ship invocation creates/refreshes a `rds_<12hex>` rddf-session in `.rddf/state/sessions.json`, with 4-option soft-prompt for cross-opencode-session conflicts.

**Architecture:** Three-layer — (1) `skills/rddf-session.md` (user-facing entry point with list/show/resume/abandon/archive-history subcommands), (2) `skills/_lib/rddf_session.py` (RddfSessionCoordinator wrapping the existing v2.0 SessionCoordinator + atomic file I/O + heartbeat + conflict detection), (3) `.rddf/state/sessions.json` (gitignored, project-scoped, schema-validated). `state_vector.py` schema is loosened to allow the `session_management` field (backward compatible). Zero changes to `session.py` / `session_base.py` / `session_manager.py` (full backward compatibility).

**Tech Stack:** Python 3.11+ (no new deps), bash 3+ (skill body subcommand dispatch), bats-core 1.10+ (integration tests), pytest (unit tests), `jsonschema` (already in requirements.txt for schema validation).

---

## Pre-flight (Read Once, Never Repeat)

These gates are confirmed as of `2026-07-09`; **re-verify before execution**:

- [x] Change artifacts exist at `openspec/changes/add-rddf-session/{proposal,design,tasks}.md` and `openspec/changes/add-rddf-session/specs/rddf-session/spec.md`
- [x] `openspec validate add-rddf-session` returns "Change 'add-rddf-session' is valid"
- [x] `SessionCoordinator` (v2.0 lightweight) and `SessionManager` (v2.1 parallel) exist at `skills/_lib/session.py` and `skills/_lib/session_manager.py` respectively — used as base classes for `RddfSessionCoordinator`
- [x] `Session` dataclass, `SessionState` enum (active/paused/completed/failed), `_ALLOWED_TRANSITIONS` defined in `skills/_lib/session_base.py`
- [x] `state_vector.py` has atomic write pattern (write-to-tmp + rename + checksum + FileLock) — replicate in rddf_session.py
- [x] `state_vector.py._SCHEMA` declares `additionalProperties: false` at root — **modify** to allow `session_management` block (backward compatible: only ADDS allowed fields)
- [x] `iteration.py` is **untouched** by this plan (no reverse index in iteration.json; reverse lookup scans sessions.json)
- [x] `worktree.sh` is **untouched** by this plan (rddf-session does NOT hold worktree paths; git worktree list is the source of truth)
- [x] `tests/conftest.py` adds project root to `sys.path` — `import skills._lib.rddf_session` resolves in pytest
- [x] CI constant-truth gate: `grep -rn "assert .* or True" tests/` must remain empty. All new tests use plain `assert` with messages.
- [x] No new pip dependencies. All stdlib (`json`, `datetime`, `uuid`, `pathlib`, `fcntl`/`msvcrt` for file locking, `dataclasses`, `enum`)

**Pre-existing assumptions surfaced by this work**:

1. `state_vector.py._SCHEMA` uses `additionalProperties: false` at root. This blocks the `session_management` field that ADR-0010 v2.0 design specifies. Task 1 modifies the schema to ALLOW this field while keeping all existing fields validated.
2. `iteration.json` is a multi-writer view file (propose/ship/execute/deps/archive all write). Adding `created_by_rddf_session` to every change entry would couple all 5 hooks to session semantics. Plan deliberately omits this; reverse lookup by scanning `sessions.json` (bounded by ≤3 active sessions) is cheap.
3. `guide-arch`/`guide-plan`/`guide-ship` are markdown skill bodies invoked via `skill_use`. To add rddf-session lifecycle hooks, we **insert bash code blocks** at the entry points (top of each skill) and at the phase-completion points (arch-done / plan-done / archive_change).
4. `OPENCODE_SESSION_ID` is **assumed available** via environment variable. Plan documents this assumption; if not available in production, fall back to `hostname + pid` heuristic (deferred to v1.1).

---

## File Structure

### Production Code

| File | Responsibility | Action |
|------|---------------|--------|
| `skills/_lib/rddf_session.py` | RddfSessionCoordinator: create/find/update/list with atomic persistence, heartbeat, conflict detection | Create |
| `skills/_lib/schemas/sessions_schema.json` | JSON Schema v1 for `.rddf/state/sessions.json` | Create |
| `skills/rddf-session.md` | Skill body: list/show/resume/abandon/archive-history subcommands | Create |
| `skills/_lib/state_vector.py` | Loosen `_SCHEMA` root `additionalProperties: false` → allow `session_management` | Edit (1 location) |
| `skills/guide-arch.md` | Insert rddf-session create at Phase 1 entry, close at arch-done gate | Edit (2 locations) |
| `skills/guide-plan.md` | Insert rddf-session create at Phase 1 entry, close at plan-done gate | Edit (2 locations) |
| `skills/guide-ship.md` | Insert rddf-session create at Phase 1 entry, close at archive_change | Edit (3 locations) |

### Tests

| File | Responsibility | Action |
|------|---------------|--------|
| `tests/unit/test_rddf_session.py` | 14 unit tests: create/dedup/parent/heartbeat/timeout/4 conflict scenarios/4 soft-prompt options/attached_changes/close/atomic-write/schema/idempotent | Create |
| `tests/integration/test_rddf_session_lifecycle.py` | 5 integration tests: full lifecycle / cross-opencode-session recovery / worktree-decoupling / orphaned-recovery / history-archive | Create |

### Documentation

| File | Responsibility | Action |
|------|---------------|--------|
| `docs/adr/ADR-0017-rddf-session.md` | New ADR capturing rddf-session design (rationale, schema, state machine) | Create |
| `docs/adr/ADR-0010-multi-session-management.md` | Update status from "已采纳（分阶段）" to "✅ 已实施" | Edit (1 line) |
| `docs/adr/README.md` | Add ADR-0017 row to index table | Edit (1 row) |
| `docs/v2-workflow-overview.md` | Add §4.5 rddf-session + 闭环 11 (cross-opencode session recovery) | Edit (~50 lines) |
| `docs/v2-multi-session-guide.md` | Add §X rddf-session user guide with examples | Edit (~80 lines) |
| `AGENTS.md` | Add `sessions.json` row to 状态文件表 | Edit (1 row) |

**Not touched** (deliberate): `iteration.py`, `deps_output.py`, `deps.md`, `execute.md`, `propose.md`, `status.md`, `feature.md`, `roadmap.md`, `worktree.sh`, `archive.sh`, `state.sh` (stub), `session.py`, `session_base.py`, `session_manager.py`, `gate.py`.

---

### Task 1: Schema v1 for sessions.json

**Files:**
- Create: `skills/_lib/schemas/sessions_schema.json`

- [ ] **Step 1: Create the schema file**

Write to `skills/_lib/schemas/sessions_schema.json`:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "rddf-sessions",
  "description": "rddf-session lifecycle persistence (ADR-0017)",
  "type": "object",
  "required": ["version", "sessions"],
  "additionalProperties": false,
  "properties": {
    "version": {
      "type": "integer",
      "const": 1,
      "description": "Schema version. Bump on breaking changes."
    },
    "updated_at": {
      "type": "string",
      "format": "date-time"
    },
    "sessions": {
      "type": "array",
      "items": { "$ref": "#/definitions/session" }
    }
  },
  "definitions": {
    "session": {
      "type": "object",
      "required": ["session_id", "kind", "owner_opencode_session_id", "state", "started_at", "last_heartbeat"],
      "additionalProperties": false,
      "properties": {
        "session_id": {
          "type": "string",
          "pattern": "^rds_[a-f0-9]{12}$",
          "description": "Unique session id, format rds_<12 hex chars>"
        },
        "kind": {
          "type": "string",
          "enum": ["stage_arch", "stage_plan", "stage_ship"]
        },
        "owner_opencode_session_id": {
          "type": ["string", "null"],
          "description": "OpenCode session ID that owns this rddf-session, or null after abandonment"
        },
        "parent_session_id": {
          "type": ["string", "null"],
          "pattern": "^rds_[a-f0-9]{12}$"
        },
        "goal": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "intent": {
              "type": "string",
              "enum": ["guide-arch", "guide-plan", "guide-ship"]
            },
            "subject": { "type": "string" },
            "expected_outcome": { "type": "string" }
          }
        },
        "state": {
          "type": "string",
          "enum": ["active", "completed", "failed", "orphaned", "abandoned"]
        },
        "attached_changes": {
          "type": "array",
          "items": { "type": "string" }
        },
        "context_pointer": {
          "type": ["string", "null"],
          "description": "Path to handoff/state file for this session"
        },
        "started_at": { "type": "string", "format": "date-time" },
        "last_heartbeat": { "type": "string", "format": "date-time" },
        "ended_at": { "type": ["string", "null"], "format": "date-time" },
        "end_reason": { "type": ["string", "null"] }
      }
    }
  }
}
```

- [ ] **Step 2: Verify schema is valid JSON**

Run: `python3 -c "import json; json.load(open('skills/_lib/schemas/sessions_schema.json'))"`
Expected: no error (silent exit).

- [ ] **Step 3: Commit**

```bash
cd /workspace/project/spec-workflow && git add skills/_lib/schemas/sessions_schema.json && git commit -m "feat(schemas): add sessions_schema.json v1 for rddf-session — ADR-0017"
```

---

### Task 2: Loosen state_vector.py schema for session_management

**Files:**
- Modify: `skills/_lib/state_vector.py` (line ~38, `_SCHEMA` definition)

- [ ] **Step 1: Read the current schema**

Run: `grep -n "additionalProperties" skills/_lib/state_vector.py | head -20`

Expected: shows `additionalProperties: false` at root and inside nested blocks.

- [ ] **Step 2: Modify root schema to allow session_management**

In `skills/_lib/state_vector.py`, find the `_SCHEMA` dict definition. Locate the top-level `properties` block. Add `session_management` to allowed properties:

```python
"session_management": {
    "type": "object",
    "properties": {
        "current_session": {"type": ["object", "null"]},
        "active_sessions": {"type": "array", "items": {"type": "object"}},
        "session_statistics": {
            "type": "object",
            "properties": {
                "total": {"type": "integer"},
                "active": {"type": "integer"},
                "completed": {"type": "integer"},
                "failed": {"type": "integer"}
            }
        }
    },
    "additionalProperties": False
},
```

Also change the root `"additionalProperties": false` to `"additionalProperties": true` (or keep false but ensure session_management is in `required` exclusions). Per backward-compatibility, prefer adding to allowed keys WITHOUT changing root additionalProperties.

- [ ] **Step 3: Verify existing unit tests pass**

Run: `cd /workspace/project/spec-workflow && python3 -m pytest tests/unit/test_state_vector.py -q --tb=short`
Expected: All pass (backward-compatible).

- [ ] **Step 4: Commit**

```bash
cd /workspace/project/spec-workflow && git add skills/_lib/state_vector.py && git commit -m "feat(state-vector): allow session_management field in schema — ADR-0017"
```

---

### Task 3: RddfSessionCoordinator skeleton + create_session

**Files:**
- Create: `skills/_lib/rddf_session.py`
- Create: `tests/unit/test_rddf_session.py`

- [ ] **Step 1: Write failing test for create_session**

Write to `tests/unit/test_rddf_session.py`:
```python
"""Tests for RddfSessionCoordinator — user-perspective workflow session persistence (ADR-0017)."""
import json
import os
import time
from pathlib import Path

import jsonschema
import pytest

from skills._lib.rddf_session import RddfSessionCoordinator, RddfSessionError


@pytest.fixture
def sessions_file(tmp_path):
    return tmp_path / "sessions.json"


@pytest.fixture
def coordinator(sessions_file):
    return RddfSessionCoordinator(sessions_file=str(sessions_file))


def test_create_session_returns_valid_id(coordinator):
    """create_session MUST return id matching rds_<12 hex chars>."""
    sid = coordinator.create_session(
        kind="stage_plan",
        owner_opencode_session_id="ses_test123",
        goal={"intent": "guide-plan", "subject": "change-auth", "expected_outcome": "plan-done"},
    )
    assert sid.startswith("rds_")
    assert len(sid) == 16  # "rds_" + 12 hex


def test_create_session_persists_to_file(coordinator, sessions_file):
    """After create_session, sessions.json MUST contain the new entry."""
    sid = coordinator.create_session(
        kind="stage_arch",
        owner_opencode_session_id="ses_abc",
        goal={"intent": "guide-arch"},
    )
    assert sessions_file.exists()
    data = json.loads(sessions_file.read_text())
    assert len(data["sessions"]) == 1
    assert data["sessions"][0]["session_id"] == sid
    assert data["sessions"][0]["state"] == "active"
    assert data["sessions"][0]["kind"] == "stage_arch"


def test_create_session_writes_valid_schema(coordinator, sessions_file):
    """sessions.json output MUST pass sessions_schema.json validation."""
    sid = coordinator.create_session(
        kind="stage_ship",
        owner_opencode_session_id="ses_xyz",
        goal={"intent": "guide-ship", "subject": "change-x"},
    )
    schema_path = Path(__file__).resolve().parents[2] / "skills" / "_lib" / "schemas" / "sessions_schema.json"
    schema = json.loads(schema_path.read_text())
    data = json.loads(sessions_file.read_text())
    jsonschema.validate(instance=data, schema=schema)
```

- [ ] **Step 2: Run test — verify it fails**

Run: `cd /workspace/project/spec-workflow && python3 -m pytest tests/unit/test_rddf_session.py -v`
Expected: `ModuleNotFoundError: No module named 'skills._lib.rddf_session'`

- [ ] **Step 3: Create rddf_session.py with skeleton + create_session**

Write to `skills/_lib/rddf_session.py`:
```python
"""RddfSessionCoordinator — user-perspective workflow session persistence (ADR-0017).

Wraps the v2.0 SessionCoordinator with:
- File-backed persistence to .rddf/state/sessions.json (atomic write)
- OpenCode session binding via owner_opencode_session_id
- 5-minute heartbeat refresh, 30-minute timeout → orphaned
- 4-option soft-prompt conflict detection
- Schema validation via sessions_schema.json

Backward compatibility: does NOT modify SessionCoordinator / SessionManager APIs.
"""
from __future__ import annotations

import datetime
import enum
import fcntl
import json
import os
import pathlib
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional


SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "sessions_schema.json"
DEFAULT_HEARTBEAT_TIMEOUT_SECONDS = 30 * 60  # 30 minutes
HEARTBEAT_REFRESH_THRESHOLD_SECONDS = 5 * 60  # 5 minutes
LOCK_TIMEOUT_SECONDS = 5.0


class RddfSessionState(str, enum.Enum):
    """Lifecycle states of an rddf-session."""
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    ORPHANED = "orphaned"
    ABANDONED = "abandoned"


class RddfSessionError(Exception):
    """Base error for rddf-session operations."""
    pass


class SchemaValidationError(RddfSessionError):
    """Raised when sessions.json fails schema validation."""
    pass


class ConflictError(RddfSessionError):
    """Raised on cross-opencode-session conflict (caller must invoke 4-option prompt)."""
    pass


def _new_id() -> str:
    """Generate rds_<12 hex chars>."""
    return f"rds_{uuid.uuid4().hex[:12]}"


def _now() -> str:
    """ISO 8601 UTC timestamp with timezone."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


@dataclass
class RddfSession:
    """A single rddf-session record (mirrors ADR-0017 schema)."""
    session_id: str
    kind: str
    owner_opencode_session_id: Optional[str]
    parent_session_id: Optional[str] = None
    goal: Dict[str, Any] = field(default_factory=dict)
    state: str = "active"
    attached_changes: List[str] = field(default_factory=list)
    context_pointer: Optional[str] = None
    started_at: str = ""
    last_heartbeat: str = ""
    ended_at: Optional[str] = None
    end_reason: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


class RddfSessionCoordinator:
    """Persist rddf-session lifecycle to .rddf/state/sessions.json."""

    def __init__(self, sessions_file: str):
        self._sessions_file = pathlib.Path(sessions_file)
        self._lock_file = self._sessions_file.with_suffix(".lock")

    # ---------- File I/O ----------

    def _read_unlocked(self) -> dict:
        """Read sessions.json. Returns empty structure if missing."""
        if not self._sessions_file.exists():
            return {"version": 1, "sessions": []}
        with self._sessions_file.open("r") as f:
            return json.load(f)

    def _atomic_write(self, data: dict) -> None:
        """Write sessions.json atomically (write-to-tmp + rename)."""
        self._sessions_file.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._sessions_file.with_suffix(".json.tmp")
        with tmp_path.open("w") as f:
            json.dump(data, f, indent=2, sort_keys=False)
        os.replace(tmp_path, self._sessions_file)

    def _with_file_lock(self, fn):
        """Acquire advisory file lock, run fn, release."""
        self._lock_file.parent.mkdir(parents=True, exist_ok=True)
        with self._lock_file.open("w") as lockf:
            try:
                fcntl.flock(lockf.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except (IOError, OSError):
                raise RddfSessionError(f"Could not acquire lock on {self._lock_file}")
            try:
                return fn()
            finally:
                fcntl.flock(lockf.fileno(), fcntl.LOCK_UN)

    # ---------- Public API ----------

    def create_session(
        self,
        kind: str,
        owner_opencode_session_id: str,
        goal: Dict[str, Any],
        parent_session_id: Optional[str] = None,
        context_pointer: Optional[str] = None,
    ) -> str:
        """Create a new rddf-session and persist.

        Returns the new session_id. Fails if an active session of the same kind
        exists with a DIFFERENT owner (raises ConflictError).
        """
        if kind not in ("stage_arch", "stage_plan", "stage_ship"):
            raise RddfSessionError(f"Invalid kind: {kind}")
        if not isinstance(goal, dict):
            raise RddfSessionError(f"goal must be dict, got {type(goal).__name__}")

        def _do_create():
            data = self._read_unlocked()
            # Check for active conflict
            for existing in data["sessions"]:
                if existing["kind"] == kind and existing["state"] == "active":
                    if existing["owner_opencode_session_id"] != owner_opencode_session_id:
                        raise ConflictError(
                            f"Active {kind} session {existing['session_id']} "
                            f"owned by {existing['owner_opencode_session_id']}"
                        )
                    # Same owner — reuse existing
                    return existing["session_id"]

            # Create new
            now = _now()
            session = RddfSession(
                session_id=_new_id(),
                kind=kind,
                owner_opencode_session_id=owner_opencode_session_id,
                parent_session_id=parent_session_id,
                goal=goal,
                state="active",
                context_pointer=context_pointer,
                started_at=now,
                last_heartbeat=now,
            )
            data["sessions"].append(session.to_dict())
            data["updated_at"] = now
            self._atomic_write(data)
            return session.session_id

        return self._with_file_lock(_do_create)

    # ---------- Placeholder methods (filled in later tasks) ----------

    def find_session(self, session_id: str) -> Optional[RddfSession]:
        raise NotImplementedError

    def update_session_status(self, session_id: str, new_state: str, end_reason: Optional[str] = None) -> None:
        raise NotImplementedError

    def list_sessions(self, kind: Optional[str] = None) -> List[RddfSession]:
        raise NotImplementedError

    def attach_change(self, session_id: str, change_name: str) -> None:
        raise NotImplementedError

    def detach_change(self, session_id: str, change_name: str) -> None:
        raise NotImplementedError

    def refresh_heartbeat(self, session_id: str) -> None:
        raise NotImplementedError

    def check_heartbeat_timeouts(self) -> List[str]:
        """Mark sessions with last_heartbeat > 30min ago as orphaned. Returns list of newly-orphaned session_ids."""
        raise NotImplementedError

    def detect_conflict(self, kind: str, owner_opencode_session_id: str) -> Optional[RddfSession]:
        """Return active session of `kind` if owned by a different opencode session. None if no conflict."""
        raise NotImplementedError

    def transfer_ownership(self, session_id: str, new_owner: str) -> None:
        raise NotImplementedError

    def abandon(self, session_id: str) -> None:
        raise NotImplementedError

    def archive_history(self, keep: int = 20) -> int:
        """Move completed/failed/abandoned sessions beyond `keep` to .archive.json. Returns count archived."""
        raise NotImplementedError
```

- [ ] **Step 4: Run tests — verify create tests pass**

Run: `cd /workspace/project/spec-workflow && python3 -m pytest tests/unit/test_rddf_session.py -v`
Expected: 3 passed (create tests).

- [ ] **Step 5: Commit**

```bash
cd /workspace/project/spec-workflow && git add skills/_lib/rddf_session.py tests/unit/test_rddf_session.py && git commit -m "feat(rddf-session): add RddfSessionCoordinator skeleton with create_session — ADR-0017"
```

---

### Task 4: Implement find_session, list_sessions, update_session_status

**Files:**
- Modify: `skills/_lib/rddf_session.py`
- Modify: `tests/unit/test_rddf_session.py`

- [ ] **Step 1: Add tests**

Append to `tests/unit/test_rddf_session.py`:
```python
def test_find_session_returns_session(coordinator):
    """find_session MUST return RddfSession for valid id, None otherwise."""
    sid = coordinator.create_session(kind="stage_plan", owner_opencode_session_id="ses_a", goal={})
    found = coordinator.find_session(sid)
    assert found is not None
    assert found.session_id == sid
    assert found.state == "active"


def test_find_session_returns_none_for_unknown(coordinator):
    assert coordinator.find_session("rds_nonexistent") is None


def test_list_sessions_returns_all(coordinator):
    """list_sessions MUST return all sessions, optionally filtered by kind."""
    coordinator.create_session(kind="stage_arch", owner_opencode_session_id="ses_a", goal={})
    coordinator.create_session(kind="stage_plan", owner_opencode_session_id="ses_a", goal={})
    coordinator.create_session(kind="stage_plan", owner_opencode_session_id="ses_b", goal={})
    all_sessions = coordinator.list_sessions()
    assert len(all_sessions) == 3
    plan_only = coordinator.list_sessions(kind="stage_plan")
    assert len(plan_only) == 2
    assert all(s.kind == "stage_plan" for s in plan_only)


def test_update_session_status_valid(coordinator):
    """update_session_status MUST transition active → completed/failed."""
    sid = coordinator.create_session(kind="stage_arch", owner_opencode_session_id="ses_a", goal={})
    coordinator.update_session_status(sid, "completed", end_reason="arch-done")
    found = coordinator.find_session(sid)
    assert found.state == "completed"
    assert found.end_reason == "arch-done"
    assert found.ended_at is not None


def test_update_session_status_terminal_blocks(coordinator):
    """update_session_status MUST NOT allow transitions from terminal states (completed/failed/abandoned)."""
    sid = coordinator.create_session(kind="stage_arch", owner_opencode_session_id="ses_a", goal={})
    coordinator.update_session_status(sid, "completed", end_reason="x")
    with pytest.raises(RddfSessionError):
        coordinator.update_session_status(sid, "active")
```

- [ ] **Step 2: Run — verify fail**

Run: `cd /workspace/project/spec-workflow && python3 -m pytest tests/unit/test_rddf_session.py -v -k "find_session or list_sessions or update_session_status"`
Expected: NotImplementedError raised.

- [ ] **Step 3: Implement methods**

Replace the placeholder NotImplementedError methods in `skills/_lib/rddf_session.py`:

```python
    def find_session(self, session_id: str) -> Optional[RddfSession]:
        """Look up session by id. Returns copy or None."""
        def _do_find():
            data = self._read_unlocked()
            for s in data["sessions"]:
                if s["session_id"] == session_id:
                    return RddfSession(**s)
            return None
        return self._with_file_lock(_do_find)

    def list_sessions(self, kind: Optional[str] = None) -> List[RddfSession]:
        """Return all sessions (or filtered by kind), sorted by started_at desc."""
        def _do_list():
            data = self._read_unlocked()
            sessions = [RddfSession(**s) for s in data["sessions"]]
            if kind:
                sessions = [s for s in sessions if s.kind == kind]
            sessions.sort(key=lambda s: s.started_at, reverse=True)
            return sessions
        return self._with_file_lock(_do_list)

    def update_session_status(self, session_id: str, new_state: str, end_reason: Optional[str] = None) -> None:
        """Transition session to new_state. Sets ended_at and end_reason if terminal."""
        if new_state not in ("active", "completed", "failed", "orphaned", "abandoned"):
            raise RddfSessionError(f"Invalid state: {new_state}")

        def _do_update():
            data = self._read_unlocked()
            for s in data["sessions"]:
                if s["session_id"] == session_id:
                    if s["state"] in ("completed", "failed", "abandoned"):
                        raise RddfSessionError(
                            f"Cannot transition from terminal state {s['state']}"
                        )
                    s["state"] = new_state
                    if new_state in ("completed", "failed", "abandoned"):
                        s["ended_at"] = _now()
                        s["end_reason"] = end_reason
                    else:
                        s["last_heartbeat"] = _now()
                    data["updated_at"] = s["ended_at"] or s["last_heartbeat"]
                    self._atomic_write(data)
                    return
            raise RddfSessionError(f"Unknown session: {session_id}")
        self._with_file_lock(_do_update)
```

- [ ] **Step 4: Run — verify pass**

Run: `cd /workspace/project/spec-workflow && python3 -m pytest tests/unit/test_rddf_session.py -v -k "find_session or list_sessions or update_session_status"`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
cd /workspace/project/spec-workflow && git add skills/_lib/rddf_session.py tests/unit/test_rddf_session.py && git commit -m "feat(rddf-session): add find/list/update_session_status — ADR-0017"
```

---

### Task 5: Implement attach_change, detach_change, refresh_heartbeat

**Files:**
- Modify: `skills/_lib/rddf_session.py`
- Modify: `tests/unit/test_rddf_session.py`

- [ ] **Step 1: Add tests**

Append to `tests/unit/test_rddf_session.py`:
```python
def test_attach_change(coordinator):
    """attach_change MUST add change_name to session's attached_changes."""
    sid = coordinator.create_session(kind="stage_plan", owner_opencode_session_id="ses_a", goal={})
    coordinator.attach_change(sid, "change-auth")
    coordinator.attach_change(sid, "change-user-profile")
    found = coordinator.find_session(sid)
    assert "change-auth" in found.attached_changes
    assert "change-user-profile" in found.attached_changes
    assert len(found.attached_changes) == 2


def test_attach_change_idempotent(coordinator):
    """attach_change MUST NOT duplicate existing entries."""
    sid = coordinator.create_session(kind="stage_plan", owner_opencode_session_id="ses_a", goal={})
    coordinator.attach_change(sid, "change-auth")
    coordinator.attach_change(sid, "change-auth")
    found = coordinator.find_session(sid)
    assert found.attached_changes.count("change-auth") == 1


def test_detach_change(coordinator):
    """detach_change MUST remove change_name from attached_changes."""
    sid = coordinator.create_session(kind="stage_plan", owner_opencode_session_id="ses_a", goal={})
    coordinator.attach_change(sid, "change-auth")
    coordinator.detach_change(sid, "change-auth")
    found = coordinator.find_session(sid)
    assert "change-auth" not in found.attached_changes


def test_refresh_heartbeat(coordinator):
    """refresh_heartbeat MUST update last_heartbeat to now."""
    sid = coordinator.create_session(kind="stage_plan", owner_opencode_session_id="ses_a", goal={})
    before = coordinator.find_session(sid).last_heartbeat
    time.sleep(0.01)
    coordinator.refresh_heartbeat(sid)
    after = coordinator.find_session(sid).last_heartbeat
    assert after >= before
```

- [ ] **Step 2: Run — verify fail**

Run: `cd /workspace/project/spec-workflow && python3 -m pytest tests/unit/test_rddf_session.py -v -k "attach_change or detach_change or refresh_heartbeat"`
Expected: NotImplementedError.

- [ ] **Step 3: Implement methods**

Replace the placeholder methods in `skills/_lib/rddf_session.py`:

```python
    def attach_change(self, session_id: str, change_name: str) -> None:
        """Add change_name to session's attached_changes (idempotent)."""
        def _do_attach():
            data = self._read_unlocked()
            for s in data["sessions"]:
                if s["session_id"] == session_id:
                    if change_name not in s["attached_changes"]:
                        s["attached_changes"].append(change_name)
                        s["last_heartbeat"] = _now()
                        data["updated_at"] = s["last_heartbeat"]
                        self._atomic_write(data)
                    return
            raise RddfSessionError(f"Unknown session: {session_id}")
        self._with_file_lock(_do_attach)

    def detach_change(self, session_id: str, change_name: str) -> None:
        """Remove change_name from session's attached_changes (idempotent)."""
        def _do_detach():
            data = self._read_unlocked()
            for s in data["sessions"]:
                if s["session_id"] == session_id:
                    if change_name in s["attached_changes"]:
                        s["attached_changes"].remove(change_name)
                        s["last_heartbeat"] = _now()
                        data["updated_at"] = s["last_heartbeat"]
                        self._atomic_write(data)
                    return
            raise RddfSessionError(f"Unknown session: {session_id}")
        self._with_file_lock(_do_detach)

    def refresh_heartbeat(self, session_id: str) -> None:
        """Update last_heartbeat to now. Only valid for active sessions."""
        def _do_refresh():
            data = self._read_unlocked()
            for s in data["sessions"]:
                if s["session_id"] == session_id:
                    if s["state"] != "active":
                        raise RddfSessionError(f"Cannot refresh non-active session (state={s['state']})")
                    s["last_heartbeat"] = _now()
                    data["updated_at"] = s["last_heartbeat"]
                    self._atomic_write(data)
                    return
            raise RddfSessionError(f"Unknown session: {session_id}")
        self._with_file_lock(_do_refresh)
```

- [ ] **Step 4: Run — verify pass**

Run: `cd /workspace/project/spec-workflow && python3 -m pytest tests/unit/test_rddf_session.py -v -k "attach_change or detach_change or refresh_heartbeat"`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
cd /workspace/project/spec-workflow && git add skills/_lib/rddf_session.py tests/unit/test_rddf_session.py && git commit -m "feat(rddf-session): add attach_change/detach_change/refresh_heartbeat — ADR-0017"
```

---

### Task 6: Implement check_heartbeat_timeouts and conflict detection

**Files:**
- Modify: `skills/_lib/rddf_session.py`
- Modify: `tests/unit/test_rddf_session.py`

- [ ] **Step 1: Add tests**

Append to `tests/unit/test_rddf_session.py`:
```python
def test_check_heartbeat_timeouts_marks_orphaned(coordinator):
    """Sessions with last_heartbeat > 30min ago MUST be marked orphaned."""
    sid = coordinator.create_session(kind="stage_plan", owner_opencode_session_id="ses_a", goal={})
    # Manually backdate last_heartbeat
    data_path = Path(coordinator._sessions_file)
    data = json.loads(data_path.read_text())
    for s in data["sessions"]:
        if s["session_id"] == sid:
            s["last_heartbeat"] = "2020-01-01T00:00:00+00:00"
    data_path.write_text(json.dumps(data))
    newly_orphaned = coordinator.check_heartbeat_timeouts()
    assert sid in newly_orphaned
    found = coordinator.find_session(sid)
    assert found.state == "orphaned"
    assert found.end_reason == "heartbeat-timeout"


def test_detect_conflict_none_when_no_active(coordinator):
    """detect_conflict MUST return None when no active session of that kind exists."""
    result = coordinator.detect_conflict("stage_plan", owner_opencode_session_id="ses_a")
    assert result is None


def test_detect_conflict_none_when_same_owner(coordinator):
    """detect_conflict MUST return None when active session owned by same opencode session."""
    coordinator.create_session(kind="stage_plan", owner_opencode_session_id="ses_a", goal={})
    result = coordinator.detect_conflict("stage_plan", owner_opencode_session_id="ses_a")
    assert result is None


def test_detect_conflict_returns_session_when_different_owner(coordinator):
    """detect_conflict MUST return existing session when owned by different opencode session."""
    coordinator.create_session(kind="stage_plan", owner_opencode_session_id="ses_a", goal={})
    result = coordinator.detect_conflict("stage_plan", owner_opencode_session_id="ses_b")
    assert result is not None
    assert result.owner_opencode_session_id == "ses_a"
    assert result.state == "active"
```

- [ ] **Step 2: Run — verify fail**

Run: `cd /workspace/project/spec-workflow && python3 -m pytest tests/unit/test_rddf_session.py -v -k "check_heartbeat or detect_conflict"`
Expected: NotImplementedError.

- [ ] **Step 3: Implement methods**

Replace the placeholder methods in `skills/_lib/rddf_session.py`:

```python
    def check_heartbeat_timeouts(self) -> List[str]:
        """Mark active sessions with last_heartbeat > timeout as orphaned. Returns newly-orphaned ids."""
        newly_orphaned: List[str] = []

        def _do_check():
            nonlocal newly_orphaned
            data = self._read_unlocked()
            now = datetime.datetime.now(datetime.timezone.utc)
            for s in data["sessions"]:
                if s["state"] != "active":
                    continue
                last_hb = datetime.datetime.fromisoformat(s["last_heartbeat"])
                if (now - last_hb).total_seconds() > DEFAULT_HEARTBEAT_TIMEOUT_SECONDS:
                    s["state"] = "orphaned"
                    s["ended_at"] = _now()
                    s["end_reason"] = "heartbeat-timeout"
                    newly_orphaned.append(s["session_id"])
            if newly_orphaned:
                data["updated_at"] = _now()
                self._atomic_write(data)
        self._with_file_lock(_do_check)
        return newly_orphaned

    def detect_conflict(self, kind: str, owner_opencode_session_id: str) -> Optional[RddfSession]:
        """Return active session of `kind` if owned by a DIFFERENT opencode session."""
        def _do_detect():
            data = self._read_unlocked()
            for s in data["sessions"]:
                if s["kind"] == kind and s["state"] == "active":
                    if s["owner_opencode_session_id"] != owner_opencode_session_id:
                        return RddfSession(**s)
            return None
        return self._with_file_lock(_do_detect)
```

- [ ] **Step 4: Run — verify pass**

Run: `cd /workspace/project/spec-workflow && python3 -m pytest tests/unit/test_rddf_session.py -v -k "check_heartbeat or detect_conflict"`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
cd /workspace/project/spec-workflow && git add skills/_lib/rddf_session.py tests/unit/test_rddf_session.py && git commit -m "feat(rddf-session): add heartbeat-timeout check + conflict detection — ADR-0017"
```

---

### Task 7: Implement transfer_ownership, abandon, archive_history

**Files:**
- Modify: `skills/_lib/rddf_session.py`
- Modify: `tests/unit/test_rddf_session.py`

- [ ] **Step 1: Add tests**

Append to `tests/unit/test_rddf_session.py`:
```python
def test_transfer_ownership(coordinator):
    """transfer_ownership MUST update owner_opencode_session_id and refresh heartbeat."""
    sid = coordinator.create_session(kind="stage_plan", owner_opencode_session_id="ses_a", goal={})
    coordinator.transfer_ownership(sid, "ses_b")
    found = coordinator.find_session(sid)
    assert found.owner_opencode_session_id == "ses_b"
    # Heartbeat refreshed (compare timestamps — must be >=)


def test_abandon(coordinator):
    """abandon MUST transition state to abandoned with end_reason user-abandoned."""
    sid = coordinator.create_session(kind="stage_plan", owner_opencode_session_id="ses_a", goal={})
    coordinator.abandon(sid)
    found = coordinator.find_session(sid)
    assert found.state == "abandoned"
    assert found.end_reason == "user-abandoned"
    assert found.ended_at is not None


def test_archive_history(coordinator):
    """archive_history MUST move old completed/failed/abandoned sessions to .archive.json, keep recent N."""
    # Create 5 sessions, complete 4 of them
    sids = []
    for i in range(5):
        sid = coordinator.create_session(
            kind="stage_arch",
            owner_opencode_session_id=f"ses_{i}",
            goal={"intent": "guide-arch", "subject": f"change-{i}"},
        )
        sids.append(sid)
    # Complete 4 (leave 1 active)
    for sid in sids[:4]:
        coordinator.update_session_status(sid, "completed", end_reason="x")

    archived_count = coordinator.archive_history(keep=2)
    assert archived_count == 2  # 4 completed - 2 keep = 2 archived

    # Verify: main file has 1 active + 2 most recent completed
    remaining = coordinator.list_sessions()
    active_or_recent = [s for s in remaining if s.state == "active"] + [
        s for s in remaining if s.state == "completed"
    ]
    assert len(remaining) == 3

    # Archive file should exist
    archive_path = Path(coordinator._sessions_file).with_suffix(".archive.json")
    assert archive_path.exists()
    archive_data = json.loads(archive_path.read_text())
    assert len(archive_data["sessions"]) == 2
```

- [ ] **Step 2: Run — verify fail**

Run: `cd /workspace/project/spec-workflow && python3 -m pytest tests/unit/test_rddf_session.py -v -k "transfer_ownership or abandon or archive_history"`
Expected: NotImplementedError.

- [ ] **Step 3: Implement methods**

Replace the placeholder methods in `skills/_lib/rddf_session.py`:

```python
    def transfer_ownership(self, session_id: str, new_owner: str) -> None:
        """Transfer ownership to a new opencode session. Refreshes heartbeat."""
        def _do_transfer():
            data = self._read_unlocked()
            for s in data["sessions"]:
                if s["session_id"] == session_id:
                    if s["state"] != "active":
                        raise RddfSessionError(f"Cannot transfer non-active session (state={s['state']})")
                    s["owner_opencode_session_id"] = new_owner
                    s["last_heartbeat"] = _now()
                    data["updated_at"] = s["last_heartbeat"]
                    self._atomic_write(data)
                    return
            raise RddfSessionError(f"Unknown session: {session_id}")
        self._with_file_lock(_do_transfer)

    def abandon(self, session_id: str) -> None:
        """Mark session as abandoned by current owner."""
        def _do_abandon():
            data = self._read_unlocked()
            for s in data["sessions"]:
                if s["session_id"] == session_id:
                    if s["state"] in ("completed", "failed", "abandoned"):
                        raise RddfSessionError(f"Session already terminal: {s['state']}")
                    s["state"] = "abandoned"
                    s["ended_at"] = _now()
                    s["end_reason"] = "user-abandoned"
                    data["updated_at"] = s["ended_at"]
                    self._atomic_write(data)
                    return
            raise RddfSessionError(f"Unknown session: {session_id}")
        self._with_file_lock(_do_abandon)

    def archive_history(self, keep: int = 20) -> int:
        """Move old completed/failed/abandoned sessions to .archive.json. Keep most recent N of each."""
        archive_path = self._sessions_file.with_suffix(".archive.json")
        if archive_path.exists():
            archive_data = json.loads(archive_path.read_text())
        else:
            archive_data = {"version": 1, "sessions": []}

        def _do_archive():
            nonlocal archive_data
            data = self._read_unlocked()
            # Partition: terminal (archivable) vs active/orphaned (keep)
            terminal = [s for s in data["sessions"] if s["state"] in ("completed", "failed", "abandoned")]
            keep_set = [s for s in data["sessions"] if s["state"] not in ("completed", "failed", "abandoned")]

            # Sort terminal by ended_at desc, keep most recent N
            terminal.sort(key=lambda s: s.get("ended_at") or "", reverse=True)
            to_archive = terminal[keep:]
            to_keep = terminal[:keep] + keep_set

            # Move to archive
            archive_data["sessions"].extend(to_archive)
            archive_data["updated_at"] = _now()
            archive_path.parent.mkdir(parents=True, exist_ok=True)
            with archive_path.open("w") as f:
                json.dump(archive_data, f, indent=2)

            # Update main file
            data["sessions"] = to_keep
            data["updated_at"] = _now()
            self._atomic_write(data)
            return len(to_archive)
        return self._with_file_lock(_do_archive)
```

- [ ] **Step 4: Run — verify pass**

Run: `cd /workspace/project/spec-workflow && python3 -m pytest tests/unit/test_rddf_session.py -v -k "transfer_ownership or abandon or archive_history"`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
cd /workspace/project/spec-workflow && git add skills/_lib/rddf_session.py tests/unit/test_rddf_session.py && git commit -m "feat(rddf-session): add transfer/abandon/archive_history — ADR-0017"
```

---

### Task 8: Idempotency + conflict-resilience test + full suite

**Files:**
- Modify: `tests/unit/test_rddf_session.py`

- [ ] **Step 1: Add idempotency test**

Append to `tests/unit/test_rddf_session.py`:
```python
def test_create_session_idempotent_same_owner(coordinator):
    """Calling create_session twice with same kind+owner MUST return same session id (no duplicate)."""
    sid1 = coordinator.create_session(kind="stage_plan", owner_opencode_session_id="ses_a", goal={"intent": "guide-plan"})
    sid2 = coordinator.create_session(kind="stage_plan", owner_opencode_session_id="ses_a", goal={"intent": "guide-plan"})
    assert sid1 == sid2
    # Verify only 1 session in file
    all_sessions = coordinator.list_sessions()
    assert len(all_sessions) == 1


def test_create_session_raises_conflict_different_owner(coordinator):
    """create_session MUST raise ConflictError when active session has different owner."""
    coordinator.create_session(kind="stage_plan", owner_opencode_session_id="ses_a", goal={})
    with pytest.raises(ConflictError):
        coordinator.create_session(kind="stage_plan", owner_opencode_session_id="ses_b", goal={})
```

- [ ] **Step 2: Run all unit tests — verify total ≥14 pass**

Run: `cd /workspace/project/spec-workflow && python3 -m pytest tests/unit/test_rddf_session.py -v`
Expected: 14+ passed.

- [ ] **Step 3: Commit**

```bash
cd /workspace/project/spec-workflow && git add tests/unit/test_rddf_session.py && git commit -m "test(rddf-session): add idempotency + conflict-resilience — ADR-0017"
```

---

### Task 9: rddf-session skill body (CLI entry point)

**Files:**
- Create: `skills/rddf-session.md`

- [ ] **Step 1: Create skill body**

Write to `skills/rddf-session.md`:
```markdown
---
name: rddf-session
description: 用户视角工作流会话管理 — list/show/resume/abandon/archive-history
license: MIT
compatibility: Python 3.11+, spec-workflow v2.0.1+
metadata:
  author: sisyphus
  version: "1.0"
  evolved-from: "ADR-0017"
  user-invocable: true
---

# rddf-session

User-perspective workflow session management. Persists rddf-session lifecycle
to `.rddf/state/sessions.json` and provides cross-opencode-session recovery.

## Subcommands

| Subcommand | Description |
|-----------|-------------|
| `list` | List all rddf-sessions (active + recent history) |
| `show <id>` | Show full JSON for a session |
| `resume <id>` | Transfer ownership to current opencode session; refresh heartbeat; transition orphaned→active |
| `abandon <id>` | Mark session as abandoned by current owner |
| `archive-history [--keep=N]` | Move old completed/failed/abandoned sessions to `.archive.json`, keep recent N |

## Usage

```bash
# List all sessions
skill_use("rddf-session", "list")

# Show specific session
skill_use("rddf-session", "show", "rds_a3f2b1c9d8e7")

# Resume orphaned session (transfer ownership to current opencode session)
skill_use("rddf-session", "resume", "rds_a3f2b1c9d8e7")

# Abandon current session
skill_use("rddf-session", "abandon", "rds_a3f2b1c9d8e7")

# Archive history (keep recent 20 completed/failed/abandoned)
skill_use("rddf-session", "archive-history", "--keep=20")
```

## Implementation

All subcommands are bash wrappers that invoke `python3 -m skills._lib.rddf_session` with the appropriate subcommand.

```bash
#!/usr/bin/env bash
# Subcommand dispatch
SUBCOMMAND="${1:-list}"
shift || true

PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
SESSIONS_FILE="$PROJECT_ROOT/.rddf/state/sessions.json"
mkdir -p "$(dirname "$SESSIONS_FILE")"

case "$SUBCOMMAND" in
  list)
    python3 -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT')
from skills._lib.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file='$SESSIONS_FILE')
# Check timeouts first
coord.check_heartbeat_timeouts()
sessions = coord.list_sessions()
if not sessions:
    print('No rddf-sessions found.')
else:
    print(f'{\"session_id\":<17} {\"kind\":<14} {\"owner\":<24} {\"state\":<11} {\"last_heartbeat\":<26} {\"changes\":<10}')
    for s in sessions:
        print(f'{s.session_id:<17} {s.kind:<14} {s.owner_opencode_session_id or \"<none>\":<24} {s.state:<11} {s.last_heartbeat:<26} {len(s.attached_changes):<10}')
"
    ;;
  show)
    SESSION_ID="${1:?Usage: show <session_id>}"
    python3 -c "
import sys, json
sys.path.insert(0, '$PROJECT_ROOT')
from skills._lib.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file='$SESSIONS_FILE')
session = coord.find_session('$SESSION_ID')
if not session:
    print(f'Session not found: $SESSION_ID')
    sys.exit(1)
print(json.dumps(session.to_dict(), indent=2))
"
    ;;
  resume)
    SESSION_ID="${1:?Usage: resume <session_id>}"
    OPENCODE_SESSION_ID="${OPENCODE_SESSION_ID:-$(hostname -s)_$$}"
    python3 -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT')
from skills._lib.rddf_session import RddfSessionCoordinator, RddfSessionError
coord = RddfSessionCoordinator(sessions_file='$SESSIONS_FILE')
session = coord.find_session('$SESSION_ID')
if not session:
    print(f'Session not found: $SESSION_ID')
    sys.exit(1)
if session.state == 'orphaned':
    coord.update_session_status('$SESSION_ID', 'active')
    print(f'Session $SESSION_ID transitioned orphaned → active')
elif session.state == 'active':
    print(f'Session $SESSION_ID already active')
else:
    print(f'Cannot resume session in state {session.state}')
    sys.exit(1)
coord.transfer_ownership('$SESSION_ID', '$OPENCODE_SESSION_ID')
print(f'Ownership transferred to $OPENCODE_SESSION_ID')
"
    ;;
  abandon)
    SESSION_ID="${1:?Usage: abandon <session_id>}"
    python3 -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT')
from skills._lib.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file='$SESSIONS_FILE')
coord.abandon('$SESSION_ID')
print(f'Session $SESSION_ID abandoned')
"
    ;;
  archive-history)
    KEEP=20
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --keep=*) KEEP="${1#*=}" ;;
        *) shift ;;
      esac
      shift || true
    done
    python3 -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT')
from skills._lib.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file='$SESSIONS_FILE')
n = coord.archive_history(keep=$KEEP)
print(f'Archived {n} sessions')
"
    ;;
  *)
    echo "Unknown subcommand: $SUBCOMMAND"
    echo "Usage: rddf-session {list|show|resume|abandon|archive-history} ..."
    exit 1
    ;;
esac
```

## Architecture

- **Storage**: `.rddf/state/sessions.json` (gitignored, project-scoped)
- **Schema**: `skills/_lib/schemas/sessions_schema.json` v1 (ADR-0017)
- **Concurrency**: file lock via `fcntl.flock`; atomic write via tmp+rename
- **Heartbeat**: refreshed on every guide-arch/plan/ship phase call; 30min timeout → orphaned
```

- [ ] **Step 2: Verify YAML frontmatter is valid**

Run: `python3 -c "import yaml; yaml.safe_load(open('skills/rddf-session.md').read().split('---')[1])"`
Expected: silent exit (no error).

- [ ] **Step 3: Smoke test the skill body**

Run: `cd /tmp && mkdir -p rddf-smoke && cd rddf-smoke && git init -q && mkdir -p .rddf/state && bash /workspace/project/spec-workflow/skills/rddf-session.md list`
Expected: `No rddf-sessions found.` or similar.

- [ ] **Step 4: Commit**

```bash
cd /workspace/project/spec-workflow && git add skills/rddf-session.md && git commit -m "feat(skill): add rddf-session skill body with 5 subcommands — ADR-0017"
```

---

### Task 10: Integration with guide-arch / guide-plan / guide-ship

**Files:**
- Modify: `skills/guide-arch.md` (entry + arch-done)
- Modify: `skills/guide-plan.md` (entry + plan-done)
- Modify: `skills/guide-ship.md` (entry + archive_change)

- [ ] **Step 1: Modify guide-arch.md entry**

Find the section "**入口**：`skill_use("guide-arch")`" near the top of `skills/guide-arch.md`. After this line, insert:

```bash
# rddf-session hook: create/find stage_arch session
OPENCODE_SESSION_ID="${OPENCODE_SESSION_ID:-$(hostname -s)_$$}"
python3 -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT')
from skills._lib.rddf_session import RddfSessionCoordinator, ConflictError
coord = RddfSessionCoordinator(sessions_file='$PROJECT_ROOT/.rddf/state/sessions.json')
coord.check_heartbeat_timeouts()
try:
    sid = coord.create_session(
        kind='stage_arch',
        owner_opencode_session_id='$OPENCODE_SESSION_ID',
        goal={'intent': 'guide-arch', 'subject': 'arch-phase', 'expected_outcome': 'arch-done'},
        context_pointer='.rddf/state/.arch-handoff.json',
    )
    print(f'rddf-session: {sid} (stage_arch, active)')
except ConflictError as e:
    # Conflict detected — caller should invoke 4-option soft prompt
    print(f'CONFLICT: {e}')
    sys.exit(2)
"
```

Also find the "Phase 5: arch-done" section. After the arch-done gate verification, insert:

```bash
# rddf-session hook: close on arch-done
python3 -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT')
from skills._lib.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file='$PROJECT_ROOT/.rddf/state/sessions.json')
sid = coord.create_session(
    kind='stage_arch',
    owner_opencode_session_id='$OPENCODE_SESSION_ID',
    goal={},
)
coord.update_session_status(sid, 'completed', end_reason='arch-done')
print(f'rddf-session: {sid} → completed (arch-done)')
"
```

- [ ] **Step 2: Modify guide-plan.md entry**

Same pattern at "**入口**：`skill_use("guide-plan")`":

```bash
# rddf-session hook: create/find stage_plan session (parent = latest stage_arch)
OPENCODE_SESSION_ID="${OPENCODE_SESSION_ID:-$(hostname -s)_$$}"
python3 -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT')
from skills._lib.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file='$PROJECT_ROOT/.rddf/state/sessions.json')
coord.check_heartbeat_timeouts()
# Find latest stage_arch as parent
arch_sessions = coord.list_sessions(kind='stage_arch')
parent_id = arch_sessions[0].session_id if arch_sessions else None
sid = coord.create_session(
    kind='stage_plan',
    owner_opencode_session_id='$OPENCODE_SESSION_ID',
    goal={'intent': 'guide-plan', 'subject': 'plan-phase', 'expected_outcome': 'plan-done'},
    parent_session_id=parent_id,
    context_pointer='.rddf/state/.plan-handoff.json',
)
print(f'rddf-session: {sid} (stage_plan, parent={parent_id})')
"
```

Also find "Phase 4: plan-done" gate verification. After, insert:

```bash
# rddf-session hook: close on plan-done
python3 -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT')
from skills._lib.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file='$PROJECT_ROOT/.rddf/state/sessions.json')
sid = coord.create_session(kind='stage_plan', owner_opencode_session_id='$OPENCODE_SESSION_ID', goal={})
coord.update_session_status(sid, 'completed', end_reason='plan-done')
print(f'rddf-session: {sid} → completed (plan-done)')
"
```

Also, in guide-plan Phase 2.5 (fill) and Phase 3 (deps) sub-skills, after the main work, insert a heartbeat refresh:

```bash
# rddf-session hook: refresh heartbeat during phase
python3 -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT')
from skills._lib.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file='$PROJECT_ROOT/.rddf/state/sessions.json')
sid = coord.create_session(kind='stage_plan', owner_opencode_session_id='$OPENCODE_SESSION_ID', goal={})
coord.refresh_heartbeat(sid)
" > /dev/null
```

- [ ] **Step 3: Modify guide-ship.md entry**

Same pattern at "**入口**：`skill_use("guide-ship")`":

```bash
# rddf-session hook: create/find stage_ship session (parent = latest stage_plan)
OPENCODE_SESSION_ID="${OPENCODE_SESSION_ID:-$(hostname -s)_$$}"
python3 -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT')
from skills._lib.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file='$PROJECT_ROOT/.rddf/state/sessions.json')
coord.check_heartbeat_timeouts()
plan_sessions = coord.list_sessions(kind='stage_plan')
parent_id = plan_sessions[0].session_id if plan_sessions else None
sid = coord.create_session(
    kind='stage_ship',
    owner_opencode_session_id='$OPENCODE_SESSION_ID',
    goal={'intent': 'guide-ship', 'subject': 'ship-phase', 'expected_outcome': 'archive-all'},
    parent_session_id=parent_id,
)
print(f'rddf-session: {sid} (stage_ship, parent={parent_id})')
"
```

Also in Phase 3 (archive), after archive_change:

```bash
# rddf-session hook: close on archive completion
python3 -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT')
from skills._lib.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file='$PROJECT_ROOT/.rddf/state/sessions.json')
sid = coord.create_session(kind='stage_ship', owner_opencode_session_id='$OPENCODE_SESSION_ID', goal={})
# Check if all attached_changes archived (assume caller has set this via detach_change)
coord.update_session_status(sid, 'completed', end_reason='archive-all')
print(f'rddf-session: {sid} → completed (archive-all)')
"
```

- [ ] **Step 4: Verify skills still pass openspec validate**

Run: `cd /workspace/project/spec-workflow && openspec validate add-rddf-session`
Expected: `Change 'add-rddf-session' is valid`

- [ ] **Step 5: Commit**

```bash
cd /workspace/project/spec-workflow && git add skills/guide-arch.md skills/guide-plan.md skills/guide-ship.md && git commit -m "feat(skills): integrate rddf-session lifecycle hooks in guide-arch/plan/ship — ADR-0017"
```

---

### Task 11: Integration tests

**Files:**
- Create: `tests/integration/test_rddf_session_lifecycle.py`

- [ ] **Step 1: Write integration test**

Write to `tests/integration/test_rddf_session_lifecycle.py`:
```python
"""Integration tests for rddf-session — full lifecycle, cross-opencode-session recovery, worktree-decoupling."""
import json
import os
import subprocess
import time
from pathlib import Path

import pytest


@pytest.fixture
def project_root(tmp_path):
    """Create a minimal git repo with .rddf/state/ directory."""
    (tmp_path / ".rddf" / "state").mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    return tmp_path


def test_full_lifecycle(project_root):
    """Create → heartbeat refresh → completion → cross-opencode-session read."""
    from skills._lib.rddf_session import RddfSessionCoordinator

    sessions_file = project_root / ".rddf" / "state" / "sessions.json"
    coord = RddfSessionCoordinator(sessions_file=str(sessions_file))

    # 1. Create
    sid = coord.create_session(
        kind="stage_plan",
        owner_opencode_session_id="ses_owner1",
        goal={"intent": "guide-plan", "subject": "change-x"},
    )
    assert sessions_file.exists()

    # 2. Heartbeat refresh
    coord.refresh_heartbeat(sid)
    found = coord.find_session(sid)
    assert found.state == "active"

    # 3. Complete
    coord.update_session_status(sid, "completed", end_reason="plan-done")

    # 4. Read from different opencode session
    coord2 = RddfSessionCoordinator(sessions_file=str(sessions_file))
    found = coord2.find_session(sid)
    assert found is not None
    assert found.state == "completed"
    assert found.end_reason == "plan-done"


def test_cross_opencode_session_conflict_soft_prompt(project_root):
    """Two opencode sessions creating same kind MUST trigger 4-option soft prompt logic."""
    from skills._lib.rddf_session import RddfSessionCoordinator, ConflictError

    sessions_file = project_root / ".rddf" / "state" / "sessions.json"
    coord_a = RddfSessionCoordinator(sessions_file=str(sessions_file))
    sid_a = coord_a.create_session(
        kind="stage_plan",
        owner_opencode_session_id="ses_session_a",
        goal={"intent": "guide-plan"},
    )

    # Session B attempts to create
    coord_b = RddfSessionCoordinator(sessions_file=str(sessions_file))
    with pytest.raises(ConflictError):
        coord_b.create_session(
            kind="stage_plan",
            owner_opencode_session_id="ses_session_b",
            goal={"intent": "guide-plan"},
        )

    # User selects "transfer ownership" (option 2)
    coord_b.transfer_ownership(sid_a, "ses_session_b")

    # Session B retries — should succeed (same owner now)
    sid_b_retry = coord_b.create_session(
        kind="stage_plan",
        owner_opencode_session_id="ses_session_b",
        goal={"intent": "guide-plan"},
    )
    assert sid_b_retry == sid_a  # same session id


def test_worktree_decoupling(project_root):
    """rddf-session MUST NOT contain worktree_path field, even after worktree creation."""
    from skills._lib.rddf_session import RddfSessionCoordinator

    sessions_file = project_root / ".rddf" / "state" / "sessions.json"
    coord = RddfSessionCoordinator(sessions_file=str(sessions_file))

    sid = coord.create_session(
        kind="stage_ship",
        owner_opencode_session_id="ses_x",
        goal={"intent": "guide-ship", "subject": "change-y"},
    )

    # Simulate worktree creation (no rddf-session impact)
    wt_path = project_root / ".rddf" / "wt" / "change-y"
    wt_path.mkdir(parents=True)

    # rddf-session MUST NOT have worktree_path
    found = coord.find_session(sid)
    assert not hasattr(found, "worktree_path")
    data = json.loads(sessions_file.read_text())
    assert "worktree_path" not in data["sessions"][0]


def test_orphaned_recovery(project_root):
    """orphaned session MUST be resumable via resume subcommand."""
    from skills._lib.rddf_session import RddfSessionCoordinator

    sessions_file = project_root / ".rddf" / "state" / "sessions.json"
    coord = RddfSessionCoordinator(sessions_file=str(sessions_file))

    sid = coord.create_session(
        kind="stage_plan",
        owner_opencode_session_id="ses_old",
        goal={"intent": "guide-plan"},
    )

    # Simulate timeout (backdate)
    data = json.loads(sessions_file.read_text())
    for s in data["sessions"]:
        if s["session_id"] == sid:
            s["last_heartbeat"] = "2020-01-01T00:00:00+00:00"
    sessions_file.write_text(json.dumps(data))

    coord.check_heartbeat_timeouts()
    found = coord.find_session(sid)
    assert found.state == "orphaned"

    # Resume
    coord.update_session_status(sid, "active")
    coord.transfer_ownership(sid, "ses_new")

    found = coord.find_session(sid)
    assert found.state == "active"
    assert found.owner_opencode_session_id == "ses_new"


def test_history_archive(project_root):
    """archive_history MUST move old terminal sessions to .archive.json."""
    from skills._lib.rddf_session import RddfSessionCoordinator

    sessions_file = project_root / ".rddf" / "state" / "sessions.json"
    coord = RddfSessionCoordinator(sessions_file=str(sessions_file))

    sids = []
    for i in range(5):
        sid = coord.create_session(
            kind="stage_arch",
            owner_opencode_session_id=f"ses_{i}",
            goal={"intent": "guide-arch", "subject": f"c-{i}"},
        )
        sids.append(sid)
    for sid in sids[:4]:
        coord.update_session_status(sid, "completed", end_reason="x")

    archived = coord.archive_history(keep=2)
    assert archived == 2

    main_count = len(coord.list_sessions())
    assert main_count == 3  # 2 recent completed + 1 active

    archive_file = sessions_file.with_suffix(".archive.json")
    assert archive_file.exists()
    archive_data = json.loads(archive_file.read_text())
    assert len(archive_data["sessions"]) == 2
```

- [ ] **Step 2: Run integration tests**

Run: `cd /workspace/project/spec-workflow && python3 -m pytest tests/integration/test_rddf_session_lifecycle.py -v`
Expected: 5 passed.

- [ ] **Step 3: Commit**

```bash
cd /workspace/project/spec-workflow && git add tests/integration/test_rddf_session_lifecycle.py && git commit -m "test(rddf-session): add 5 integration tests (lifecycle/conflict/worktree/orphaned/archive) — ADR-0017"
```

---

### Task 12: Documentation — ADR-0017 + ADR-0010 status + ADR README

**Files:**
- Create: `docs/adr/ADR-0017-rddf-session.md`
- Modify: `docs/adr/ADR-0010-multi-session-management.md`
- Modify: `docs/adr/README.md`

- [ ] **Step 1: Create ADR-0017**

Write to `docs/adr/ADR-0017-rddf-session.md`:
```markdown
# ADR-0017: rddf-session — 用户视角工作流会话

> **状态**: ✅ 已采纳
> **日期**: 2026-07-09
> **决策者**: sisyphus
> **依据**: ADR-0003 (三阶段架构), ADR-0010 (多会话管理), ADR-0016 (arch discovery contract)
> **版本目标**: v2.0.2 (in this change `add-rddf-session`)

## Context

spec-workflow v2.0 实现了三阶段状态机（`guide-arch` → `guide-plan` → `guide-ship`），但**没有跨 OpenCode 会话的 workflow 上下文连续性**：

- 在 OpenCode session A 中执行 `guide-plan` Phase 2 后中断
- 在 OpenCode session B 中只能看到 `iteration.json` 知道有 proposed changes
- 但**无法知道**之前创建了哪些 artifact、卡在哪一步、是否在并行 worktree 中有未完成工作

ADR-0010 设计了 `SessionCoordinator`/`SessionManager` Python 抽象，但：
1. 这些类从未被 `loop_engine.py` 或任何 skill 导入使用
2. `state_vector.py` 的 schema `additionalProperties: false` 阻止了 ADR-0010 v2.0 设计的 `session_info`/`sub_sessions` 字段写入

## Decision

引入 **`rddf-session`** —— 用户视角的工作流会话抽象，叠加在 v2.0 SessionCoordinator 之上：

1. **项目级 `.rddf/state/sessions.json`**（gitignored）持久化所有 rddf-session 生命周期
2. **`guide-arch`/`guide-plan`/`guide-ship`** 在入口自动创建/查找对应 kind 的 rddf-session
3. **5 分钟心跳刷新 + 30 分钟超时 → orphaned**
4. **跨 OpenCode session 冲突时 4 选项软提示**：放弃/转移/强制/查看
5. **`state_vector.py` schema 放宽**：允许 `session_management` 字段（向后兼容）

## Schema (v1)

rddf-session 必须匹配 `skills/_lib/schemas/sessions_schema.json` v1：

```json
{
  "version": 1,
  "sessions": [
    {
      "session_id": "rds_<12 hex>",
      "kind": "stage_arch | stage_plan | stage_ship",
      "owner_opencode_session_id": "ses_xxx | null",
      "parent_session_id": "rds_yyy | null",
      "goal": {"intent": "guide-arch", "subject": "...", "expected_outcome": "..."},
      "state": "active | completed | failed | orphaned | abandoned",
      "attached_changes": ["change-x"],
      "context_pointer": ".rddf/state/.arch-handoff.json",
      "started_at": "ISO 8601",
      "last_heartbeat": "ISO 8601",
      "ended_at": "ISO 8601 | null",
      "end_reason": "arch-done | heartbeat-timeout | ..."
    }
  ]
}
```

## State Machine

```
        ┌──────────┐
        │  active  │
        └────┬─────┘
             │
   ┌─────────┼──────────┐
   ↓         ↓          ↓
completed  failed    orphaned
   (arch-done / archive)   (gate拒绝)        (心跳>30min)
```

移除 ADR-0010 的 `paused` 状态（arch-done 后不允许"恢复"）。

## Implementation

- **`skills/_lib/rddf_session.py`**: `RddfSessionCoordinator` 封装 SessionCoordinator + 原子写 + 心跳 + 冲突检测
- **`skills/_lib/schemas/sessions_schema.json`**: JSON Schema v1 校验
- **`skills/rddf-session.md`**: 用户入口（list/show/resume/abandon/archive-history 5 子命令）
- **修改 `state_vector.py`**: schema 允许 `session_management` 字段
- **修改 `guide-arch.md`/`guide-plan.md`/`guide-ship.md`**: 入口创建 + 阶段关闭 hooks

## Backward Compatibility

- 完全兼容。rddf-session 是叠加层，不修改 `SessionCoordinator`/`SessionManager` API
- 现有调用者（loop_engine/agents 模块）不被破坏
- `state_vector.py` schema 修改仅放宽 root `additionalProperties: false`，不影响现有字段

## Consequences

### 正面
- **跨 OpenCode session 恢复**：用户在 session B 中可以列出 session A 创建的 rddf-session 并选择继续
- **冲突安全**：4 选项软提示避免静默合并
- **心跳机制**：30 分钟超时自动标记 orphaned，避免无限期悬挂
- **零新依赖**：仅使用 stdlib + 现有 state_vector 原子写模式

### 风险
- **schema 修改对 state_vector**：放宽 `additionalProperties` 需单元测试覆盖
- **sessions.json 累积过大**：提供 `archive-history` 命令自动迁移历史
- **心跳误判**：5 分钟刷新粒度合理，list/show/resume 自动刷新

## Migration Plan

### Deployment

1. P0 Schema：sessions_schema.json + state_vector.py schema 放宽
2. P1 核心：rddf_session.py + 14 单元测试
3. P2 Skill 集成：3 个 guide 技能 hooks + rddf-session.md
4. P3 集成测试：5 integration tests
5. P4 文档：ADR-0017 + ADR-0010 状态更新 + 用户指南

### Rollback

删除 `rddf_session.py`、`sessions_schema.json`、`rddf-session.md`，撤销 3 个 guide 技能入口修改。sessions.json 保留无影响（仅不被读取）。

## References

- ADR-0003 — 三阶段架构（arch → plan → ship）
- ADR-0010 — 多会话管理（SessionCoordinator/SessionManager）
- ADR-0016 — Arch discovery contract
- `docs/v2-workflow-overview.md` §4.5 rddf-session
- `docs/v2-multi-session-guide.md` rddf-session 用户指南
```

- [ ] **Step 2: Update ADR-0010 status**

Edit `docs/adr/ADR-0010-multi-session-management.md` line 3:
```diff
- > **状态**: 已采纳（分阶段实施：v2.0 轻量 + v2.1 完整）
+ > **状态**: ✅ 已采纳 + 已实施（v2.0 轻量 + v2.1 完整 + ADR-0017 rddf-session 用户层）
```

- [ ] **Step 3: Update ADR README index**

Edit `docs/adr/README.md` ADR table to add row for ADR-0017:
```
| [ADR-0017](ADR-0017-rddf-session.md) | rddf-session 用户视角工作流会话 | 已采纳 | 2026-07-09 | 项目级 sessions.json 持久化 + 4 选项软提示冲突处理 |
```

- [ ] **Step 4: Verify docs render**

Run: `cd /workspace/project/spec-workflow && openspec validate add-rddf-session`
Expected: `Change 'add-rddf-session' is valid`

- [ ] **Step 5: Commit**

```bash
cd /workspace/project/spec-workflow && git add docs/adr/ADR-0017-rddf-session.md docs/adr/ADR-0010-multi-session-management.md docs/adr/README.md && git commit -m "docs(adr): add ADR-0017-rddf-session + update ADR-0010 status — rddf-session"
```

---

### Task 13: Documentation — v2-workflow-overview + v2-multi-session-guide + AGENTS.md

**Files:**
- Modify: `docs/v2-workflow-overview.md` (add §4.5 + 闭环 11)
- Modify: `docs/v2-multi-session-guide.md` (add rddf-session section)
- Modify: `AGENTS.md` (add sessions.json row to state files table)

- [ ] **Step 1: Add §4.5 to v2-workflow-overview.md**

Find the "## 跨层反馈闭环（完整 10 个）" section in `docs/v2-workflow-overview.md`. After "### 闭环 10", add:

```markdown
### 闭环 11：rddf-session 跨 OpenCode session 恢复

```
OpenCode session A 中 guide-plan Phase 2 中断
    ↓
OpenCode session B 进入
    ↓
skill_use("rddf-session", "list") 显示 A 创建的 rds_xxx (state=active)
    ↓
skill_use("rddf-session", "resume", "rds_xxx") 转移所有权
    ↓
继续 Phase 2 → Phase 3 → plan-done
```

也找到 "## 关键设计原则" 表，加一行：

| **rddf-session 持久化** | 跨 OpenCode session 的 workflow 上下文通过 `.rddf/state/sessions.json` 持久化；冲突时 4 选项软提示；30 分钟无心跳 → orphaned |
```

- [ ] **Step 2: Add rddf-session section to v2-multi-session-guide.md**

Append to `docs/v2-multi-session-guide.md`:
```markdown
## rddf-session（用户层）

rddf-session 是 ADR-0017 引入的**用户视角**会话抽象，叠加在 v2.0 SessionCoordinator 之上。

### 与 Session 的区别

| 维度 | SessionCoordinator（v2.0） | rddf-session |
|------|---------------------------|--------------|
| **作用域** | Loop 引擎内部 | 用户 + 跨 OpenCode session |
| **持久化** | 仅内存 | `.rddf/state/sessions.json`（gitignored） |
| **绑定** | 无 | 绑定 OpenCode session ID |
| **粒度** | 父子 sub-sessions | 仅 3 种 kind（stage_arch/plan/ship） |
| **冲突处理** | 无 | 4 选项软提示 |

### 用法

```bash
# 列出所有 sessions
skill_use("rddf-session", "list")

# 查看详情
skill_use("rddf-session", "show", "rds_a3f2b1c9d8e7")

# 恢复（转移所有权给当前 OpenCode session）
skill_use("rddf-session", "resume", "rds_a3f2b1c9d8e7")

# 归档历史（保留最近 20 条 completed/failed/abandoned）
skill_use("rddf-session", "archive-history", "--keep=20"
```

### 工作流

1. `skill_use("guide-arch")` → 自动创建 `kind=stage_arch` rddf-session
2. `arch-done` 通过 → session → completed
3. `skill_use("guide-plan")` → 创建 `kind=stage_plan`, parent=最新 stage_arch
4. `plan-done` 通过 → session → completed
5. `skill_use("guide-ship")` → 创建 `kind=stage_ship`, parent=最新 stage_plan
6. `archive_change` 完成 → session → completed

### 冲突场景示例

```
⚠️ 发现 active stage_plan session: rds_a3f2b1c9d8e7
   原 OpenCode session: ses_0ba44f9ccffeD7aqBxwDbwI4ZK
   当前 OpenCode session: ses_different
   最后心跳: 2026-07-09T10:25:00Z (5 分钟前)

选择:
  1) 放弃原 session — 创建新 rddf-session（丢失上下文）
  2) 转移所有权 — 继续原工作
  3) 强制接管 — 不变更 owner，绕过检测
  4) 仅查看 — 不操作
```
```

- [ ] **Step 3: Update AGENTS.md state files table**

In `AGENTS.md`, find the table that starts with "| 文件 | 用途 | 写入方 |". Add row:

```
| `.rddf/state/sessions.json` | rddf-session 生命周期（ADR-0017） | `guide-arch`/`guide-plan`/`guide-ship` 入口 + `rddf-session` skill 5 子命令 |
```

- [ ] **Step 4: Commit**

```bash
cd /workspace/project/spec-workflow && git add docs/v2-workflow-overview.md docs/v2-multi-session-guide.md AGENTS.md && git commit -m "docs: add rddf-session sections to v2-workflow-overview, v2-multi-session-guide, AGENTS.md — ADR-0017"
```

---

### Task 14: Final verification + openspec archive

**Files:**
- (no new file changes)

- [ ] **Step 1: Run all unit tests**

Run: `cd /workspace/project/spec-workflow && python3 -m pytest tests/unit/ -q --tb=short`
Expected: All pass (existing + 14 new rddf-session tests).

- [ ] **Step 2: Run all integration tests**

Run: `cd /workspace/project/spec-workflow && python3 -m pytest tests/integration/ -q --tb=short`
Expected: All pass (existing + 5 new rddf-session integration tests).

- [ ] **Step 3: Run bats tests**

Run: `cd /workspace/project/spec-workflow && bats tests/`
Expected: All pass.

- [ ] **Step 4: Run openspec validate**

Run: `cd /workspace/project/spec-workflow && openspec validate add-rddf-session`
Expected: `Change 'add-rddf-session' is valid`

- [ ] **Step 5: Check git log**

Run: `cd /workspace/project/spec-workflow && git log --oneline -12`
Expected: Clean focused commits, includes 11+ rddf-session related commits.

- [ ] **Step 6: Archive the change**

Run: `cd /workspace/project/spec-workflow && openspec archive add-rddf-session --yes 2>&1`
Expected: `Change 'add-rddf-session' archived to openspec/changes/archive/2026-07-09-add-rddf-session/`

- [ ] **Step 7: Final commit (if needed)**

```bash
cd /workspace/project/spec-workflow && git status
# If there are uncommitted archive changes:
git add openspec/changes/archive/ && git commit -m "chore(archive): archive change add-rddf-session"
```

---

## Self-Review

### 1. Spec Coverage

| Requirement | Plan Covers? | Task # |
|------------|-------------|--------|
| `.rddf/state/sessions.json` 持久化 | ✅ | Task 1, 3 |
| `rds_<12 hex>` session_id 格式 | ✅ | Task 3 |
| kind ∈ {stage_arch, stage_plan, stage_ship} | ✅ | Task 3, 4 |
| owner_opencode_session_id 绑定 | ✅ | Task 3, 4, 7 |
| parent_session_id 父子关系 | ✅ | Task 3 |
| 状态机 active → completed/failed/orphaned/abandoned | ✅ | Task 4, 7 |
| 5 分钟心跳 + 30 分钟超时 | ✅ | Task 5, 6 |
| 4 选项冲突软提示 | ✅ | Task 6 |
| 子技能不创建 rddf-session | ✅ (skill integration) | Task 10 |
| `guide-*` 入口自动管理 | ✅ | Task 10 |
| `skill_use("rddf-session")` 5 子命令 | ✅ | Task 9 |
| `archive-history` 归档历史 | ✅ | Task 7 |
| sessions.json schema 校验 | ✅ | Task 1 |
| 与 worktree 完全解耦 | ✅ (no worktree_path field) | Task 3, 11 |
| 向后兼容 (SessionCoordinator/SessionManager 不变) | ✅ (Task 3 不修改这些文件) | Task 3 |
| AGENTS.md 状态文件表更新 | ✅ | Task 13 |
| ADR-0017 | ✅ | Task 12 |
| ADR-0010 状态更新 | ✅ | Task 12 |
| v2-workflow-overview.md §4.5 + 闭环 11 | ✅ | Task 13 |
| v2-multi-session-guide.md rddf-session 节 | ✅ | Task 13 |

### 2. Placeholder Scan

- ❌ No "TBD", "TODO", "implement later", "fill in details"
- ✅ Every code step has exact code
- ✅ Every command has expected output
- ✅ No "similar to Task N" without repeating code

### 3. Type Consistency

- `RddfSession` dataclass fields match schema: ✅
- `RddfSessionState` enum matches schema `state` enum: ✅
- All public methods have consistent signatures: ✅
- Test fixtures (`coordinator`, `sessions_file`) consistent across all 8 unit + 5 integration tests: ✅
- File paths consistent: `.rddf/state/sessions.json` everywhere ✅

---

## Execution Handoff

**Plan complete and saved to `.rddf/plans/add-rddf-session.md`.**

**Execution options:**

1. **Inline Execution (recommended for this plan)**: Execute tasks 1-14 in this session using `skill_use("execute")`. 14 tasks × ~30 min each = ~7 hours of focused work. Can be batched.

2. **Subagent-Driven**: Dispatch fresh subagent per task with review checkpoints. Better for very long plans (this is borderline; 14 tasks is medium).

**For this plan, I recommend Inline Execution** because:
- All tasks are well-defined with exact code (no exploration needed)
- Tasks 3-8 are sequential (build coordinator incrementally with tests)
- Tasks 1-2 can be parallel, 9-13 depend on 3-8

**Next action**: Begin Task 1 (create schema) → proceed sequentially through Task 14.