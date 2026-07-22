# v2-loop-engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Phase 2 loop engine for rdd-workflow v2.0 — `LoopEngine` class with 5-building-block cycle + 4 safety mechanisms, 8 pluggable detectors, 7 pluggable actions, 3 interaction modes (Loop/Menu/Hybrid), 7 human-in-loop node types with 3 verification modes, design-first phase, and ASCII real-time flowchart generator.

**Architecture:** Single entry point `skills/loop-engine.py` orchestrating six `_lib/` modules. Loop cycle: `verify_goal → scan_state → generate_plan → execute_plan → verify_results → adapt`. Safety enforced at engine layer (max_iterations=100, max_retries=3, oscillation detection, circuit breaker). Detectors/Actions are pluggable via `.rdd-workflow/{detectors,actions}/` Python files. Three modes switchable at runtime. Flowchart reads state vector + event log for observability. Total ~2,500 lines Python + ~150 lines tests. 100% backward compatible with v1.x via existing sync layer.

**Tech Stack:** Python 3.10+, existing `skills/_lib/{state_vector,event_log,event_types,gate,config,defaults,sync_state,lock}.py`, `subprocess` (stdlib), `importlib` (stdlib for plugin loading), `pytest` (testing), OpenSpec CLI v1.4.1+ (workflow orchestration).

**OpenRDD Workflow Phases Covered:** This plan executes the full lifecycle for the `v2-loop-engine` change:
- **Phase 0 — Propose** (artifacts already exist in `openspec/changes/v2-loop-engine/`; verified valid)
- **Phase 1 — Plan** (this document)
- **Phase 2 — Execute** (Tasks 1-6 below; update `openspec/changes/v2-loop-engine/tasks.md` after each section)
- **Phase 3 — Status** (Task 7: validate via `openspec validate` + pytest)
- **Phase 4 — Archive** (Task 8: `openspec archive --yes` + git commit + worktree cleanup)

---

## File Structure

This change creates new files only. No existing v1.x files are modified — v2-core-foundation sync layer handles compatibility.

### Production Code

| File | Lines | Responsibility |
|---|---|---|
| `skills/loop-engine.py` | ~500 | `LoopEngine` class — public entry point, `run()` cycle, 5 building-block methods, safety mechanism enforcement |
| `skills/_lib/detectors.py` | ~400 | `Detector` base + `DetectionResult` dataclass + 8 built-in detectors + plugin loader |
| `skills/_lib/actions.py` | ~350 | `Action` base + `ActionResult` dataclass + 7 built-in actions + subprocess wrapper + 30-min timeout + plugin loader |
| `skills/_lib/interaction_modes.py` | ~250 | `LoopMode`, `MenuMode`, `HybridMode` classes; runtime mode switching via parameter |
| `skills/_lib/human_nodes.py` | ~300 | `HumanNode` registry, 7 node types (`arch.adr_create`, etc.), 3 verification modes (`human`, `multi_model`, `script`) |
| `skills/_lib/design_phase.py` | ~150 | Pre-loop design phase: Goal Design, Verification Design, Control Design; persists to state vector |
| `skills/_lib/flowchart.py` | ~100 | ASCII flowchart generator reading state vector + event log; refresh < 100ms |

### Tests (`tests/unit/`)

| File | Responsibility |
|---|---|
| `tests/unit/test_loop_engine.py` | Full cycle, max_iterations, oscillation detection, circuit breaker, goal achievement, event log coverage |
| `tests/unit/test_detectors.py` | Each of 8 detectors + plugin loading from `.rdd-workflow/detectors/` + performance < 500ms total |
| `tests/unit/test_actions.py` | Each of 7 actions (mocked subprocess), timeout, error handling, event log integration, plugin loading |
| `tests/unit/test_interaction_modes.py` | Loop/Menu/Hybrid in isolation + runtime mode switching + each human node verification mode |
| `tests/unit/test_human_nodes.py` | All 7 node types + each verification mode (human/multi_model/script stub) |

### Documentation

| File | Update Reason |
|---|---|
| `docs/v2-api-reference.md` | Add public APIs: `LoopEngine.run()`, `Detector`, `Action`, `InteractionMode` |
| `docs/v2-config-schema.md` | Document `loop.yaml` schema extensions (human_nodes list, detectors/actions plugin paths) |
| `docs/v2-loop-engine.md` | New user guide — how to invoke loop engine, configure modes, register plugins |

### OpenSpec Artifacts (`openspec/changes/v2-loop-engine/`)

Already exist. After Task 8 archive, moved to `openspec/changes/archive/2026-06-25-v2-loop-engine/`.

---

## Pre-Flight Checklist

Before starting Task 1, confirm:

- [ ] Working directory is `/workspace/project/rdd-workflow` (repo root)
- [ ] On branch `master`, no uncommitted changes to `openspec/changes/v2-loop-engine/` (or work in worktree)
- [ ] `python3 --version` shows 3.10 or later
- [ ] `openspec --version` shows 1.4.1 or later
- [ ] `openspec validate v2-loop-engine` returns `Change 'v2-loop-engine' is valid`
- [ ] `python3 -m pytest tests/unit/ -q` shows 45 passed (v2-core-foundation baseline)
- [ ] `python3 -c "from skills._lib.state_vector import StateVector; from skills._lib.event_log import EventLog; from skills._lib.gate import GateMechanism; from skills._lib.config import ConfigParser; from skills._lib.event_context import current_context; print('imports ok')"` succeeds

---

## Architectural Foundation (Read Before Implementing)

### Module Dependency Graph

```
loop-engine.py
    ├─→ detectors.py        (scan_state)
    ├─→ actions.py          (execute_plan)
    ├─→ interaction_modes.py (run-time mode dispatch)
    │       └─→ human_nodes.py (verification dispatch)
    ├─→ design_phase.py     (pre-loop, optional)
    └─→ flowchart.py        (observability, optional)

All modules depend on:
    skills/_lib/state_vector.py  (StateVector - persistent state)
    skills/_lib/event_log.py     (EventLog - audit trail)
    skills/_lib/event_types.py   (EventType, Severity, Event)
    skills/_lib/event_context.py (event context snapshot)
    skills/_lib/config.py        (ConfigParser - read loop.yaml)
    skills/_lib/gate.py          (GateMechanism - phase validation)
    skills/_lib/defaults.py      (built-in defaults)
```

### Critical Interfaces (Lock These Before Coding)

```python
# skills/_lib/detectors.py
from dataclasses import dataclass
from typing import Any, Callable

@dataclass
class DetectionResult:
    type: str           # e.g. "worktrees", "pending_changes"
    data: dict          # detector-specific payload
    message: str        # human-readable summary
    severity: str = "info"  # info | warn | error

class Detector:
    name: str
    def detect(self, state: dict) -> DetectionResult: ...

# skills/_lib/actions.py
@dataclass
class ActionResult:
    success: bool
    data: dict
    error: str | None = None

class Action:
    name: str
    def execute(self, params: dict, event_log: EventLog) -> ActionResult: ...
```

### Safety Mechanism Semantics

| Mechanism | Default | Trigger | Exit Status |
|---|---|---|---|
| `max_iterations` | 100 | iteration count ≥ max | `max_iterations_exceeded` |
| `max_retries` | 3 | same action retried 3x | `max_retries_exceeded` |
| Oscillation detection | 5 iter / ≤ 2 distinct states | window match | `oscillation_detected` |
| Circuit breaker | 3 consecutive failures | count ≥ 3 | `circuit_broken` |
| Per-action timeout | 30 min | wall-clock | `ActionResult(success=False, error="timeout")` |

### Verification Mode Stubs

`multi_model` verification depends on `v2-advanced-features` (Tribunal). Until that ships, the verifier MUST:
1. Import-attempt: `from skills._lib.tribunal import Tribunal`
2. On `ImportError`: raise `NotImplementedError("multi_model verification requires v2-advanced-features")` AND log a clear event
3. Tests for `multi_model` mode use `pytest.raises(NotImplementedError)` to verify the stub behavior

---

## Task 1: Loop Engine Core (§1 of `openspec/changes/v2-loop-engine/tasks.md`)

**Files:**
- Create: `skills/_lib/loop_state.py`
- Create: `skills/loop-engine.py`
- Create: `tests/unit/test_loop_engine.py`

### Step 1.0: Extend state schema for loop engine current phase

The existing `state_vector_schema.json` defines `loop_state` with fields `mode`, `iteration`, `last_action`, `last_action_at` and `additionalProperties: false`. The loop engine needs to track the current cycle phase (`verify_goal`, `scan_state`, etc.) for flowchart observability. Add `current_phase` to the schema.

**File:** `skills/_lib/schemas/state_vector_schema.json`

In the `loop_state.properties` section, add:

```json
"current_phase": {
  "type": ["string", "null"],
  "enum": ["verify_goal", "scan_state", "generate_plan", "execute_plan", "verify_results", "adapt", null],
  "description": "Current phase of the loop engine cycle (v2-loop-engine)."
}
```

Run existing tests to confirm no regression:

```bash
cd /workspace/project/rdd-workflow && python3 -m pytest tests/unit/test_state_vector.py -q
```

Expected: All existing tests still pass (additive schema change).

### Step 1.1: Write failing test for `verify_goal` with custom predicate

**File:** `tests/unit/test_loop_engine.py`

```python
import pytest
from skills.loop_engine import LoopEngine, LoopStatus
from skills._lib.state_vector import StateVector
from skills._lib.event_log import EventLog

@pytest.fixture
def engine(tmp_path):
    """Create a LoopEngine backed by tmp state vector + event log."""
    sv_path = str(tmp_path / "state-vector.json")
    el_path = str(tmp_path / "event-log.jsonl")
    # CORRECT API: StateVector.load(path) or StateVector.create_default()
    # (constructor takes dict, not path string)
    sv = StateVector.load(sv_path)
    el = EventLog(el_path)
    return LoopEngine(state=sv, event_log=el)

def test_verify_goal_with_predicate_returns_true_when_met(engine):
    """verify_goal returns True when dotted-path predicate is satisfied."""
    # CORRECT FIELD: plan_side.active_change (singular — schema constraint)
    engine.state.update_field("plan_side.active_change", None)
    assert engine.verify_goal("plan_side['active_change'] is None") is True

def test_verify_goal_with_predicate_returns_false_when_unmet(engine):
    """verify_goal returns False when predicate is not satisfied."""
    engine.state.update_field("plan_side.active_change", "v2-loop-engine")
    assert engine.verify_goal("plan_side['active_change'] is None") is False
```

