## Why

spec-workflow v1.x scatters state across 13 files (`.zcf/.roadmap-state.json`, `proposal-suggestions.md`, individual change `.openspec.yaml`, etc.) and has no formal transition validation between workflow phases. This creates race conditions, ambiguous recovery, and no enforcement that phases complete in order. v2.0 ADRs (ADR-0006, ADR-0007, ADR-0002) commit to a unified state vector + event log + two-level gate mechanism, but no code exists yet.

## What Changes

- **Add** `skills/_lib/state_vector.py` — unified state with file-locked load/save, JSON Schema validation, and nested-field updates
- **Add** `skills/_lib/event_log.py` — append-only JSONL event log with filtering, progress reports, and unique event IDs
- **Add** `skills/_lib/lock.py` — `fcntl`-based file lock with 10s default timeout and context-manager API
- **Add** `skills/_lib/gate.py` — `GateMechanism` class with arch_done / plan_done / ship_done checks and plugin registration
- **Add** `skills/_lib/config.py` + `defaults.py` — config parser for `.spec-workflow.json` and `loop.yaml` with priority-merge rules
- **Add** `skills/_lib/sync_state.py` — bidirectional sync between v2 state vector and v1.x legacy state files
- **Add** `skills/_lib/schemas/state_vector_schema.json` — JSON Schema definition with `goal`, `arch_side`, `plan_side`, `ship_side`, `loop_state`, `memory`, `metadata` fields
- **Add** `tests/unit/test_state_vector.py`, `test_event_log.py`, `test_gate.py`, `test_config.py`

## Capabilities

### New Capabilities
- `state-management`: Unified state vector + event log + file lock + v1.x sync layer (replaces 13 scattered v1.x state files)
- `gate-mechanism`: Two-level (error/warning) phase-transition checks with plugin extension API
- `configuration`: Multi-source config parser with priority-merge (runtime > loop.yaml > .spec-workflow.json > env > defaults)

### Modified Capabilities
- None (no existing spec-level behavior is changing; this is purely additive infrastructure)

## Impact

- **New code**: ~1,200 lines Python (state_vector ~300, event_log ~250, gate ~300, config ~200, sync ~200, lock ~100, schemas ~50)
- **Dependencies**: Adds `PyYAML` (for `loop.yaml` parsing); existing v1.x code untouched
- **Compatibility**: 100% backward compatible with v1.x — v1.x skills continue to work; sync layer keeps legacy files consistent
- **Risk**: Low — additive change; sync layer can be disabled if conflicts arise
- **Source**: v2-implementation-plan.md § Phase 1 (P1-T1 ~ P1-T5)
