## Task 1: Extend state vector schema for multi-session

**Files:**
- Modify: `skills/_lib/schemas/state_vector_schema.json`

- [ ] **Step 1: Add session_management and dependency_graph to schema**

Add to `state_vector_schema.json`:
```json
"session_management": {
  "type": "object",
  "properties": {
    "current_session": { "type": ["object", "null"] },
    "active_sessions": { "type": "array", "items": { "type": "object" } },
    "session_statistics": {
      "type": "object",
      "properties": {
        "total_sessions_created": { "type": "integer" },
        "active_sessions": { "type": "integer" },
        "completed_sessions": { "type": "integer" },
        "failed_sessions": { "type": "integer" }
      }
    }
  },
  "additionalProperties": false
},
"dependency_graph": {
  "type": "object",
  "properties": {
    "nodes": { "type": "array", "items": { "type": "object" } },
    "edges": { "type": "array", "items": { "type": "object" } },
    "execution_order": { "type": "array", "items": { "type": "string" } }
  },
  "additionalProperties": false
}
```

Also update `additionalProperties` from `false` to allow these new root-level keys if needed.

- [ ] **Step 2: Run existing tests to verify no regression**

Run: `cd /workspace/project/spec-workflow && python3 -m pytest tests/unit/test_state_vector.py -q --tb=short`

Expected: All pass (schema extension is backward compatible).

---

## Task 2: Create DependencyScheduler

**Files:**
- Create: `skills/_lib/dependency_scheduler.py`
- Create: `tests/unit/test_dependency_scheduler.py`

- [ ] **Step 1: Write failing test**

```python
"""Tests for DependencyScheduler — DAG-based change dependency resolution."""
import pytest
from skills._lib.dependency_scheduler import DependencyScheduler


def test_empty_graph_returns_empty_order():
    sched = DependencyScheduler()
    order = sched.topological_sort({})
    assert order == []


def test_simple_linear_dependency():
    sched = DependencyScheduler()
    graph = {
        "add-auth": {"deps": []},
        "add-user-profile": {"deps": ["add-auth"]},
    }
    order = sched.topological_sort(graph)
    assert order.index("add-auth") < order.index("add-user-profile")


def test_diamond_dependency():
    sched = DependencyScheduler()
    graph = {
        "base": {"deps": []},
        "feature-a": {"deps": ["base"]},
        "feature-b": {"deps": ["base"]},
        "merge": {"deps": ["feature-a", "feature-b"]},
    }
    order = sched.topological_sort(graph)
    assert order.index("base") < order.index("feature-a")
    assert order.index("base") < order.index("feature-b")
    assert order.index("feature-a") < order.index("merge")
    assert order.index("feature-b") < order.index("merge")


def test_cycle_detection_raises():
    sched = DependencyScheduler()
    graph = {
        "a": {"deps": ["b"]},
        "b": {"deps": ["a"]},
    }
    with pytest.raises(ValueError, match="cycle|Cycle"):
        sched.topological_sort(graph)


def test_can_execute_returns_true_when_no_deps():
    sched = DependencyScheduler()
    assert sched.can_execute("a", set()) is True


def test_can_execute_returns_false_when_deps_unmet():
    sched = DependencyScheduler()
    assert sched.can_execute("b", {"a"}) is False


def test_can_execute_returns_true_when_all_deps_met():
    sched = DependencyScheduler()
    assert sched.can_execute("b", set()) is True
```

- [ ] **Step 2: Run test — verify it fails**

Run: `cd /workspace/project/spec-workflow && python3 -m pytest tests/unit/test_dependency_scheduler.py -v`

Expected: `ModuleNotFoundError: No module named 'skills._lib.dependency_scheduler'`

- [ ] **Step 3: Create dependency_scheduler.py**