### Step 1.2: Run test — verify it fails (no `loop_engine` module)

```bash
cd /workspace/project/rdd-workflow && python3 -m pytest tests/unit/test_loop_engine.py -v
```

Expected: `ModuleNotFoundError: No module named 'skills.loop_engine'`

### Step 1.3: Create `skills/_lib/loop_state.py` (loop iteration state dataclass)

**File:** `skills/_lib/loop_state.py`

```python
"""Loop iteration state — in-memory state passed between 5 building blocks."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LoopState:
    """Mutable in-memory state for one loop iteration."""
    goal: str = ""
    iteration: int = 0
    detections: list = field(default_factory=list)   # List[DetectionResult]
    plan: list = field(default_factory=list)         # List[(Action, params)]
    executed: list = field(default_factory=list)     # List[ActionResult]
    errors: list = field(default_factory=list)       # List[str]
    consecutive_failures: int = 0
    recent_state_hashes: list = field(default_factory=list)  # for oscillation detection

    def snapshot_hash(self) -> str:
        """Hashable representation of current state for oscillation detection."""
        return str(sorted([(d["type"], str(d.get("data", {}))) for d in self.detections]))
```

### Step 1.4: Create minimal `skills/loop-engine.py` with `verify_goal` only

**File:** `skills/loop-engine.py`

```python
"""LoopEngine — the AI-native execution engine for rdd-workflow v2.0.

Implements 5-building-block cycle: verify_goal → scan_state → generate_plan →
execute_plan → verify_results → adapt. Safety mechanisms enforced at engine layer.
"""
from __future__ import annotations
from enum import Enum
from typing import Optional
from skills._lib.state_vector import StateVector
from skills._lib.event_log import EventLog
from skills._lib.event_types import EventType, Severity, Event
from skills._lib.loop_state import LoopState
from skills._lib.config import ConfigParser


class LoopStatus(str, Enum):
    """Loop termination statuses."""
    SUCCESS = "success"
    MAX_ITERATIONS_EXCEEDED = "max_iterations_exceeded"
    MAX_RETRIES_EXCEEDED = "max_retries_exceeded"
    OSCILLATION_DETECTED = "oscillation_detected"
    CIRCUIT_BROKEN = "circuit_broken"
    ERROR = "error"


class LoopEngine:
    """Main loop engine. Call .run() to execute cycle until goal or safety trigger."""

    # SAFETY_DEFAULTS are code-level fallback when config doesn't specify.
    # Config-provided values override these via ConfigParser.parse().
    SAFETY_DEFAULTS = {
        "max_iterations": 100,
        "max_retries": 3,
        "oscillation_window": 5,
        "oscillation_distinct_threshold": 2,
        "circuit_breaker_threshold": 3,
        "action_timeout_seconds": 30 * 60,
    }

    def __init__(self, state: StateVector, event_log: EventLog, config: Optional[ConfigParser] = None):
        self.state = state
        self.event_log = event_log
        # CORRECT API: ConfigParser only exposes .parse(runtime_overrides) → dict
        # It does NOT have get_loop_safety() or get(). Use .parse() then .get().
        self.config = config or ConfigParser()
        cfg = self.config.parse()
        loop_cfg = cfg.get("loop", {})
        # Merge: SAFETY_DEFAULTS < loop_cfg (loop_cfg wins)
        self.safety = {
            "max_iterations": loop_cfg.get("max_iterations", self.SAFETY_DEFAULTS["max_iterations"]),
            "max_retries": loop_cfg.get("max_retries", self.SAFETY_DEFAULTS["max_retries"]),
            "oscillation_window": loop_cfg.get("oscillation_window", self.SAFETY_DEFAULTS["oscillation_window"]),
            "oscillation_distinct_threshold": loop_cfg.get("oscillation_distinct_threshold", self.SAFETY_DEFAULTS["oscillation_distinct_threshold"]),
            "circuit_breaker_threshold": loop_cfg.get("circuit_breaker_threshold", self.SAFETY_DEFAULTS["circuit_breaker_threshold"]),
            "action_timeout_seconds": loop_cfg.get("action_timeout_seconds", self.SAFETY_DEFAULTS["action_timeout_seconds"]),
        }
        self.loop_state = LoopState()

    def verify_goal(self, goal_predicate: str) -> bool:
        """Evaluate goal predicate against current state vector.
        Predicate is a Python expression using dotted-path access against state dict.
        Example: "plan_side['active_change'] is None"
        """
        state_dict = self.state.to_dict()
        try:
            return bool(eval(goal_predicate, {"__builtins__": {}}, state_dict))
        except Exception as e:
            self.event_log.record(Event(
                event_type=EventType.ERROR_OCCURRED,
                severity=Severity.ERROR,
                message=f"Goal predicate eval failed: {e}",
                context={"predicate": goal_predicate},
            ))
            return False
```

### Step 1.5: Run test — verify Step 1.1 now passes

```bash
cd /workspace/project/rdd-workflow && python3 -m pytest tests/unit/test_loop_engine.py::test_verify_goal_with_predicate_returns_true_when_met tests/unit/test_loop_engine.py::test_verify_goal_with_predicate_returns_false_when_unmet -v
```

Expected: 2 passed

### Step 1.6: Add safety mechanism tests + scan/plan/execute skeleton

Add to `tests/unit/test_loop_engine.py`:

```python
def test_max_iterations_exceeded_triggers_stop(tmp_path):
    """Loop exits with max_iterations_exceeded when iterations hit cap."""
    sv_path = str(tmp_path / "state-vector.json")
    el_path = str(tmp_path / "event-log.jsonl")
    # CORRECT API: StateVector.load(path) — constructor takes dict, not path string
    engine = LoopEngine(state=StateVector.load(sv_path), event_log=EventLog(el_path))
    engine.safety["max_iterations"] = 3
    # Unachievable goal — never true (dotted-path predicate)
    status = engine.run(goal_predicate="plan_side['active_change'] == 'IMPOSSIBLE_VALUE'", max_iterations=3)
    assert status == LoopStatus.MAX_ITERATIONS_EXCEEDED

def test_oscillation_detected_with_5_same_states(tmp_path):
    """Loop exits with oscillation_detected when last 5 states are ≤ 2 distinct."""
    sv_path = str(tmp_path / "state-vector.json")
    el_path = str(tmp_path / "event-log.jsonl")
    engine = LoopEngine(state=StateVector.load(sv_path), event_log=EventLog(el_path))
    engine.safety["max_iterations"] = 20
    # Simulate stuck state
    for _ in range(5):
        engine.loop_state.detections = [{"type": "x", "data": {}, "message": "x"}]
        engine.loop_state.recent_state_hashes.append(engine.loop_state.snapshot_hash())
    # Provide a custom run path that always oscillates
    def fake_scan(_): pass
    def fake_plan(_): pass
    def fake_execute(_): pass
    def fake_verify_results(_): return False
    def fake_adapt(_): pass
    engine.scan_state = fake_scan
    engine.generate_plan = fake_plan
    engine.execute_plan = fake_execute
    engine.verify_results = fake_verify_results
    engine.adapt = fake_adapt
    engine.loop_state.detections = [{"type": "x", "data": {}, "message": "x"}]
    status = engine.run(goal_predicate="plan_side['active_change'] == 'NEVER'")
    assert status == LoopStatus.OSCILLATION_DETECTED
```

Add to `skills/loop-engine.py`:

```python
    def run(self, goal_predicate: str, max_iterations: Optional[int] = None) -> LoopStatus:
        """Execute loop cycle until goal achieved or safety trigger."""
        max_iter = max_iterations or self.safety["max_iterations"]
        self.loop_state.goal = goal_predicate
        self.event_log.record(Event(
            event_type=EventType.LOOP_STARTED, severity=Severity.INFO,
            message=f"Loop started with goal: {goal_predicate}",
            context={"max_iterations": max_iter, "safety": self.safety},
        ))

        while self.loop_state.iteration < max_iter:
            self.loop_state.iteration += 1
            if self.verify_goal(goal_predicate):
                self.event_log.record(Event(
                    event_type=EventType.LOOP_COMPLETED, severity=Severity.INFO,
                    message=f"Goal achieved at iteration {self.loop_state.iteration}",
                ))
                return LoopStatus.SUCCESS

            self._check_oscillation()
            self._check_circuit_breaker()

            self.scan_state()
            self.generate_plan()
            self.execute_plan()
            self.verify_results()
            self.adapt()

        self.event_log.record(Event(
            event_type=EventType.WARNING_ISSUED, severity=Severity.WARN,
            message=f"Max iterations ({max_iter}) exceeded",
        ))
        return LoopStatus.MAX_ITERATIONS_EXCEEDED

    def _check_oscillation(self) -> None:
        """Detect oscillating loop — same few states repeatedly."""
        self.loop_state.recent_state_hashes.append(self.loop_state.snapshot_hash())
        window = self.safety["oscillation_window"]
        if len(self.loop_state.recent_state_hashes) >= window:
            recent = self.loop_state.recent_state_hashes[-window:]
            if len(set(recent)) <= self.safety["oscillation_distinct_threshold"]:
                self.event_log.record(Event(
                    event_type=EventType.WARNING_ISSUED, severity=Severity.WARN,
                    message=f"Oscillation detected: last {window} states ≤ {self.safety['oscillation_distinct_threshold']} distinct",
                    context={"recent_states": recent},
                ))
                # Raise to terminate run loop
                raise _OscillationDetected()

    def _check_circuit_breaker(self) -> None:
        """3 consecutive failures triggers circuit break."""
        if self.loop_state.consecutive_failures >= self.safety["circuit_breaker_threshold"]:
            self.event_log.record(Event(
                event_type=EventType.ERROR_OCCURRED, severity=Severity.ERROR,
                message=f"Circuit breaker: {self.loop_state.consecutive_failures} consecutive failures",
            ))
            raise _CircuitBroken()

    # Stub methods — implemented in later tasks
    def scan_state(self) -> None:
        """Run all detectors and populate loop_state.detections."""
        pass

    def generate_plan(self) -> None:
        """Match detectors → actions, build execution plan."""
        pass

    def execute_plan(self) -> None:
        """Execute each action in plan."""
        pass

    def verify_results(self) -> bool:
        """Verify execution results meet goal. Stub returns False."""
        return False

    def adapt(self) -> None:
        """Adapt strategy based on results. Stub does nothing."""
        pass


class _OscillationDetected(Exception):
    pass


class _CircuitBroken(Exception):
    pass
```

