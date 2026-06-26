# v2-advanced-features Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the 5 advanced subsystems of spec-workflow v2.0 (Tribunal, Sanitizer, Memory, Session, Agents) with full TDD coverage so that `v2-advanced-features` can be archived.

**Architecture:** Each subsystem is a standalone Python module in `skills/_lib/` with a matching unit test in `tests/unit/`. All modules depend on the already-shipped v2-core-foundation (StateVector, EventLog, FileLock, ConfigParser) and v2-loop-engine (EventType, Severity, HumanNodeRegistry, actions). The Tribunal specifically implements the `MULTI_MODEL` verification mode that `human_nodes.py` currently raises `MultiModelUnavailableError` for.

**Tech Stack:** Python 3.12, pytest, dataclass, enum, typing, no external deps.

**Reference Spec:** `openspec/changes/v2-advanced-features/{proposal,design,tasks}.md` + `openspec/changes/v2-advanced-features/specs/{tribunal,memory,session-agents}/spec.md`

---

## File Map

| File | Action | Dependencies | Lines (est) |
|------|--------|--------------|-------------|
| `skills/_lib/sanitizer.py` | CREATE | (none — pure stdlib) | ~150 |
| `skills/_lib/tribunal.py` | CREATE | `skills._lib.event_log`, `skills._lib.event_types`, `skills._lib.sanitizer` | ~250 |
| `skills/_lib/memory.py` | CREATE | `skills._lib.lock`, `skills._lib.event_log` | ~280 |
| `skills/_lib/session.py` | CREATE | `skills._lib.state_vector`, `skills._lib.event_log` | ~220 |
| `skills/_lib/agents.py` | CREATE | `skills._lib.event_log`, `skills._lib.event_types` | ~250 |
| `tests/unit/test_sanitizer.py` | CREATE | (none) | ~150 |
| `tests/unit/test_tribunal.py` | CREATE | `skills._lib.tribunal` | ~200 |
| `tests/unit/test_memory.py` | CREATE | `skills._lib.memory` | ~200 |
| `tests/unit/test_session.py` | CREATE | `skills._lib.session` | ~150 |
| `tests/unit/test_agents.py` | CREATE | `skills._lib.agents` | ~200 |

**Total:** ~2050 lines (5 modules + 5 tests).

---

## Code Patterns to Follow

Reference: `skills/_lib/event_types.py`, `skills/_lib/human_nodes.py`, `tests/unit/test_human_nodes.py`.

All modules MUST follow these conventions:

```python
"""One-line module docstring.

Longer description if needed, including cross-module dependencies.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Dict, List, Tuple

# Lazy imports for cross-module deps (avoid circular):
# from skills._lib.event_log import EventLog  # noqa: E402
```

**Test conventions** (see `tests/unit/test_human_nodes.py`):
- Use pytest fixtures, not classes
- Use `monkeypatch.setitem(sys.modules, ...)` for module stubs
- One behavior per test, descriptive name
- Use real subprocess execution when possible
- Avoid mocking — use stubs that call real implementations

---

## Dependency Order

Tasks run sequentially because later tasks depend on earlier ones:
1. **sanitizer** (no deps) → unblocks Tribunal
2. **tribunal** (depends on sanitizer) → unblocks nothing but validates integration
3. **memory** (depends on lock + event_log) → independent of tribunal
4. **session** (depends on state_vector + event_log) → independent of tribunal
5. **agents** (depends on event_log + event_types) → independent of tribunal

Tasks 2-5 are **independent of each other** once Task 1 (sanitizer) is done. Tasks 3, 4, 5 can run **in parallel** with Task 2.

---

## Task 1: Sanitizer Module

**Files:**
- Create: `skills/_lib/sanitizer.py`
- Test: `tests/unit/test_sanitizer.py`

**Public API:**
```python
@dataclass
class SanitizationResult:
    sanitized_text: str
    redactions: List[Tuple[str, str]]  # (pattern_name, original)
    had_sensitive_data: bool

def sanitize(text: str, whitelist: Optional[List[str]] = None) -> SanitizationResult:
    """Redact API keys, passwords, and sensitive paths."""

# Pre-defined patterns:
API_KEY_PATTERNS: List[str] = [...]  # regex patterns
PASSWORD_PATTERNS: List[str] = [...]
SENSITIVE_PATH_PATTERNS: List[str] = [...]
```

**Required behavior:**
- Detect API keys (regex: `sk-[a-zA-Z0-9]{20,}`, `api_key=...`, Bearer tokens)
- Detect passwords (`password=...`, `passwd=...`, env var names containing SECRET/TOKEN/KEY)
- Detect sensitive paths (`/etc/`, `~/.ssh/`, `~/.aws/`)
- Replace with `<REDACTED>` placeholder
- Whitelist allowed paths (regex match against path string)
- Performance: < 10ms per check (per spec requirement)

