## Why

ADR-0010 currently has a v2.0 lightweight implementation that adds `session_info` and `sub_sessions` fields to the state vector and supports basic coordinator/worker role assignment. This is sufficient for simple parent-child cooperation but explicitly **does not support**:

- True parallel execution (v2.0 is round-robin within a single process, not multi-process)
- Dependency graph scheduling (changes must be ordered manually)
- Inter-session communication (sessions only share state via the state vector)
- Dynamic load balancing (changes assigned statically)
- Session persistence / crash recovery

Users running multi-change workflows with logical dependencies need automatic DAG scheduling and true parallelism to realize the full benefit of multi-session management. ADR-0010 §Decision §"v2.1: 方案 B" already specifies the target design.

## What Changes

- **`SessionManager`**: Full session manager replacing the v2.0 `SessionCoordinatorV20`; spawns sessions via `ProcessPoolExecutor` for true parallelism
- **`DependencyScheduler`**: Build dependency graph from change `deps`, perform Kahn-algorithm topological sort, gate change execution on completed dependencies
- **`session_ipc`**: Inter-process message queue for cross-session communication beyond the state vector
- **Extended state vector**: `session_management` and `dependency_graph` blocks per ADR-0010 §"完整状态向量扩展（v2.1）"
- **Load balancing & persistence**: Dynamic change-to-session assignment, session checkpointing, crash recovery
- **Backward compatibility**: v2.0 lightweight mode continues to work; full mode is opt-in via configuration