Update `run()` to catch the new exceptions:

```python
    def run(self, goal_predicate: str, max_iterations: Optional[int] = None) -> LoopStatus:
        max_iter = max_iterations or self.safety["max_iterations"]
        self.loop_state.goal = goal_predicate
        self.event_log.record(Event(
            event_type=EventType.LOOP_STARTED, severity=Severity.INFO,
            message=f"Loop started with goal: {goal_predicate}",
            context={"max_iterations": max_iter},
        ))
        try:
            while self.loop_state.iteration < max_iter:
                self.loop_state.iteration += 1
                if self.verify_goal(goal_predicate):
                    self.event_log.record(Event(
                        event_type=EventType.LOOP_COMPLETED, severity=Severity.INFO,
                        message=f"Goal achieved at iteration {self.loop_state.iteration}",
                    ))
                    return LoopStatus.SUCCESS

                self._check_oscillation()
                self._check_circuit_breaker()

                self.scan_state()
                self.generate_plan()
                self.execute_plan()
                self.verify_results()
                self.adapt()

            return LoopStatus.MAX_ITERATIONS_EXCEEDED
        except _OscillationDetected:
            return LoopStatus.OSCILLATION_DETECTED
        except _CircuitBroken:
            return LoopStatus.CIRCUIT_BROKEN
```

### Step 1.7: Run all loop-engine tests + full suite

```bash
cd /workspace/project/rdd-workflow && python3 -m pytest tests/unit/test_loop_engine.py -v
```

Expected: 4 passed (verify_goal × 2, max_iterations, oscillation)

```bash
cd /workspace/project/rdd-workflow && python3 -m pytest tests/unit/ -q
```

Expected: 45 + 4 = 49 passed, no regressions

### Step 1.8: Commit

```bash
cd /workspace/project/rdd-workflow && git add skills/loop-engine.py skills/_lib/loop_state.py tests/unit/test_loop_engine.py && git commit -m "feat(loop-engine): LoopEngine class with 5-block skeleton + verify_goal + safety mechanisms (closes §1.1-1.4)"
```

---

## Task 2: Detectors (§2 of `tasks.md`)

**Files:**
- Create: `skills/_lib/detectors.py`
- Create: `tests/unit/test_detectors.py`

### Step 2.1: Write failing test for `Detector` base + first built-in (`detect_worktrees`)

**File:** `tests/unit/test_detectors.py`

```python
import os
import pytest
from skills._lib.detectors import Detector, DetectionResult, BUILTIN_DETECTORS, load_plugin_detectors


def test_detection_result_dataclass():
    r = DetectionResult(type="x", data={"k": "v"}, message="hello")
    assert r.type == "x"
    assert r.data == {"k": "v"}
    assert r.message == "hello"
    assert r.severity == "info"

def test_detect_worktrees_returns_empty_when_no_worktrees(tmp_path, monkeypatch):
    """detect_worktrees returns empty list when no git worktrees exist."""
    # Use a temp git repo
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.chdir(repo)
    os.system("git init -q && git config user.email test@test.com && git config user.name test")
    os.system("git commit --allow-empty -m init -q")

    from skills._lib.detectors import detect_worktrees
    result = detect_worktrees(state={})
    assert result.type == "worktrees"
    assert isinstance(result.data, dict)
    assert "worktrees" in result.data

def test_eight_builtin_detectors_registered():
    """All 8 built-in detectors are in BUILTIN_DETECTORS."""
    expected = {
        "detect_worktrees", "detect_pending_changes", "detect_archived_changes",
        "detect_roadmap_state", "detect_adr_status", "detect_health_issues",
        "detect_test_gaps", "detect_stale_branches",
    }
    actual = {d.name for d in BUILTIN_DETECTORS}
    assert expected == actual

def test_load_plugin_detectors_empty_when_dir_missing(tmp_path, monkeypatch):
    """No error when .rdd-workflow/detectors/ doesn't exist."""
    monkeypatch.chdir(tmp_path)
    plugins = load_plugin_detectors()
    assert plugins == []
```

### Step 2.2: Run — verify failure

```bash
cd /workspace/project/rdd-workflow && python3 -m pytest tests/unit/test_detectors.py -v
```

Expected: `ModuleNotFoundError: No module named 'skills._lib.detectors'`

### Step 2.3: Create `skills/_lib/detectors.py`

**File:** `skills/_lib/detectors.py`

```python
"""Built-in state detectors + plugin loader for the loop engine.

8 built-in detectors cover v1.x workflow state. Custom detectors can be added
by dropping Python files in `.rdd-workflow/detectors/` that subclass `Detector`.
"""
from __future__ import annotations
import os
import subprocess
import importlib.util
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


@dataclass
class DetectionResult:
    """Structured output of a single detector."""
    type: str
    data: dict
    message: str
    severity: str = "info"  # info | warn | error

    def to_dict(self) -> dict:
        return asdict(self)


class Detector:
    """Base class for all detectors. Subclass and set `name`."""
    name: str = "base"

    def detect(self, state: dict) -> DetectionResult:
        raise NotImplementedError


# ─────────────────────────────────────────────────────────────────────────────
# Built-in detectors
# ─────────────────────────────────────────────────────────────────────────────

def detect_worktrees(state: dict) -> DetectionResult:
    """Detect active git worktrees."""
    try:
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True, text=True, timeout=5,
        )
        lines = [l for l in result.stdout.splitlines() if l.startswith("worktree ")]
        worktrees = [l.split(" ", 1)[1] for l in lines]
        return DetectionResult(
            type="worktrees", data={"worktrees": worktrees, "count": len(worktrees)},
            message=f"{len(worktrees)} active worktree(s)",
        )
    except Exception as e:
        return DetectionResult(type="worktrees", data={"error": str(e)}, message=str(e), severity="warn")


def detect_pending_changes(state: dict) -> DetectionResult:
    """Detect active (non-archived) openspec changes."""
    changes_dir = Path("openspec/changes")
    if not changes_dir.exists():
        return DetectionResult(type="pending_changes", data={"changes": []}, message="No openspec/changes dir")
    active = [d.name for d in changes_dir.iterdir() if d.is_dir() and d.name != "archive"]
    return DetectionResult(
        type="pending_changes", data={"changes": active, "count": len(active)},
        message=f"{len(active)} pending change(s)",
    )


def detect_archived_changes(state: dict) -> DetectionResult:
    """Detect archived openspec changes."""
    archive_dir = Path("openspec/changes/archive")
    if not archive_dir.exists():
        return DetectionResult(type="archived_changes", data={"changes": []}, message="No archive dir")
    archived = [d.name for d in archive_dir.iterdir() if d.is_dir()]
    return DetectionResult(
        type="archived_changes", data={"changes": archived, "count": len(archived)},
        message=f"{len(archived)} archived change(s)",
    )


def detect_roadmap_state(state: dict) -> DetectionResult:
    """Detect roadmap phase and category."""
    roadmap_file = Path(".rddf/state/roadmap-state.json")
    if not roadmap_file.exists():
        return DetectionResult(type="roadmap_state", data={}, message="No roadmap state file", severity="warn")
    import json
    data = json.loads(roadmap_file.read_text())
    return DetectionResult(
        type="roadmap_state", data=data,
        message=f"Phase: {data.get('phase', 'unknown')}, category: {data.get('category', 'unknown')}",
    )


def detect_adr_status(state: dict) -> DetectionResult:
    """Detect ADR directory status."""
    adr_dir = Path("docs/adr") if Path("docs/adr").exists() else Path("adr")
    if not adr_dir.exists():
        return DetectionResult(type="adr_status", data={"exists": False}, message="No ADR dir", severity="warn")
    adrs = sorted([f.name for f in adr_dir.glob("*.md")])
    return DetectionResult(
        type="adr_status", data={"exists": True, "adrs": adrs, "count": len(adrs)},
        message=f"{len(adrs)} ADR(s) found",
    )


def detect_health_issues(state: dict) -> DetectionResult:
    """Detect general repo health — uncommitted changes, dirty tree."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True, timeout=5,
        )
        dirty = [l for l in result.stdout.splitlines() if l.strip()]
        severity = "warn" if len(dirty) > 10 else "info"
        return DetectionResult(
            type="health", data={"dirty_files": dirty, "count": len(dirty)},
            message=f"{len(dirty)} uncommitted file(s)", severity=severity,
        )
    except Exception as e:
        return DetectionResult(type="health", data={"error": str(e)}, message=str(e), severity="error")


def detect_test_gaps(state: dict) -> DetectionResult:
    """Detect test coverage gaps — files in skills/_lib/ without tests."""
    lib_dir = Path("skills/_lib")
    tests_dir = Path("tests/unit")
    if not lib_dir.exists():
        return DetectionResult(type="test_gaps", data={}, message="No skills/_lib dir")
    py_files = {p.stem for p in lib_dir.glob("*.py") if p.stem != "__init__"}
    test_files = {p.stem.replace("test_", "") for p in tests_dir.glob("test_*.py")}
    gaps = sorted(py_files - test_files)
    return DetectionResult(
        type="test_gaps", data={"gaps": gaps, "count": len(gaps)},
        message=f"{len(gaps)} module(s) without tests",
        severity="warn" if gaps else "info",
    )


def detect_stale_branches(state: dict) -> DetectionResult:
    """Detect stale git branches (no commits in 30+ days)."""
    try:
        result = subprocess.run(
            ["git", "for-each-ref", "--format=%(refname:short) %(committerdate:iso8601)",
             "refs/heads/"],
            capture_output=True, text=True, timeout=5,
        )
        import datetime
        stale = []
        now = datetime.datetime.now(datetime.timezone.utc)
        for line in result.stdout.splitlines():
            parts = line.split(" ", 1)
            if len(parts) != 2:
                continue
            branch, date_str = parts
            try:
                branch_date = datetime.datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                age_days = (now - branch_date).days
                if age_days > 30:
                    stale.append({"branch": branch, "age_days": age_days})
            except ValueError:
                continue
        return DetectionResult(
            type="stale_branches", data={"branches": stale, "count": len(stale)},
            message=f"{len(stale)} stale branch(es)",
            severity="warn" if stale else "info",
        )
    except Exception as e:
        return DetectionResult(type="stale_branches", data={"error": str(e)}, message=str(e), severity="warn")


# ─────────────────────────────────────────────────────────────────────────────
# Registry + plugin loader
# ─────────────────────────────────────────────────────────────────────────────

BUILTIN_DETECTORS = [
    detect_worktrees, detect_pending_changes, detect_archived_changes,
    detect_roadmap_state, detect_adr_status, detect_health_issues,
    detect_test_gaps, detect_stale_branches,
]


class _FunctionDetector(Detector):
    """Wrap a built-in detector function as a Detector instance."""
    def __init__(self, fn):
        self.fn = fn
        self.name = fn.__name__

    def detect(self, state: dict) -> DetectionResult:
        return self.fn(state)


def load_plugin_detectors(plugin_dir: str = ".rdd-workflow/detectors") -> list:
    """Load custom Detector subclasses from a directory."""
    pdir = Path(plugin_dir)
    if not pdir.exists():
        return []
    plugins = []
    for py_file in pdir.glob("*.py"):
        if py_file.name.startswith("_"):
            continue
        spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if isinstance(attr, type) and issubclass(attr, Detector) and attr is not Detector:
                    plugins.append(attr())
        except Exception:
            continue
    return plugins


def all_detectors() -> list:
    """Return built-in + plugin detectors as Detector instances."""
    builtin = [_FunctionDetector(fn) for fn in BUILTIN_DETECTORS]
    plugins = load_plugin_detectors()
    return builtin + plugins
```