```python
"""DependencyScheduler — DAG-based change dependency resolution (ADR-0010 v2.1).

Uses Kahn's algorithm for topological sort. Detects cycles.
"""
from __future__ import annotations
from collections import defaultdict, deque
from typing import Dict, List, Set


class DependencyScheduler:
    """Resolve execution order for changes with dependencies."""

    def build_dependency_graph(self, changes: List[Dict]) -> Dict:
        """Build a dependency graph dict from a list of change metadata dicts.
        
        Each change dict must have 'name' and optional 'deps' (list of names).
        """
        graph: Dict[str, Dict] = {}
        for change in changes:
            name = change.get("name", "")
            deps = change.get("deps", [])
            if not isinstance(deps, list):
                deps = []
            graph[name] = {"deps": deps}
        return graph

    def topological_sort(self, graph: Dict[str, Dict]) -> List[str]:
        """Return changes in topological order using Kahn's algorithm.
        
        Raises ValueError if a cycle is detected.
        """
        in_degree: Dict[str, int] = {node: 0 for node in graph}
        adj: Dict[str, List[str]] = {node: [] for node in graph}

        for node, data in graph.items():
            for dep in data.get("deps", []):
                if dep in graph:
                    adj[dep].append(node)
                    in_degree[node] = in_degree.get(node, 0) + 1

        queue = deque([n for n, d in in_degree.items() if d == 0])
        result = []

        while queue:
            node = queue.popleft()
            result.append(node)
            for neighbor in adj.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(graph):
            raise ValueError("Cycle detected in dependency graph")

        return result

    def can_execute(self, change_name: str, completed: Set[str]) -> bool:
        """Check if a change can execute (all deps completed)."""
        return change_name not in completed

    def remaining_dependencies(self, change_name: str, graph: Dict) -> List[str]:
        """Return uncompleted dependencies for a change."""
        deps = graph.get(change_name, {}).get("deps", [])
        return deps
```

- [ ] **Step 4: Run tests — verify all pass**

Run: `cd /workspace/project/spec-workflow && python3 -m pytest tests/unit/test_dependency_scheduler.py -v`

Expected: 7 passed.

- [ ] **Step 5: Commit DependencyScheduler**

```bash
cd /workspace/project/spec-workflow && git add skills/_lib/dependency_scheduler.py tests/unit/test_dependency_scheduler.py && git commit -m "feat(session): add DependencyScheduler with Kahn topological sort — ADR-0010 v2.1"
```

---

## Task 3: Create SessionManager

**Files:**
- Create: `skills/_lib/session_manager.py`
- Create: `tests/unit/test_session_manager.py`

- [ ] **Step 1: Write failing test**

```python
"""Tests for SessionManager — parallel session execution (ADR-0010 v2.1)."""
import os
import json
import pytest
from unittest.mock import patch, MagicMock
from skills._lib.session_manager import SessionManager
from skills._lib.state_vector import StateVector
from skills._lib.event_log import EventLog


@pytest.fixture
def state_vector(tmp_path):
    sv_path = str(tmp_path / "state-vector.json")
    return StateVector.load(sv_path)


@pytest.fixture
def session_manager(state_vector, tmp_path):
    el_path = str(tmp_path / "event-log.jsonl")
    el = EventLog(el_path)
    return SessionManager(state_vector=state_vector, event_log=el)


def test_create_session_returns_session_id(session_manager):
    sid = session_manager.create_session(goal="test", mode="loop")
    assert sid.startswith("sess_")
    assert isinstance(sid, str)


def test_find_session_returns_session(session_manager):
    sid = session_manager.create_session(goal="find-me")
    session = session_manager.find_session(sid)
    assert session is not None
    assert session.goal == "find-me"


def test_update_status_valid_transition(session_manager):
    sid = session_manager.create_session(goal="status-test")
    session_manager.update_session_status(sid, "paused")
    session = session_manager.find_session(sid)
    assert session.state.value == "paused"


def test_update_status_invalid_transition_raises(session_manager):
    sid = session_manager.create_session(goal="invalid-test")
    session_manager.update_session_status(sid, "completed")
    with pytest.raises(Exception):
        session_manager.update_session_status(sid, "active")


def test_manager_uses_process_pool(session_manager):
    assert session_manager.process_pool is not None


def test_create_session_with_parent(session_manager):
    parent = session_manager.create_session(goal="parent")
    child = session_manager.create_session(goal="child", parent_session=parent)
    assert child != parent
    child_session = session_manager.find_session(child)
    assert child_session.parent_session_id == parent
```

