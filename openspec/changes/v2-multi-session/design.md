## Context

v2.0.0-beta ships a lightweight `SessionCoordinator` (`skills/_lib/session.py`, 266 lines) that provides sequential parent-child session coordination with in-memory storage. Per ADR-0010, the full v2.1 implementation adds true parallelism, dependency scheduling, IPC, and state-vector persistence.

## Goals / Non-Goals

**Goals:**
- `SessionManager` with `ProcessPoolExecutor` for true parallel session execution
- `DependencyScheduler` with topological sort (Kahn's algorithm) for change dependency resolution
- Inter-process communication via message queue for cross-session coordination
- State vector schema extension for `session_management` and `dependency_graph` blocks
- Dynamic load balancing and basic crash recovery (session checkpointing)
- Full test coverage for all new modules

**Non-Goals:**
- Changing the v2.0 `SessionCoordinator` API (backward compatible)
- Removing v2.0 lightweight mode (it remains as fallback)
- Implementing the full ADR-0012 flow customization layer
- Multi-host distributed sessions (single-machine multi-process only)

## Decisions

### Decision 1: New files, not extension of session.py

`SessionManager` and `DependencyScheduler` are new files. v2.0 `session.py` stays untouched — backward compatibility guaranteed.

### Decision 2: ProcessPoolExecutor, not ThreadPoolExecutor

True parallelism requires separate processes (Python GIL). `ProcessPoolExecutor` is stdlib, zero extra dependencies. IPC via `multiprocessing.Queue`.

### Decision 3: Opt-in via config, not automatic

Full parallel mode is opt-in via `.spec-workflow.json`: `{"session": {"mode": "parallel"}}`. Default stays sequential (v2.0 behavior). Zero breakage for existing users.

### Decision 4: DAG resolution at change level, not task level

DependencyScheduler resolves dependencies at the change level (`add-auth` → `add-user-profile`), not individual tasks. Tasks within a change always execute sequentially.

## Architecture

```
SessionManager
  ├── spawns sessions via ProcessPoolExecutor
  ├── reads DependencyScheduler for execution order
  ├── uses multiprocessing.Queue for IPC
  ├── persists to state vector (session_management + dependency_graph blocks)
  └── falls back to SessionCoordinator when mode=sequential

DependencyScheduler
  ├── build_dependency_graph(changes) → DiGraph
  ├── topological_sort(graph) → execution_order
  ├── can_execute(change, completed) → bool
  └── remaining_dependencies(change, graph) → list

State vector schema extension:
  session_management: { current_session, active_sessions, session_statistics }
  dependency_graph: { nodes, edges, execution_order }
```