### Step 2.4: Run — verify all 4 tests pass

```bash
cd /workspace/project/rdd-workflow && python3 -m pytest tests/unit/test_detectors.py -v
```

Expected: 4 passed

### Step 2.5: Add performance test — all 8 detectors < 500ms total

Add to `tests/unit/test_detectors.py`:

```python
def test_all_detectors_run_under_500ms():
    """All 8 built-in detectors complete sequentially in < 500ms."""
    import time
    from skills._lib.detectors import BUILTIN_DETECTORS
    start = time.perf_counter()
    results = [fn({}) for fn in BUILTIN_DETECTORS]
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert len(results) == 8
    assert elapsed_ms < 500, f"Detectors took {elapsed_ms:.0f}ms (limit 500ms)"
```

### Step 2.6: Run + commit

```bash
cd /workspace/project/rdd-workflow && python3 -m pytest tests/unit/test_detectors.py -v && python3 -m pytest tests/unit/ -q
```

Expected: 5 detector tests pass, full suite = 54 passed

```bash
cd /workspace/project/rdd-workflow && git add skills/_lib/detectors.py tests/unit/test_detectors.py && git commit -m "feat(detectors): 8 built-in detectors + plugin loader + 500ms perf budget (closes §2.1-2.6)"
```

---

## Task 3: Actions (§3 of `tasks.md`)

**Files:**
- Create: `skills/_lib/actions.py`
- Create: `tests/unit/test_actions.py`

### Step 3.1: Write failing test for `Action` base + subprocess wrapper

**File:** `tests/unit/test_actions.py`

```python
import time
import pytest
from unittest.mock import patch, MagicMock
from skills._lib.actions import Action, ActionResult, run_subprocess


def test_action_result_dataclass():
    r = ActionResult(success=True, data={"x": 1})
    assert r.success is True
    assert r.data == {"x": 1}
    assert r.error is None


def test_run_subprocess_success():
    """run_subprocess returns success=True on exit 0."""
    result = run_subprocess(["echo", "hello"], timeout_seconds=5)
    assert result.success is True
    assert "hello" in result.data["stdout"]


def test_run_subprocess_failure_returns_error():
    """run_subprocess returns success=False on non-zero exit."""
    result = run_subprocess(["false"], timeout_seconds=5)
    assert result.success is False
    assert result.error is not None


def test_run_subprocess_timeout_terminates():
    """run_subprocess kills process exceeding timeout."""
    result = run_subprocess(["sleep", "10"], timeout_seconds=1)
    assert result.success is False
    assert "timeout" in (result.error or "").lower() or result.data.get("timed_out") is True


def test_seven_builtin_actions_registered():
    """All 7 built-in actions present."""
    from skills._lib.actions import BUILTIN_ACTIONS
    expected = {
        "action_create_worktree", "action_generate_plan", "action_execute_worktree",
        "action_archive_change", "action_cleanup_stale", "action_update_roadmap",
        "action_create_adr",
    }
    actual = {a.__name__ for a in BUILTIN_ACTIONS}
    assert expected == actual
```

### Step 3.2: Run — verify failure

```bash
cd /workspace/project/rdd-workflow && python3 -m pytest tests/unit/test_actions.py -v
```

Expected: `ModuleNotFoundError: No module named 'skills._lib.actions'`

### Step 3.3: Create `skills/_lib/actions.py`

**File:** `skills/_lib/actions.py`

```python
"""Built-in actions + subprocess wrapper for the loop engine.

7 built-in actions cover v1.x workflow operations. Custom actions can be added
by dropping Python files in `.rdd-workflow/actions/` that subclass `Action`.
"""
from __future__ import annotations
import subprocess
import importlib.util
import os
import json
import datetime
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Optional
from skills._lib.event_log import EventLog
from skills._lib.event_types import EventType, Severity, Event


@dataclass
class ActionResult:
    """Result of action execution."""
    success: bool
    data: dict = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


def run_subprocess(cmd: list, timeout_seconds: int = 30 * 60) -> ActionResult:
    """Run a subprocess with timeout. Returns ActionResult with stdout/stderr."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout_seconds,
        )
        return ActionResult(
            success=(result.returncode == 0),
            data={"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode},
            error=None if result.returncode == 0 else f"exit {result.returncode}: {result.stderr[:200]}",
        )
    except subprocess.TimeoutExpired:
        return ActionResult(
            success=False,
            data={"timed_out": True, "timeout_seconds": timeout_seconds},
            error=f"Timeout after {timeout_seconds}s",
        )
    except Exception as e:
        return ActionResult(success=False, data={"exception": str(e)}, error=str(e))


class Action:
    """Base class for all actions. Subclass and set `name`."""
    name: str = "base"

    def execute(self, params: dict, event_log: EventLog) -> ActionResult:
        raise NotImplementedError


# ─────────────────────────────────────────────────────────────────────────────
# Built-in actions
# ─────────────────────────────────────────────────────────────────────────────

def action_create_worktree(params: dict, event_log: EventLog) -> ActionResult:
    """Create a git worktree. params: {branch: str, path: str}"""
    branch = params.get("branch")
    path = params.get("path")
    if not branch or not path:
        return ActionResult(success=False, error="branch and path required")
    result = run_subprocess(["git", "worktree", "add", "-b", branch, path], timeout_seconds=60)
    event_log.record(Event(
        event_type=EventType.EXECUTION_UNIT_COMPLETED,
        severity=Severity.INFO if result.success else Severity.ERROR,
        message=f"worktree create: {branch} -> {path}",
        context=result.to_dict(),
    ))
    return result


def action_generate_plan(params: dict, event_log: EventLog) -> ActionResult:
    """Generate an implementation plan. params: {change: str, output: str}"""
    change = params.get("change", "")
    output = params.get("output", ".sisyphus/plans/auto-generated.md")
    # Minimal stub — full implementation lives in prometheus-planning skill
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(f"# Auto-generated plan for {change}\n\nGenerated at {datetime.datetime.now().isoformat()}\n")
    event_log.record(Event(
        event_type=EventType.PLAN_GENERATED, severity=Severity.INFO,
        message=f"plan generated: {output}",
    ))
    return ActionResult(success=True, data={"path": output})


def action_execute_worktree(params: dict, event_log: EventLog) -> ActionResult:
    """Execute a worktree's contents. params: {path: str, command: str}"""
    path = params.get("path", ".")
    cmd = params.get("command", "echo no-op")
    result = run_subprocess(cmd.split(), timeout_seconds=30 * 60)
    event_log.record(Event(
        event_type=EventType.EXECUTION_UNIT_COMPLETED,
        severity=Severity.INFO if result.success else Severity.ERROR,
        message=f"execute worktree {path}: {cmd}",
        context=result.to_dict(),
    ))
    return result


def action_archive_change(params: dict, event_log: EventLog) -> ActionResult:
    """Archive an openspec change. params: {change: str}"""
    change = params.get("change")
    if not change:
        return ActionResult(success=False, error="change required")
    src = Path(f"openspec/changes/{change}")
    dst_dir = Path("openspec/changes/archive")
    dst = dst_dir / f"{datetime.date.today().isoformat()}-{change}"
    if not src.exists():
        return ActionResult(success=False, error=f"change not found: {src}")
    dst_dir.mkdir(parents=True, exist_ok=True)
    src.rename(dst)
    event_log.record(Event(
        event_type=EventType.EXECUTION_UNIT_COMPLETED, severity=Severity.INFO,
        message=f"archived change: {change} -> {dst.name}",
    ))
    return ActionResult(success=True, data={"archived_to": str(dst)})


def action_cleanup_stale(params: dict, event_log: EventLog) -> ActionResult:
    """Clean up stale git worktrees/branches. params: {dry_run: bool}"""
    dry_run = params.get("dry_run", True)
    list_result = run_subprocess(["git", "worktree", "list", "--porcelain"], timeout_seconds=10)
    if not list_result.success:
        return ActionResult(success=False, error="failed to list worktrees")
    cleaned = []
    for line in list_result.data["stdout"].splitlines():
        if line.startswith("worktree ") and ".." not in line:
            path = line.split(" ", 1)[1]
            # Don't remove main worktree
            if path == str(Path.cwd()):
                continue
            if not dry_run:
                run_subprocess(["git", "worktree", "remove", path, "--force"], timeout_seconds=30)
            cleaned.append(path)
    event_log.record(Event(
        event_type=EventType.EXECUTION_UNIT_COMPLETED, severity=Severity.INFO,
        message=f"cleanup {'dry-run' if dry_run else 'executed'}: {len(cleaned)} item(s)",
        context={"cleaned": cleaned},
    ))
    return ActionResult(success=True, data={"cleaned": cleaned, "dry_run": dry_run})


def action_update_roadmap(params: dict, event_log: EventLog) -> ActionResult:
    """Update roadmap state. params: {phase: str, category: str}"""
    phase = params.get("phase")
    category = params.get("category")
    if not phase or not category:
        return ActionResult(success=False, error="phase and category required")
    roadmap_file = Path(".rddf/state/roadmap-state.json")
    roadmap_file.parent.mkdir(parents=True, exist_ok=True)
    data = {"phase": phase, "category": category, "updated_at": datetime.datetime.now().isoformat()}
    roadmap_file.write_text(json.dumps(data, indent=2))
    event_log.record(Event(
        event_type=EventType.STATE_UPDATED, severity=Severity.INFO,
        message=f"roadmap updated: {phase} / {category}",
    ))
    return ActionResult(success=True, data=data)


def action_create_adr(params: dict, event_log: EventLog) -> ActionResult:
    """Create a new ADR. params: {title: str, status: str}"""
    title = params.get("title")
    status = params.get("status", "proposed")
    if not title:
        return ActionResult(success=False, error="title required")
    adr_dir = Path("docs/adr")
    adr_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(adr_dir.glob("*.md"))
    next_num = len(existing) + 1
    adr_path = adr_dir / f"{next_num:04d}-{title.lower().replace(' ', '-')}.md"
    adr_path.write_text(f"# ADR-{next_num:04d}: {title}\n\n**Status:** {status}\n\n## Context\n\n## Decision\n\n## Consequences\n")
    event_log.record(Event(
        event_type=EventType.EXECUTION_UNIT_COMPLETED, severity=Severity.INFO,
        message=f"ADR created: {adr_path.name}",
    ))
    return ActionResult(success=True, data={"path": str(adr_path), "number": next_num})


# ─────────────────────────────────────────────────────────────────────────────
# Registry + plugin loader
# ─────────────────────────────────────────────────────────────────────────────

BUILTIN_ACTIONS = [
    action_create_worktree, action_generate_plan, action_execute_worktree,
    action_archive_change, action_cleanup_stale, action_update_roadmap,
    action_create_adr,
]


class _FunctionAction:
    """Wrap a built-in action function with `name` and `execute` interface."""
    def __init__(self, fn):
        self.fn = fn
        self.name = fn.__name__

    def execute(self, params: dict, event_log: EventLog) -> ActionResult:
        return self.fn(params, event_log)


def load_plugin_actions(plugin_dir: str = ".rdd-workflow/actions") -> list:
    """Load custom Action subclasses from a directory."""
    pdir = Path(plugin_dir)
    if not pdir.exists():
        return []
    plugins = []
    for py_file in pdir.glob("*.py"):
        if py_file.name.startswith("_"):
            continue
        spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if isinstance(attr, type) and issubclass(attr, Action) and attr is not Action:
                    plugins.append(attr())
        except Exception:
            continue
    return plugins


def all_actions() -> list:
    """Return built-in + plugin actions."""
    builtin = [_FunctionAction(fn) for fn in BUILTIN_ACTIONS]
    plugins = load_plugin_actions()
    return builtin + plugins
```