**Tests required (≥ 8 tests):**
1. `test_sanitize_strips_api_key_sk_format`
2. `test_sanitize_strips_bearer_token`
3. `test_sanitize_strips_password_kvpair`
4. `test_sanitize_strips_secret_env_var`
5. `test_sanitize_strips_sensitive_path_etc`
6. `test_sanitize_strips_sensitive_path_ssh`
7. `test_whitelist_path_not_redacted`
8. `test_no_sensitive_data_unchanged`
9. `test_redactions_list_populated`
10. `test_performance_under_10ms`

---

## Task 2: Tribunal Module

**Files:**
- Create: `skills/_lib/tribunal.py`
- Test: `tests/unit/test_tribunal.py`

**Public API:**
```python
@dataclass
class TribunalResult:
    passed: bool
    exec_score: float
    review_score: float
    final_score: float
    conflict: float
    warnings: List[str] = field(default_factory=list)

class Tribunal:
    def __init__(self, executor, reviewer, sanitizer=None):
        """executor/reviewer are callables taking (change_name, criteria) -> float."""
        ...
    def verify(self, change_name: str, criteria: str, context: dict) -> TribunalResult:
        """Run executor and reviewer, compute weighted score."""
    def _judge(self, exec_score: float, review_score: float) -> Tuple[float, float]:
        """Return (final_score, conflict)."""
```

**Required behavior (per ADR-0008):**
- Formula: `final_score = exec_score * 0.4 + review_score * 0.6`
- Pass condition: `final_score >= 0.8 AND exec_score >= 0.5 AND review_score >= 0.5 AND conflict < 0.4`
- Sanitize context before passing to executor/reviewer
- Record `verification_completed` event to event log
- Warn (not fail) when executor == reviewer

**Tests required (≥ 8 tests):**
1. `test_judge_formula_weighted`
2. `test_pass_when_high_both`
3. `test_fail_when_low_final_score`
4. `test_fail_when_high_conflict`
5. `test_fail_when_one_agent_low`
6. `test_warn_when_same_agent`
7. `test_sanitize_context_before_invocation`
8. `test_record_verification_event`
9. `test_graceful_degradation_on_exception`

**Integration with human_nodes:**
The Tribunal enables `VerificationMode.MULTI_MODEL` in `human_nodes.py`. After this task, that mode should no longer raise `MultiModelUnavailableError`.

---

## Task 3: Memory Module

**Files:**
- Create: `skills/_lib/memory.py`
- Test: `tests/unit/test_memory.py`

**Public API:**
```python
@dataclass
class ExecutionRecord:
    change_name: str
    goal: str
    config: Dict[str, Any]
    iterations: int
    result: str  # "success" / "failure"
    failure_reason: Optional[str]
    timestamp: str
    duration_seconds: float

class LoopMemory:
    DEFAULT_PATH = ".spec-workflow/memory.jsonl"
    MAX_RECORDS = 10000

    def __init__(self, path: Optional[str] = None):
        ...
    def record_execution(self, record: ExecutionRecord) -> None: ...
    def get_execution_history(self, change_name: Optional[str] = None, limit: int = 100) -> List[ExecutionRecord]: ...
    def get_insights_for_change(self, change_name: str) -> Dict[str, Any]: ...
    def suggest_config(self, goal: str) -> Optional[Dict[str, Any]]: ...
    def get_last_interrupted(self) -> Optional[ExecutionRecord]: ...
    def repeated_failure_warning(self, change_name: str) -> Optional[str]: ...
    def archive(self) -> int: ...  # returns count archived
```

**Required behavior (per ADR-0006 § Memory):**
- JSONL append-only writes (consistent with EventLog)
- File lock for concurrent access
- 10K record cap; archive oldest when exceeded
- Heuristic similarity for config suggestion (Jaccard on goal token set + config key match)
- Interruption recovery: return most recent incomplete record (`result == "interrupted"`)
- Repeated-failure warning: ≥ 3 failures for same change

**Tests required (≥ 10 tests):**
1. `test_record_execution_writes_jsonl`
2. `test_get_history_filters_by_change`
3. `test_get_history_respects_limit`
4. `test_insights_for_change_aggregates`
5. `test_suggest_config_finds_similar_goal`
6. `test_suggest_config_returns_none_when_no_match`
7. `test_interrupted_recovery_returns_last`
8. `test_repeated_failure_warning_at_threshold`
9. `test_archive_when_over_cap`
10. `test_concurrent_writes_safe_via_lock`

---

## Task 4: Session Module

**Files:**
- Create: `skills/_lib/session.py`
- Test: `tests/unit/test_session.py`