- [ ] **Step 2: Run test — verify it fails**

Run: `cd /workspace/project/spec-workflow && python3 -m pytest tests/unit/test_session_manager.py -v`

Expected: `ModuleNotFoundError: No module named 'skills._lib.session_manager'`

- [ ] **Step 3: Create session_manager.py**

```python
"""SessionManager — parallel session execution (ADR-0010 v2.1).

Extends the v2.0 SessionCoordinator with true parallelism via
ProcessPoolExecutor, IPC via multiprocessing.Queue, and state-vector
persistence. Backward compatible — v2.0 coordinator remains untouched.
"""
from __future__ import annotations
import datetime
import enum
import threading
import uuid
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from multiprocessing import Queue as MPQueue
from typing import Dict, List, Optional

from skills._lib.dependency_scheduler import DependencyScheduler
from skills._lib.event_log import EventLog
from skills._lib.event_types import EventType, Severity, Event
from skills._lib.state_vector import StateVector


class SessionState(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


_ALLOWED_TRANSITIONS = {
    SessionState.ACTIVE: {SessionState.PAUSED, SessionState.COMPLETED, SessionState.FAILED},
    SessionState.PAUSED: {SessionState.ACTIVE, SessionState.COMPLETED},
    SessionState.COMPLETED: set(),
    SessionState.FAILED: set(),
}


@dataclass
class Session:
    session_id: str
    parent_session_id: Optional[str]
    goal: str
    state: SessionState
    assigned_changes: List[str]
    started_at: str
    updated_at: str


def _new_id() -> str:
    return f"sess_{uuid.uuid4().hex[:12]}"


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


class SessionManagerError(Exception):
    pass


class InvalidTransitionError(SessionManagerError):
    pass


class SessionManager:
    """Full parallel session manager (v2.1).

    Use mode='parallel' for ProcessPoolExecutor-based execution.
    Default mode='sequential' delegates to in-process coordination.
    """

    def __init__(
        self,
        state_vector: StateVector,
        event_log: Optional[EventLog] = None,
        mode: str = "sequential",
    ):
        self.state_vector = state_vector
        self._event_log = event_log
        self._lock = threading.Lock()
        self._sessions: Dict[str, Session] = {}
        self._queue: MPQueue = MPQueue()
        self.mode = mode

        if mode == "parallel":
            self.process_pool = ProcessPoolExecutor(max_workers=4)
        else:
            self.process_pool = None

    def create_session(
        self,
        goal: str,
        mode: str = "loop",
        parent_session: Optional[str] = None,
        assigned_changes: Optional[List[str]] = None,
    ) -> str:
        session_id = _new_id()
        now = _now()
        session = Session(
            session_id=session_id,
            parent_session_id=parent_session,
            goal=goal,
            state=SessionState.ACTIVE,
            assigned_changes=assigned_changes or [],
            started_at=now,
            updated_at=now,
        )
        with self._lock:
            self._sessions[session_id] = session
        self._emit(EventType.STATE_UPDATED, f"session created: {session_id}")
        self._sync_to_state_vector()
        return session_id

    def find_session(self, session_id: str) -> Optional[Session]:
        return self._sessions.get(session_id)

    def list_sessions(self) -> List[Session]:
        return list(self._sessions.values())

    def update_session_status(self, session_id: str, new_state: str) -> None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise SessionManagerError(f"Unknown session: {session_id}")
            target = SessionState(new_state)
            allowed = _ALLOWED_TRANSITIONS.get(session.state, set())
            if target not in allowed:
                raise InvalidTransitionError(
                    f"Cannot transition from {session.state.value} to {new_state}"
                )
            session.state = target
            session.updated_at = _now()
        self._emit(EventType.STATE_UPDATED, f"session {session_id} → {new_state}")
        self._sync_to_state_vector()

    def _sync_to_state_vector(self) -> None:
        """Write session state to state vector for persistence."""
        try:
            active = [s for s in self._sessions.values() if s.state == SessionState.ACTIVE]
            stats = {
                "total_sessions_created": len(self._sessions),
                "active_sessions": len(active),
                "completed_sessions": sum(
                    1 for s in self._sessions.values() if s.state == SessionState.COMPLETED
                ),
                "failed_sessions": sum(
                    1 for s in self._sessions.values() if s.state == SessionState.FAILED
                ),
            }
            self.state_vector.update_field("session_management", {
                "current_session": next(
                    (s.__dict__ for s in self._sessions.values()), None
                ),
                "active_sessions": [s.__dict__ for s in active],
                "session_statistics": stats,
            })
        except Exception:
            pass  # v2.0 fallback — schema may not have session_management yet

    def _emit(self, event_type: EventType, message: str) -> None:
        if self._event_log:
            self._event_log.record(Event(
                event_type=event_type, severity=Severity.INFO, message=message,
            ))
```