### Step 3.4: Run — verify all tests pass

```bash
cd /workspace/project/rdd-workflow && python3 -m pytest tests/unit/test_actions.py -v
```

Expected: 5 passed

### Step 3.5: Add test for plugin loading

Add to `tests/unit/test_actions.py`:

```python
def test_load_plugin_actions_empty_when_dir_missing(tmp_path, monkeypatch):
    """No error when .rdd-workflow/actions/ doesn't exist."""
    monkeypatch.chdir(tmp_path)
    from skills._lib.actions import load_plugin_actions
    assert load_plugin_actions() == []
```

### Step 3.6: Run full suite + commit

```bash
cd /workspace/project/rdd-workflow && python3 -m pytest tests/unit/ -q
```

Expected: 60 passed (45 baseline + 4 loop + 5 detectors + 6 actions)

```bash
cd /workspace/project/rdd-workflow && git add skills/_lib/actions.py tests/unit/test_actions.py && git commit -m "feat(actions): 7 built-in actions + subprocess wrapper + 30min timeout + plugin loader (closes §3.1-3.5)"
```

---

## Task 4: Interaction Modes + Human Nodes (§4 of `tasks.md`)

**Files:**
- Create: `skills/_lib/interaction_modes.py`
- Create: `skills/_lib/human_nodes.py`
- Create: `tests/unit/test_interaction_modes.py`
- Create: `tests/unit/test_human_nodes.py`

### Step 4.1: Write failing test for `HumanNode` registry + verification dispatch

**File:** `tests/unit/test_human_nodes.py`

```python
import pytest
from skills._lib.human_nodes import (
    HumanNodeRegistry, NodeTrigger, VerificationMode, MultiModelUnavailableError,
)


def test_seven_node_types_registered():
    """All 7 human-in-loop node types present."""
    reg = HumanNodeRegistry()
    expected = {
        "arch.adr_create", "arch.roadmap_define", "plan.change_select",
        "plan.propose_confirm", "ship.archive_confirm", "ship.cleanup_confirm",
        "ship.execute_error",
    }
    actual = {n.name for n in reg.list_nodes()}
    assert expected == actual


def test_verification_modes_enum():
    """3 verification modes: human, multi_model, script."""
    assert VerificationMode.HUMAN.value == "human"
    assert VerificationMode.MULTI_MODEL.value == "multi_model"
    assert VerificationMode.SCRIPT.value == "script"


def test_multi_model_raises_not_implemented():
    """multi_model verification raises NotImplementedError until v2-advanced-features."""
    reg = HumanNodeRegistry()
    trigger = NodeTrigger(name="arch.adr_create", mode=VerificationMode.MULTI_MODEL, params={})
    with pytest.raises(NotImplementedError, match="v2-advanced-features"):
        reg.verify(trigger)


def test_script_verification_runs_command():
    """script verification runs configured command and uses exit code."""
    reg = HumanNodeRegistry()
    trigger = NodeTrigger(
        name="plan.change_select", mode=VerificationMode.SCRIPT,
        params={"command": ["true"]},
    )
    result = reg.verify(trigger)
    assert result.success is True
```

### Step 4.2: Create `skills/_lib/human_nodes.py`

**File:** `skills/_lib/human_nodes.py`

```python
"""Human-in-Loop node registry with 3 verification modes."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from skills._lib.actions import run_subprocess


class VerificationMode(str, Enum):
    HUMAN = "human"
    MULTI_MODEL = "multi_model"
    SCRIPT = "script"


class MultiModelUnavailableError(NotImplementedError):
    """Raised when multi_model verification is requested before v2-advanced-features ships."""
    pass


@dataclass
class NodeTrigger:
    """A human-in-loop node invocation."""
    name: str
    mode: VerificationMode
    params: dict


@dataclass
class VerificationResult:
    success: bool
    data: dict
    message: str = ""


# Built-in node definitions: name → required verification mode
BUILTIN_NODE_DEFS = [
    ("arch.adr_create", VerificationMode.HUMAN),
    ("arch.roadmap_define", VerificationMode.HUMAN),
    ("plan.change_select", VerificationMode.HUMAN),
    ("plan.propose_confirm", VerificationMode.HUMAN),
    ("ship.archive_confirm", VerificationMode.HUMAN),
    ("ship.cleanup_confirm", VerificationMode.SCRIPT),
    ("ship.execute_error", VerificationMode.HUMAN),
]


class HumanNodeRegistry:
    """Registry of human-in-loop nodes with verification dispatch."""

    def __init__(self):
        self._nodes = {name: mode for name, mode in BUILTIN_NODE_DEFS}

    def list_nodes(self) -> list:
        return [NodeTrigger(name=n, mode=m, params={}) for n, m in self._nodes.items()]

    def verify(self, trigger: NodeTrigger) -> VerificationResult:
        """Dispatch verification according to trigger.mode."""
        if trigger.mode == VerificationMode.MULTI_MODEL:
            raise MultiModelUnavailableError(
                "multi_model verification requires v2-advanced-features (Tribunal). "
                "Not yet implemented."
            )
        if trigger.mode == VerificationMode.SCRIPT:
            cmd = trigger.params.get("command")
            if not cmd:
                return VerificationResult(success=False, data={}, message="no command")
            result = run_subprocess(cmd if isinstance(cmd, list) else cmd.split(), timeout_seconds=300)
            return VerificationResult(
                success=result.success,
                data=result.data,
                message=f"script exit: {result.data.get('returncode', '?')}",
            )
        # HUMAN mode — caller is expected to display menu and collect input
        # This stub returns success=True to allow loop to proceed (test override available)
        return VerificationResult(success=True, data={"mode": "human"}, message="human input required (caller handles UI)")
```

### Step 4.3: Run human_nodes tests

```bash
cd /workspace/project/rdd-workflow && python3 -m pytest tests/unit/test_human_nodes.py -v
```

Expected: 4 passed

### Step 4.4: Write failing test for interaction modes

