## Why

Phase 4 implements the three-phase architecture (ADR-0003) by splitting the existing v1.x `guide-spec.md` into two new skills (`guide-arch.md` for architecture definition, `guide-plan.md` for change generation), backed by a comprehensive test suite and migration documentation. Without this change, the v2.0 state vector, loop engine, and tribunal have no public-facing workflow skills to drive them. This is the change that makes v2.0 user-visible.

## What Changes

- **Add** `skills/guide-arch.md` — architecture definition phase (setup → adr-create → architecture → roadmap-define → arch-done), integrates gate (arch_done)
- **Add** `skills/guide-plan.md` — change generation phase (scan → propose → deps → plan-done), integrates gate (plan_done); forked from `guide-spec.md`
- **Modify** `skills/guide.md` — recommender updates to support three-phase scan (arch/plan/ship)
- **Add** `.zcf/.arch-handoff.json` — phase transition handoff (ADR count, roadmap state, gap analysis)
- **Add** `.zcf/.plan-handoff.json` — phase transition handoff (active changes, artifacts state, deps analysis)
- **Add** `tests/unit/` — 10 unit test files (test_state_vector, test_event_log, test_gate, test_config, test_loop_engine, test_detectors, test_actions, test_tribunal, test_memory, test_session)
- **Add** `tests/integration/` — 3 integration test files (test_loop_flow, test_gate_transition, test_phase_switch)
- **Add** `docs/migration/v1-to-v2.md` — user migration guide (already drafted in commit 9b9018e, will be enhanced)
- **Modify** `README.md` — add v2.0 features, update workflow diagram
- **Modify** `USAGE.md` — update skill list, add Loop engine examples

## Capabilities

### New Capabilities
- `guide-arch-skill`: Architecture definition phase state machine
- `guide-plan-skill`: Change generation phase state machine
- `unit-test-suite`: pytest-based unit tests for all v2 Python modules (≥ 80% coverage)
- `integration-test-suite`: End-to-end tests for loop flow, gate transition, phase switch
- `migration-guide`: v1.x → v2.0 user migration documentation

### Modified Capabilities
- `guide-recommender` (existing `skills/guide.md`): Extended to recommend three phases (arch/plan/ship) instead of two (spec/ship)

## Impact

- **New code**: ~350 lines Markdown (guide-arch ~200, guide-plan ~150) + ~1,500 lines Python tests
- **Dependencies**: pytest (for test suite); all else from previous changes
- **Compatibility**: 100% backward compatible — `guide-spec.md` retained as alias that internally calls arch → plan
- **Risk**: Medium — splitting a working skill risks regression; mitigated by alias + integration tests
- **Source**: v2-implementation-plan.md § Phase 4 (P4-T1 ~ P4-T4)
