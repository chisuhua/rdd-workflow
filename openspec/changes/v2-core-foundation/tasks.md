## 1. State Vector Foundation (P1-T1)

- [x] 1.1 Create `skills/_lib/state_vector.py` with `StateVector` class (load/save/update_field/validate/create_default/reset)
- [x] 1.2 Create `skills/_lib/lock.py` with `FileLock` class (fcntl-based, 10s timeout, context manager)
- [x] 1.3 Create `skills/_lib/schemas/state_vector_schema.json` with fields: goal, arch_side, plan_side, ship_side, loop_state, memory, metadata
- [x] 1.4 Add checksum field to state vector for corruption detection
- [x] 1.5 Add `version: "2.0"` and `metadata.spec_workflow_version` + `metadata.git_commit` fields
- [x] 1.6 Write unit tests: read/write roundtrip, concurrent read+write (2 processes), invalid schema rejection, file size < 50KB
- [x] 1.7 Verify read/write latency < 10ms on local FS

## 2. Event Log (P1-T2)

- [x] 2.1 Create `skills/_lib/event_log.py` with `EventLog` class (record/query/get_progress_report/generate_id)
- [x] 2.2 Create `skills/_lib/event_types.py` with 17 event types (loop_started, scan_completed, plan_generated, ...) and severity enum (debug/info/warn/error)
- [x] 2.3 Create `skills/_lib/event_context.py` reading current context from state vector
- [x] 2.4 Event ID format: `evt_YYYYMMDD_HHMMSS_NNN` (unique within same second)
- [x] 2.5 Write unit tests: write→query consistency, query 10K events < 100ms, unique IDs
- [x] 2.6 Verify progress report stats accuracy (iterations, completed units, error count)

## 3. Gate Mechanism (P1-T3)

- [x] 3.1 Create `skills/_lib/gate.py` with `GateMechanism` class (verify_transition/handle_gate_failure/get_suggestion)
- [x] 3.2 Define `Check` namedtuple: name, condition (lambda), message, severity
- [x] 3.3 Implement `register_gate_check()` plugin API
- [x] 3.4 Define default arch_done checks: adr_exists (error), roadmap_defined (error), gap_analysis_complete (warning)
- [x] 3.5 Define default plan_done checks: changes_committed (error), artifacts_complete (error), deps_analyzed (warning)
- [x] 3.6 Define default ship_done checks: worktrees_empty (error), archive_empty (error), tests_pass (error)
- [x] 3.7 Write unit tests: error blocks, warning allows-with-notice, force_transition records to event log, plugin works, suggestions actionable
- [x] 3.8 Create `skills/_lib/plugins/README.md` with plugin development guide

## 4. Configuration Parser (P1-T4)

- [ ] 4.1 Create `skills/_lib/config.py` with `ConfigParser` class (parse `.spec-workflow.json` and `loop.yaml`)
- [ ] 4.2 Implement priority-merge: runtime params > loop.yaml > .spec-workflow.json > env vars > defaults
- [ ] 4.3 Create `skills/_lib/defaults.py` with default values (mode=hybrid, max_iterations=100, max_retries=3)
- [ ] 4.4 Read env vars: `SPEC_WORKFLOW_MODE`, `SPEC_WORKFLOW_MAX_ITERATIONS` with type conversion
- [ ] 4.5 Validate required fields, enum values (mode in loop/menu/hybrid), numeric ranges (max_iterations > 0)
- [ ] 4.6 Add `PyYAML` to package.json dependencies
- [ ] 4.7 Write unit tests: minimal config parses, priority order correct, invalid config rejected with clear message, env vars override file config

## 5. v1.x Sync Layer (P1-T5)

- [ ] 5.1 Create `skills/_lib/sync_state.py` with `sync_state_vector_to_legacy()` and `sync_legacy_to_state_vector()`
- [ ] 5.2 Sync targets: `.zcf/.roadmap-state.json`, `proposal-suggestions.md`, `openspec/changes/<name>/.openspec.yaml`
- [ ] 5.3 Implement conflict detection via mtime; state vector wins on conflict
- [ ] 5.4 Log conflicts to event log
- [ ] 5.5 Write unit tests: state vector update triggers v1.x sync, v1.x change triggers state update, latency < 50ms, conflict resolution correct
- [ ] 5.6 Verify sync layer can be disabled via env var (escape hatch)

## 6. Integration & Documentation

- [ ] 6.1 Update `docs/v2-api-reference.md` with new public APIs
- [ ] 6.2 Update `docs/v2-config-schema.md` with `.spec-workflow.json` schema
- [ ] 6.3 Run full test suite: `pytest tests/unit/`
- [ ] 6.4 Verify zero regressions in v1.x skills (run `tests/integration/`)