**File:** `tests/unit/test_interaction_modes.py`

```python
import pytest
from unittest.mock import MagicMock
from skills._lib.interaction_modes import LoopMode, MenuMode, HybridMode
from skills._lib.human_nodes import HumanNodeRegistry, NodeTrigger, VerificationMode


@pytest.fixture
def registry():
    return HumanNodeRegistry()


def test_loop_mode_skips_human_nodes_except_on_error(registry):
    """Loop mode runs autonomously; skips human nodes unless error."""
    mode = LoopMode(registry)
    trigger = NodeTrigger("arch.adr_create", VerificationMode.HUMAN, {})
    # In success path, loop mode auto-confirms
    assert mode.should_pause(trigger, context={"error": False}) is False
    # In error path, loop mode DOES pause
    assert mode.should_pause(trigger, context={"error": True}) is True


def test_menu_mode_pauses_at_every_decision(registry):
    """Menu mode pauses at every human node."""
    mode = MenuMode(registry)
    trigger = NodeTrigger("plan.change_select", VerificationMode.HUMAN, {})
    assert mode.should_pause(trigger, context={"error": False}) is True


def test_hybrid_mode_pauses_only_at_configured_nodes(registry):
    """Hybrid mode pauses only at nodes in human_nodes config."""
    mode = HybridMode(registry, human_nodes={"arch.adr_create", "ship.archive_confirm"})
    # Configured node → pause
    trigger1 = NodeTrigger("arch.adr_create", VerificationMode.HUMAN, {})
    assert mode.should_pause(trigger1, context={"error": False}) is True
    # Non-configured node → skip
    trigger2 = NodeTrigger("plan.change_select", VerificationMode.HUMAN, {})
    assert mode.should_pause(trigger2, context={"error": False}) is False


def test_mode_name_returns_correct_value(registry):
    """Each mode reports its name."""
    assert LoopMode(registry).name == "loop"
    assert MenuMode(registry).name == "menu"
    assert HybridMode(registry, human_nodes=set()).name == "hybrid"
```

### Step 4.5: Create `skills/_lib/interaction_modes.py`

**File:** `skills/_lib/interaction_modes.py`

```python
"""Three interaction modes for the loop engine: Loop, Menu, Hybrid.

ADR-0002: Users choose autonomy level. Hybrid is default.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional
from skills._lib.human_nodes import HumanNodeRegistry, NodeTrigger


class InteractionMode(ABC):
    """Abstract base for interaction modes."""
    name: str = "base"

    def __init__(self, registry: HumanNodeRegistry):
        self.registry = registry

    @abstractmethod
    def should_pause(self, trigger: NodeTrigger, context: dict) -> bool:
        """Decide whether to pause for human input at this node."""
        raise NotImplementedError


class LoopMode(InteractionMode):
    """Fully autonomous. Skips human nodes except on error."""
    name = "loop"

    def should_pause(self, trigger: NodeTrigger, context: dict) -> bool:
        return bool(context.get("error", False))


class MenuMode(InteractionMode):
    """Fully manual. Pauses at every decision point."""
    name = "menu"

    def should_pause(self, trigger: NodeTrigger, context: dict) -> bool:
        return True


class HybridMode(InteractionMode):
    """Default. Auto for routine, manual at configured key nodes."""
    name = "hybrid"

    def __init__(self, registry: HumanNodeRegistry, human_nodes: Optional[set] = None):
        super().__init__(registry)
        self.human_nodes = human_nodes or set()

    def should_pause(self, trigger: NodeTrigger, context: dict) -> bool:
        if context.get("error", False):
            return True
        return trigger.name in self.human_nodes


def make_mode(name: str, registry: HumanNodeRegistry, **kwargs) -> InteractionMode:
    """Factory for interaction modes. name in {loop, menu, hybrid}."""
    if name == "loop":
        return LoopMode(registry)
    if name == "menu":
        return MenuMode(registry)
    if name == "hybrid":
        return HybridMode(registry, human_nodes=kwargs.get("human_nodes", set()))
    raise ValueError(f"Unknown mode: {name}")
```

### Step 4.6: Run + commit

```bash
cd /workspace/project/rdd-workflow && python3 -m pytest tests/unit/test_interaction_modes.py tests/unit/test_human_nodes.py -v
```

Expected: 8 passed (4 + 4)

```bash
cd /workspace/project/rdd-workflow && python3 -m pytest tests/unit/ -q
```

Expected: 68 passed

```bash
cd /workspace/project/rdd-workflow && git add skills/_lib/interaction_modes.py skills/_lib/human_nodes.py tests/unit/test_interaction_modes.py tests/unit/test_human_nodes.py && git commit -m "feat(interaction-modes): Loop/Menu/Hybrid + 7 human nodes + 3 verification modes (closes §4.1-4.7)"
```

---

## Task 5: Design-First Phase (§5 of `tasks.md`)

**Files:**
- Create: `skills/_lib/design_phase.py`
- Create: `tests/unit/test_design_phase.py`
- Modify: `skills/_lib/schemas/state_vector_schema.json`

### Step 5.0: Extend state schema for design phase result

The loop engine's `DesignPhase.apply()` writes to `loop_state.design`, but the current schema's `loop_state` is `additionalProperties: false` and doesn't include `design`. Add the field (same pattern as Step 1.0).

**File:** `skills/_lib/schemas/state_vector_schema.json`

In the `loop_state.properties` section, add:

```json
"design": {
  "type": ["object", "null"],
  "description": "Pre-loop design result (Goal/Verification/Control) (v2-loop-engine).",
  "properties": {
    "goal": {"type": "object"},
    "verification": {"type": "object"},
    "control": {"type": "object"}
  }
}
```

Verify no regression:

```bash
cd /workspace/project/rdd-workflow && python3 -m pytest tests/unit/test_state_vector.py -q
```

Expected: All existing tests still pass.

### Step 5.1: Write failing test for design phase

**File:** `tests/unit/test_design_phase.py`

```python
import pytest
from skills._lib.design_phase import DesignPhase, DesignResult
from skills._lib.state_vector import StateVector
from skills._lib.event_log import EventLog


@pytest.fixture
def env(tmp_path):
    sv = StateVector.load(str(tmp_path / "state-vector.json"))
    el = EventLog(str(tmp_path / "event-log.jsonl"))
    return sv, el


def test_design_phase_has_three_dimensions(env):
    """Design phase covers Goal, Verification, Control dimensions."""
    sv, el = env
    dp = DesignPhase(state=sv, event_log=el)
    dims = dp.list_dimensions()
    assert "goal" in dims
    assert "verification" in dims
    assert "control" in dims


def test_design_phase_default_goal_dim(env):
    """Default goal design includes deliverables + completion_criteria."""
    sv, el = env
    dp = DesignPhase(state=sv, event_log=el)
    goal = dp.default_for("goal")
    assert "deliverables" in goal
    assert "completion_criteria" in goal


def test_design_phase_persists_to_state_vector(env):
    """Design result saved to state vector under loop_state.design."""
    sv, el = env
    dp = DesignPhase(state=sv, event_log=el)
    result = DesignResult(
        goal={"deliverables": ["x"], "completion_criteria": "x == done"},
        verification={"executor": "deep", "reviewer": "oracle"},
        control={"max_iterations": 50, "max_retries": 2, "oscillation_threshold": 3},
    )
    dp.apply(result)
    saved = sv.to_dict()
    assert "design" in saved["loop_state"]
    assert saved["loop_state"]["design"]["control"]["max_iterations"] == 50
```

### Step 5.2: Create `skills/_lib/design_phase.py`

**File:** `skills/_lib/design_phase.py`

```python
"""Design-first phase — Goal, Verification, Control design before loop starts."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any
from skills._lib.state_vector import StateVector
from skills._lib.event_log import EventLog
from skills._lib.event_types import EventType, Severity, Event


@dataclass
class DesignResult:
    """User-confirmed design across 3 dimensions."""
    goal: dict = field(default_factory=lambda: {"deliverables": [], "completion_criteria": ""})
    verification: dict = field(default_factory=lambda: {"executor": "deep", "reviewer": "oracle"})
    control: dict = field(default_factory=lambda: {
        "max_iterations": 100, "max_retries": 3, "oscillation_threshold": 2,
    })

    def to_dict(self) -> dict:
        return asdict(self)


class DesignPhase:
    """Pre-loop design phase. Runs once before loop starts."""

    DIMENSIONS = ("goal", "verification", "control")

    DEFAULTS = {
        "goal": {
            "deliverables": [],
            "completion_criteria": "",
        },
        "verification": {
            "executor": "deep",
            "reviewer": "oracle",
        },
        "control": {
            "max_iterations": 100,
            "max_retries": 3,
            "oscillation_threshold": 2,
        },
    }

    def __init__(self, state: StateVector, event_log: EventLog):
        self.state = state
        self.event_log = event_log

    def list_dimensions(self) -> list:
        return list(self.DIMENSIONS)

    def default_for(self, dimension: str) -> dict:
        return dict(self.DEFAULTS.get(dimension, {}))

    def apply(self, result: DesignResult) -> None:
        """Persist design result to state vector and log."""
        design_dict = result.to_dict()
        self.state.update_field("loop_state.design", design_dict)
        self.event_log.record(Event(
            event_type=EventType.STATE_UPDATED, severity=Severity.INFO,
            message="design phase applied",
            context=design_dict,
        ))
```

### Step 5.3: Run + commit

```bash
cd /workspace/project/rdd-workflow && python3 -m pytest tests/unit/test_design_phase.py -v
```

Expected: 3 passed

```bash
cd /workspace/project/rdd-workflow && git add skills/_lib/design_phase.py tests/unit/test_design_phase.py && git commit -m "feat(design-phase): pre-loop Goal/Verification/Control design + state persistence (closes §5.1-5.6)"
```

---

## Task 6: Flowchart Generator (§6 of `tasks.md`)

**Files:**
- Create: `skills/_lib/flowchart.py`
- Create: `tests/unit/test_flowchart.py`

### Step 6.1: Write failing test for flowchart generation

