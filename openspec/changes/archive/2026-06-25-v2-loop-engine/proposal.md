## Why

The v2.0 architecture (ADR-0004) describes a Loop-driven engine that replaces v1.x's static state machine with a `verify_goal → scan_state → generate_plan → execute_plan → verify_results → adapt` cycle. This engine is the core "AI-native" innovation of v2.0 and the prerequisite for the tribunal (Phase 3) and customization layer (Phase 4). Without the loop engine, the state vector and gate mechanism (from `v2-core-foundation`) have no consumer.

## What Changes

- **Add** `skills/loop-engine.py` — main `LoopEngine` class with `run()` cycle and 6 building-block methods
- **Add** `skills/_lib/detectors.py` — 8 built-in detectors (worktrees, pending changes, archived, roadmap, ADR status, health, test gaps, stale branches)
- **Add** `skills/_lib/actions.py` — 7 built-in actions (create_worktree, generate_plan, execute_worktree, archive_change, cleanup_stale, update_roadmap, create_adr)
- **Add** `skills/_lib/interaction_modes.py` — Loop / Menu / Hybrid mode implementations
- **Add** `skills/_lib/human_nodes.py` — Human-in-Loop node registry with verification-mode dispatch
- **Add** `skills/_lib/design_phase.py` — design-first phase (Goal/Verification/Control design)
- **Add** `skills/_lib/flowchart.py` — ASCII flowchart generator reading state vector + event log
- **Add** `tests/unit/test_loop_engine.py`, `test_detectors.py`, `test_actions.py`, `test_interaction_modes.py`, `test_human_nodes.py`

## Capabilities

### New Capabilities
- `loop-engine`: Main loop cycle with 5 building blocks + safety mechanisms (max iterations, retries, oscillation detection, circuit breaker)
- `detectors`: 8 built-in state detectors with extension API via `.rdd-workflow/detectors/`
- `actions`: 7 built-in actions with subprocess invocation + 30-min timeout
- `interaction-modes`: Loop / Menu / Hybrid modes with runtime config override
- `human-in-loop-nodes`: 7 key node types (arch.adr_create, plan.change_select, ship.archive_confirm, etc.) with 3 verification modes (human/multi_model/script)
- `design-first-phase`: Pre-loop design phase for Goal/Verification/Control design
- `flowchart`: ASCII flowchart generator with real-time progress display

### Modified Capabilities
- None

## Impact

- **New code**: ~2,500 lines Python (loop-engine ~500, detectors ~400, actions ~350, interaction_modes ~250, human_nodes ~300, design_phase ~150, flowchart ~100) + ~150 lines tests
- **Dependencies**: All from v2-core-foundation (state vector, event log, gate); no new external deps
- **Compatibility**: 100% backward compatible — v1.x skills continue to work via the sync layer
- **Risk**: Medium — complex state machine; safety mechanisms (max_iterations, circuit breaker) are critical
- **Source**: v2-implementation-plan.md § Phase 2 (P2-T1 ~ P2-T6)