**Public API:**
```python
class SessionState(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class Session:
    session_id: str
    parent_session_id: Optional[str]
    goal: str
    state: SessionState
    started_at: str
    updated_at: str

class SessionCoordinator:
    def __init__(self, state_vector, event_log):
        ...
    def create_session(self, goal: str, parent_session_id: Optional[str] = None) -> Session: ...
    def find_session(self, session_id: str) -> Optional[Session]: ...
    def update_session_status(self, session_id: str, new_state: SessionState) -> None: ...
    def list_sessions(self, parent_session_id: Optional[str] = None) -> List[Session]: ...
```

**Required behavior (per ADR-0010):**
- Sessions stored in state vector under `session_info` and `sub_sessions` fields
- Parent-child relationships tracked
- State transitions: `active → paused → active`, `active → completed`, `active → failed`
- v2.0 is **sequential** coordination (parent blocks on sub-session) — explicit comment in code

**Tests required (≥ 7 tests):**
1. `test_create_session_writes_to_state_vector`
2. `test_find_session_returns_created`
3. `test_update_session_status_validates_transition`
4. `test_list_sessions_filters_by_parent`
5. `test_parent_child_relationship_tracked`
6. `test_session_state_transitions_validated`
7. `test_invalid_transition_raises`

---

## Task 5: Agents Module

**Files:**
- Create: `skills/_lib/agents.py`
- Test: `tests/unit/test_agents.py`

**Public API:**
```python
class AgentRole(str, Enum):
    PLANNER = "planner"
    EXECUTOR = "executor"
    VERIFIER = "verifier"

@dataclass
class AgentMessage:
    role: AgentRole
    content: str
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)

class Agent:
    def __init__(self, role: AgentRole, event_log=None): ...
    def send(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> AgentMessage: ...
    def receive(self) -> List[AgentMessage]: ...

class AgentCoordinator:
    """Orchestrates Planner → Executor → Verifier flow."""
    def __init__(self, event_log, planner, executor, verifier): ...
    def run(self, goal: str) -> Tuple[str, float]:
        """Returns (final_result, quality_score)."""
```

**Required behavior:**
- Three agent roles with distinct concerns
- Communication via shared state (state vector or event log)
- Each agent records its actions to event log
- Coordinator runs full Planner→Executor→Verifier cycle
- Quality score from Verifier (0.0-1.0)

**Tests required (≥ 8 tests):**
1. `test_three_agent_roles_defined`
2. `test_agent_send_records_event`
3. `test_agent_receive_returns_messages`
4. `test_planner_generates_plan`
5. `test_executor_runs_actions`
6. `test_verifier_scores_quality`
7. `test_coordinator_runs_full_flow`
8. `test_coordinator_records_each_step`

---

## Execution Strategy

**Subagent-Driven Execution** (per writing-plans recommendation):

1. Dispatch one subagent per task (Tasks 1-5) in parallel after Task 1 (sanitizer) is done
2. Each subagent follows TDD strictly:
   - RED: write failing test
   - Verify RED: run test, confirm fails for expected reason
   - GREEN: write minimal implementation
   - Verify GREEN: run test, confirm passes
   - REFACTOR: clean up if needed
   - COMMIT: `git commit -m "feat(_lib): <module-name> (<feature>) — closes <task-ids>"`
3. After all 5 tasks complete:
   - Run full test suite: `pytest tests/unit/`
   - Mark all tasks in `openspec/changes/v2-advanced-features/tasks.md` as `[x]`
   - Update `design.md` if any decisions changed
4. Final verification + archive

**Per-subagent prompt structure:**
- Reference this plan
- Reference existing patterns: `skills/_lib/event_types.py`, `skills/_lib/human_nodes.py`, `tests/unit/test_human_nodes.py`
- Exact file paths
- Exact test names (from the "Tests required" lists above)
- TDD requirement (write tests first)
- Commit message format

---

## Verification Checklist (before archive)

- [ ] All 5 modules created with proper docstrings
- [ ] All 5 test files created with ≥ specified test counts
- [ ] `pytest tests/unit/` passes 100% (0 failures, 0 errors)
- [ ] `pytest tests/unit/test_human_nodes.py::test_multi_model_raises_not_implemented` no longer raises (Tribunal integrated)
- [ ] `pytest tests/integration/` shows zero regressions
- [ ] All tasks in `openspec/changes/v2-advanced-features/tasks.md` marked `[x]`
- [ ] Commit history shows atomic commits per task
- [ ] No files modified outside the planned scope

---

## Post-Execution: Archive

```bash
# Mark all tasks complete first (per openspec workflow)
# Update tasks.md checkboxes

# Then archive
openspec archive v2-advanced-features
```

The archive command will move `openspec/changes/v2-advanced-features/` to `openspec/changes/archive/2026-06-26-v2-advanced-features/` and update main specs.

---

**Plan length:** ~200 lines (concise by design — subagents have full context to fill in implementation details following established patterns)