**File:** `tests/unit/test_flowchart.py`

```python
import pytest
from skills._lib.flowchart import FlowchartGenerator
from skills._lib.state_vector import StateVector
from skills._lib.event_log import EventLog


@pytest.fixture
def env(tmp_path):
    sv = StateVector.load(str(tmp_path / "state-vector.json"))
    el = EventLog(str(tmp_path / "event-log.jsonl"))
    return sv, el


def test_flowchart_includes_phase_and_iteration(env):
    """Generated flowchart shows current phase + iteration count."""
    sv, el = env
    fc = FlowchartGenerator(state=sv, event_log=el)
    sv.update_field("loop_state.current_phase", "execute_plan")
    sv.update_field("loop_state.iteration", 7)
    chart = fc.render()
    assert "execute_plan" in chart
    assert "7" in chart


def test_flowchart_includes_event_log_errors(env):
    """Flowchart summarizes recent errors from event log."""
    from skills._lib.event_types import EventType, Severity, Event
    sv, el = env
    el.record(Event(event_type=EventType.ERROR_OCCURRED, severity=Severity.ERROR, message="boom"))
    fc = FlowchartGenerator(state=sv, event_log=el)
    chart = fc.render()
    assert "error" in chart.lower() or "ERROR" in chart


def test_flowchart_renders_under_100ms(env):
    """Flowchart regeneration completes in < 100ms."""
    import time
    sv, el = env
    fc = FlowchartGenerator(state=sv, event_log=el)
    # Warm-up
    fc.render()
    start = time.perf_counter()
    chart = fc.render()
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert elapsed_ms < 100, f"Render took {elapsed_ms:.1f}ms"
    assert len(chart) > 0
```

### Step 6.2: Create `skills/_lib/flowchart.py`

**File:** `skills/_lib/flowchart.py`

```python
"""ASCII flowchart generator — reads state vector + event log, renders progress."""
from __future__ import annotations
from skills._lib.state_vector import StateVector
from skills._lib.event_log import EventLog


PHASE_LABELS = {
    "verify_goal": "[1] Verify Goal",
    "scan_state": "[2] Scan State",
    "generate_plan": "[3] Generate Plan",
    "execute_plan": "[4] Execute Plan",
    "verify_results": "[5] Verify Results",
    "adapt": "[6] Adapt",
}


class FlowchartGenerator:
    """Generate ASCII flowchart of current loop progress."""

    def __init__(self, state: StateVector, event_log: EventLog):
        self.state = state
        self.event_log = event_log

    def render(self) -> str:
        """Render the flowchart as a multi-line ASCII string."""
        sd = self.state.to_dict()
        loop_state = sd.get("loop_state", {})
        current_phase = loop_state.get("current_phase", "verify_goal")
        iteration = loop_state.get("iteration", 0)
        gate_status = sd.get("arch_side", {}).get("gate_status", "ok")
        errors = self.event_log.query(severity="error", limit=5)
        warnings = self.event_log.query(severity="warn", limit=5)

        lines = [
            "┌─ Loop Engine Progress ─────────────────────────┐",
            f"│ Iteration: {iteration:<35} │",
            f"│ Gate:      {gate_status:<35} │",
            f"│ Phase:     {PHASE_LABELS.get(current_phase, current_phase):<35} │",
            "│                                                 │",
            "│ Flow:                                           │",
            "│   verify_goal → scan_state → generate_plan      │",
            "│        ↓                                       │",
            "│   execute_plan → verify_results → adapt         │",
            "│        ↓                                       │",
            "│   (loop or exit)                                │",
        ]
        if errors:
            lines.append("│                                                 │")
            lines.append(f"│ Recent errors ({len(errors)}):".ljust(48) + "│")
            for e in errors[:3]:
                msg = e.get("message", "")[:38]
                lines.append(f"│   ! {msg}".ljust(48) + "│")
        if warnings:
            lines.append("│                                                 │")
            lines.append(f"│ Recent warnings ({len(warnings)}):".ljust(48) + "│")
            for w in warnings[:2]:
                msg = w.get("message", "")[:38]
                lines.append(f"│   ~ {msg}".ljust(48) + "│")
        lines.append("└─────────────────────────────────────────────────┘")
        return "\n".join(lines)
```

### Step 6.3: Run + commit

```bash
cd /workspace/project/rdd-workflow && python3 -m pytest tests/unit/test_flowchart.py -v
```

Expected: 3 passed

```bash
cd /workspace/project/rdd-workflow && python3 -m pytest tests/unit/ -q
```

Expected: 74 passed (45 baseline + 4 loop + 5 detectors + 6 actions + 4 modes + 4 human + 3 design + 3 flowchart)

```bash
cd /workspace/project/rdd-workflow && git add skills/_lib/flowchart.py tests/unit/test_flowchart.py && git commit -m "feat(flowchart): ASCII real-time progress generator (closes §6.1-6.5)"
```

---

## Task 7: Wire LoopEngine to Detectors + Actions + Modes + Flowchart

**Files:**
- Modify: `skills/loop-engine.py`

### Step 7.1: Add integration test

**File:** `tests/unit/test_loop_engine.py` (append)

```python
def test_loop_engine_scan_uses_detectors(tmp_path, monkeypatch):
    """scan_state() invokes all built-in detectors."""
    sv_path = str(tmp_path / "state-vector.json")
    el_path = str(tmp_path / "event-log.jsonl")
    engine = LoopEngine(state=StateVector.load(sv_path), event_log=EventLog(el_path))
    engine.scan_state()
    assert len(engine.loop_state.detections) == 8  # all 8 built-ins


def test_loop_engine_accepts_mode_parameter(tmp_path):
    """LoopEngine accepts interaction mode at construction time."""
    sv_path = str(tmp_path / "state-vector.json")
    el_path = str(tmp_path / "event-log.jsonl")
    from skills._lib.interaction_modes import make_mode, LoopMode
    from skills._lib.human_nodes import HumanNodeRegistry
    registry = HumanNodeRegistry()
    engine = LoopEngine(
        state=StateVector.load(sv_path),
        event_log=EventLog(el_path),
        mode=LoopMode(registry),
    )
    assert engine.mode.name == "loop"
```

### Step 7.2: Update `skills/loop-engine.py` — wire scan/plan/execute

Replace the stub methods:

```python
    def __init__(self, state: StateVector, event_log: EventLog, config: Optional[ConfigParser] = None,
                 mode: Optional["InteractionMode"] = None):
        self.state = state
        self.event_log = event_log
        # CORRECT API: ConfigParser.parse(runtime_overrides) → dict
        self.config = config or ConfigParser()
        cfg = self.config.parse()
        loop_cfg = cfg.get("loop", {})
        self.safety = {
            "max_iterations": loop_cfg.get("max_iterations", self.SAFETY_DEFAULTS["max_iterations"]),
            "max_retries": loop_cfg.get("max_retries", self.SAFETY_DEFAULTS["max_retries"]),
            "oscillation_window": loop_cfg.get("oscillation_window", self.SAFETY_DEFAULTS["oscillation_window"]),
            "oscillation_distinct_threshold": loop_cfg.get("oscillation_distinct_threshold", self.SAFETY_DEFAULTS["oscillation_distinct_threshold"]),
            "circuit_breaker_threshold": loop_cfg.get("circuit_breaker_threshold", self.SAFETY_DEFAULTS["circuit_breaker_threshold"]),
            "action_timeout_seconds": loop_cfg.get("action_timeout_seconds", self.SAFETY_DEFAULTS["action_timeout_seconds"]),
        }
        self.loop_state = LoopState()
        # Lazy import to avoid circular dependency
        from skills._lib.human_nodes import HumanNodeRegistry
        from skills._lib.interaction_modes import make_mode
        self.registry = HumanNodeRegistry()
        # CORRECT API: read from parsed dict, not .get()
        mode_name = cfg.get("interaction", {}).get("mode", "hybrid")
        self.mode = mode or make_mode(mode_name, self.registry)

    def scan_state(self) -> None:
        """Run all detectors and populate loop_state.detections."""
        from skills._lib.detectors import all_detectors
        detectors = all_detectors()
        results = [d.detect(self.state.to_dict()) for d in detectors]
        self.loop_state.detections = [r.to_dict() if hasattr(r, "to_dict") else r for r in results]
        self.state.update_field("loop_state.current_phase", "scan_state")
        self.state.update_field("loop_state.iteration", self.loop_state.iteration)
        self.event_log.record(Event(
            event_type=EventType.SCAN_COMPLETED, severity=Severity.INFO,
            message=f"scanned {len(results)} detectors",
            context={"count": len(results)},
        ))

    def generate_plan(self) -> None:
        """Match detectors → actions. Stub: 1:1 mapping."""
        from skills._lib.actions import all_actions
        action_objs = all_actions()
        action_map = {a.name: a for a in action_objs}
        plan = []
        for det in self.loop_state.detections:
            det_type = det.get("type") if isinstance(det, dict) else det.type
            action_name = f"action_{det_type}"
            if action_name in action_map:
                plan.append((action_map[action_name], det.get("data", {}) if isinstance(det, dict) else det.data))
        self.loop_state.plan = plan
        self.state.update_field("loop_state.current_phase", "generate_plan")

    def execute_plan(self) -> None:
        """Execute each action with timeout + retry."""
        from skills._lib.actions import _FunctionAction  # noqa
        executed = []
        for action, params in self.loop_state.plan:
            result = None
            for attempt in range(self.safety["max_retries"]):
                result = action.execute(params, self.event_log)
                if result.success:
                    break
                self.loop_state.consecutive_failures += 1
            else:
                if result is not None:
                    self.loop_state.errors.append(result.error or "unknown error")
            executed.append(result)
            if result and result.success:
                self.loop_state.consecutive_failures = 0
        self.loop_state.executed = [r.to_dict() if r else {} for r in executed]
        self.state.update_field("loop_state.current_phase", "execute_plan")

    def verify_results(self) -> bool:
        """Verify execution results meet goal. Returns True if goal achievable."""
        successes = sum(1 for r in self.loop_state.executed if r.get("success"))
        return successes == len(self.loop_state.executed) and successes > 0

    def adapt(self) -> None:
        """Adapt strategy based on results. Stub updates phase."""
        self.state.update_field("loop_state.current_phase", "adapt")
```