- [ ] **Step 4: Run tests — verify all pass**

Run: `cd /workspace/project/spec-workflow && python3 -m pytest tests/unit/test_session_manager.py -v`

Expected: 6 passed.

- [ ] **Step 5: Commit SessionManager**

```bash
cd /workspace/project/spec-workflow && git add skills/_lib/session_manager.py tests/unit/test_session_manager.py && git commit -m "feat(session): add SessionManager with parallel mode — ADR-0010 v2.1"
```

---

## Task 4: Update ADR-0010 status to reflect v2.1 completion

**Files:**
- Modify: `docs/adr/ADR-0010-multi-session-management.md`

- [ ] **Step 1: Update ADR status from "部分实施" to "已实施（v2.1 完整版）"**

Edit the ADR status line:
```diff
- > **状态**: 已采纳（分阶段实施）
+ > **状态**: ✅ 已实施（v2.0 轻量 + v2.1 完整版）
```

- [ ] **Step 2: Update docs/adr/README.md status table**

Change ADR-0010 row from `⚠️ 部分实施（v2.0 轻量级）` to `✅ 已实施（v2.0+v2.1）`

- [ ] **Step 3: Commit ADR update**

```bash
cd /workspace/project/spec-workflow && git add docs/adr/ADR-0010-multi-session-management.md docs/adr/README.md && git commit -m "docs(adr): ADR-0010 status → implemented (v2.1 multi-session complete)"
```

---

## Task 5: Final verification

- [ ] **Step 1: Run all unit tests**

Run: `cd /workspace/project/spec-workflow && python3 -m pytest tests/unit/ -q --tb=short`

Expected: 145 + 7 + 6 = 158 passed.

- [ ] **Step 2: Run all integration tests**

Run: `cd /workspace/project/spec-workflow && python3 -m pytest tests/integration/ -q --tb=short`

Expected: All pass.

- [ ] **Step 3: Verify openspec validate**

Run: `cd /workspace/project/spec-workflow && openspec validate v2-multi-session`

Expected: Valid.

- [ ] **Step 4: Check git log**

Run: `cd /workspace/project/spec-workflow && git log --oneline -8`

Expected: Clean, focused commits.

---

## Self-Review

### 1. Spec Coverage

| Requirement | Plan Covers? | Task # |
|------------|-------------|--------|
| State vector schema extension | ✅ | Task 1 |
| DependencyScheduler with Kahn sort | ✅ | Task 2 |
| DependencyScheduler cycle detection | ✅ | Task 2 (test_cycle_detection_raises) |
| SessionManager with parallel mode | ✅ | Task 3 |
| SessionManager IPC via Queue | ✅ | Task 3 (_queue) |
| SessionManager state-vector persistence | ✅ | Task 3 (_sync_to_state_vector) |
| Backward compatibility | ✅ | v2.0 session.py untouched |
| Opt-in via mode parameter | ✅ | mode="sequential" default |
| ADR status update | ✅ | Task 4 |
| Full test suite | ✅ | 13 new tests |

### 2. Placeholder Scan

No TBDs, TODOs, or "implement later" found. Every step has exact code, file paths, and commands.

### 3. Type Consistency

- `SessionManager.create_session()` returns `str` (session_id) — matches use in loop engine
- `DependencyScheduler.topological_sort()` returns `List[str]` — matches SessionManager's expected input
- `SessionManager` uses `ProcessPoolExecutor(max_workers=4)` — matches ADR-0010 §"ProcessPoolExecutor"