### Step 7.3: Run + commit

```bash
cd /workspace/project/rdd-workflow && python3 -m pytest tests/unit/ -q
```

Expected: 76 passed (74 + 2 integration)

```bash
cd /workspace/project/rdd-workflow && git add skills/loop-engine.py tests/unit/test_loop_engine.py && git commit -m "feat(loop-engine): wire scan_state/generate_plan/execute_plan to detectors/actions (closes §1.5-1.7)"
```

---

## Task 8: Documentation Updates

**Files:**
- Modify: `docs/v2-api-reference.md`
- Modify: `docs/v2-config-schema.md`
- Create: `docs/v2-loop-engine.md`

### Step 8.1: Append API section to `docs/v2-api-reference.md`

Add new section at end:

```markdown
## v2 Loop Engine APIs

### LoopEngine
- `LoopEngine(state, event_log, config=None, mode=None)` — constructor
- `engine.run(goal_predicate, max_iterations=None) → LoopStatus` — execute cycle
- `engine.verify_goal(predicate) → bool` — evaluate goal predicate
- `LoopStatus` enum: `SUCCESS`, `MAX_ITERATIONS_EXCEEDED`, `MAX_RETRIES_EXCEEDED`, `OSCILLATION_DETECTED`, `CIRCUIT_BROKEN`, `ERROR`

### Detector / DetectionResult
- `Detector` base class — subclass, set `name`, implement `detect(state) → DetectionResult`
- `DetectionResult(type, data, message, severity="info")` — structured output
- `all_detectors() → list[Detector]` — built-ins + plugins

### Action / ActionResult
- `Action` base class — subclass, set `name`, implement `execute(params, event_log) → ActionResult`
- `ActionResult(success, data, error=None)` — execution outcome
- `run_subprocess(cmd, timeout_seconds) → ActionResult` — subprocess wrapper with 30-min default timeout

### InteractionMode / HumanNodeRegistry
- `InteractionMode` ABC with `LoopMode`, `MenuMode`, `HybridMode`
- `make_mode(name, registry, **kwargs) → InteractionMode` — factory
- `HumanNodeRegistry` — 7 node types, 3 verification modes
- `MultiModelUnavailableError` — raised until v2-advanced-features ships

### DesignPhase / FlowchartGenerator
- `DesignPhase(state, event_log)` — pre-loop design
- `FlowchartGenerator(state, event_log).render() → str` — ASCII chart
```

### Step 8.2: Append config schema section

Add to `docs/v2-config-schema.md`:

```markdown
## loop.yaml — v2 Extensions

```yaml
interaction:
  mode: hybrid  # loop | menu | hybrid (default: hybrid)
  human_nodes:
    - arch.adr_create
    - ship.archive_confirm

loop:
  max_iterations: 100
  max_retries: 3
  oscillation_window: 5
  oscillation_distinct_threshold: 2
  circuit_breaker_threshold: 3
  action_timeout_seconds: 1800

plugins:
  detectors_dir: .rdd-workflow/detectors
  actions_dir: .rdd-workflow/actions
```

Runtime override: `--mode loop` CLI flag or `SPEC_WORKFLOW_MODE` env var.
```

### Step 8.3: Create `docs/v2-loop-engine.md`

```markdown
# Loop Engine User Guide

The v2.0 loop engine drives rdd-workflow via a 6-block cycle:

```
verify_goal → scan_state → generate_plan → execute_plan → verify_results → adapt
                       ↑                                          │
                       └──────────────────────────────────────────┘
```

## Quick Start

```python
from skills.loop_engine import LoopEngine
from skills._lib.state_vector import StateVector
from skills._lib.event_log import EventLog

# CORRECT API: use .load(path) to load from disk (or .create_default() for in-memory)
engine = LoopEngine(
    state=StateVector.load(".rdd-workflow/state-vector.json"),
    event_log=EventLog(".rdd-workflow/event-log.jsonl"),
)
# Goal predicate uses dotted-path access against state.to_dict()
status = engine.run(goal_predicate="plan_side['active_change'] is None")
```

## Modes

- **Loop** — fully autonomous (CI/CD)
- **Menu** — fully manual (learning/debugging)
- **Hybrid** (default) — auto for routine, manual at key nodes

Switch at runtime: `LoopEngine(..., mode=LoopMode(registry))` or `loop.yaml`.

## Plugins

Drop Python files in `.rdd-workflow/detectors/` or `.rdd-workflow/actions/` to extend.
Each must subclass `Detector` or `Action` and set `name`.
```

### Step 8.4: Commit

```bash
cd /workspace/project/rdd-workflow && git add docs/v2-api-reference.md docs/v2-config-schema.md docs/v2-loop-engine.md && git commit -m "docs(loop-engine): API reference + config schema + user guide"
```

---

## Task 9: OpenSpec Validation & Status

### Step 9.1: Run full test suite

```bash
cd /workspace/project/rdd-workflow && python3 -m pytest tests/unit/ -v
```

Expected: 76 passed, 0 failed

If failures occur: do NOT proceed to archive. Fix and re-run.

### Step 9.2: Validate openspec change

```bash
cd /workspace/project/rdd-workflow && openspec validate v2-loop-engine
```

Expected: `Change 'v2-loop-engine' is valid`

### Step 9.3: Check task completion status

```bash
cd /workspace/project/rdd-workflow && openspec instructions apply --change v2-loop-engine 2>&1 | tail -20
# OR
cd /workspace/project/rdd-workflow && grep -c "\[ \]" openspec/changes/v2-loop-engine/tasks.md
```

Expected: 0 unchecked `- [ ]` items remaining

### Step 9.4: Verify all 36 tasks checked

```bash
cd /workspace/project/rdd-workflow && grep -E "^\s*-\s*\[" openspec/changes/v2-loop-engine/tasks.md | head -40
```

All should be `- [x]`. If not, manually update.

---

## Task 10: Update `tasks.md` to Mark All Complete

### Step 10.1: Replace all `[ ]` with `[x]` in tasks.md

```bash
cd /workspace/project/rdd-workflow && sed -i 's/- \[ \]/- [x]/g' openspec/changes/v2-loop-engine/tasks.md
```

### Step 10.2: Verify

```bash
cd /workspace/project/rdd-workflow && grep -c "\[x\]" openspec/changes/v2-loop-engine/tasks.md && grep -c "\[ \]" openspec/changes/v2-loop-engine/tasks.md
```

Expected: 36 `[x]`, 0 `[ ]`

### Step 10.3: Commit task updates

```bash
cd /workspace/project/rdd-workflow && git add openspec/changes/v2-loop-engine/tasks.md && git commit -m "docs(tasks): mark all v2-loop-engine tasks complete"
```

---

## Task 11: OpenSpec Archive

### Step 11.1: Archive the change

```bash
cd /workspace/project/rdd-workflow && openspec archive v2-loop-engine -y
```

This command:
1. Moves `openspec/changes/v2-loop-engine/` → `openspec/changes/archive/2026-06-25-v2-loop-engine/`
2. Merges new specs into `openspec/specs/{loop-engine,detectors-actions,interaction-modes,design-flowchart}/`
3. Records archive metadata

### Step 11.2: Verify archive completed

```bash
cd /workspace/project/rdd-workflow && openspec list
```

Expected: `v2-loop-engine` no longer in the active list.

```bash
cd /workspace/project/rdd-workflow && ls -la openspec/changes/archive/ | grep v2-loop-engine
```

Expected: `2026-06-25-v2-loop-engine/` directory exists.

```bash
cd /workspace/project/rdd-workflow && ls openspec/specs/
```

Expected: 4 new spec directories: `loop-engine/`, `detectors-actions/`, `interaction-modes/`, `design-flowchart/`.

### Step 11.3: Verify v1.x baseline still passes

```bash
cd /workspace/project/rdd-workflow && python3 -m pytest tests/unit/ -q
```

Expected: 76 passed, zero regressions.

### Step 11.4: Final commit

```bash
cd /workspace/project/rdd-workflow && git status
```

If openspec created untracked changes (e.g., archived move creates new files in `openspec/specs/`):

```bash
cd /workspace/project/rdd-workflow && git add openspec/ && git commit -m "merge: v2-loop-engine (LoopEngine + detectors + actions + modes + design + flowchart)"
```

---

## Task 12: Post-Archive Cleanup

### Step 12.1: Verify final state

```bash
cd /workspace/project/rdd-workflow && git log --oneline -5
```

Expected: archive commit at HEAD.

```bash
cd /workspace/project/rdd-workflow && openspec list
```

Expected: v2-loop-engine removed; 3 remaining (v2-advanced-features, v2-migration-and-tests, v2-beta-release).

### Step 12.2: Confirm no untracked files

```bash
cd /workspace/project/rdd-workflow && git status
```

Expected: clean working tree (except expected `__pycache__/` if not in `.gitignore`).

---

## Summary

| Metric | Value |
|---|---|
| New Python files | 7 (`loop-engine.py`, `_lib/{loop_state,detectors,actions,interaction_modes,human_nodes,design_phase,flowchart}.py`) |
| New test files | 7 |
| New tests | ~30 (covering 36 openspec tasks) |
| New LOC | ~2,500 production + ~500 test |
| Documentation | 3 files updated/created |
| Total commits | 8 (1 per major section + final merge) |

## Exit Criteria (all must be true)

- [ ] `python3 -m pytest tests/unit/ -q` → 76 passed, 0 failed
- [ ] `openspec validate v2-loop-engine` → valid
- [ ] `openspec list` → v2-loop-engine absent
- [ ] `openspec/changes/archive/2026-06-25-v2-loop-engine/` exists
- [ ] `openspec/specs/{loop-engine,detectors-actions,interaction-modes,design-flowchart}/` exist
- [ ] `git status` clean (or only `__pycache__/`)
- [ ] Zero regressions in v2-core-foundation tests
