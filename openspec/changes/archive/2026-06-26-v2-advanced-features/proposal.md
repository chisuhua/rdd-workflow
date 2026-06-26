## Why

v2.0 ADRs (0004, 0005, 0006, 0008, 0010) describe advanced features that build on the loop engine: the Tribunal committee (multi-agent cross-validation with data sanitization), Memory system (interruption recovery, config recommendation, failure warnings), lightweight session management (v2.0 phased, v2.1 full), and multi-agent coordination (Planner/Executor/Verifier roles). These features deliver the v2 promise of "AI-native" workflow automation that learns from past executions and self-corrects.

## What Changes

- **Add** `skills/_lib/tribunal.py` — `Tribunal` class with `execute_verification()`, `review_verification()`, weighted `judge()` (0.4/0.6)
- **Add** `skills/_lib/sanitizer.py` — automatic detection and redaction of API keys, passwords, sensitive paths
- **Add** `skills/_lib/memory.py` — `LoopMemory` class for execution history, insights, config recommendations
- **Add** `skills/_lib/session.py` — `SessionCoordinator` for lightweight session management (v2.0)
- **Add** `skills/_lib/agents.py` — Planner/Executor/Verifier agent framework with state-vector-based communication
- **Add** `tests/unit/test_tribunal.py`, `test_sanitizer.py`, `test_memory.py`, `test_session.py`, `test_agents.py`

## Capabilities

### New Capabilities
- `tribunal`: Multi-agent cross-validation with weighted scoring (0.4 exec + 0.6 review), final_score ≥ 0.8 to pass, conflict > 0.4 warns
- `sanitizer`: Data redaction for API keys, passwords, sensitive paths before cross-agent verification
- `memory-system`: Execution history, interruption recovery, config recommendation based on similar past goals
- `session-management`: v2.0 lightweight (sequential coordination), v2.1 full (true parallel)
- `agent-coordination`: Planner → Executor → Verifier roles communicating via state vector

### Modified Capabilities
- `human-in-loop-nodes` (from `v2-loop-engine`): Refined to 7 specific node types with `fixed` and `configurable` policies

## Impact

- **New code**: ~1,500 lines Python (tribunal ~250, sanitizer ~150, memory ~300, session ~200, agents ~250) + ~200 lines tests
- **Dependencies**: All from v2-core-foundation and v2-loop-engine; no new external deps
- **Compatibility**: 100% backward compatible — all features are opt-in via config
- **Risk**: Medium — Tribunal depends on external agent invocation (oh-my-opencode CLI); failure modes need robust handling
- **Source**: v2-implementation-plan.md § Phase 3 (P3-T1 ~ P3-T5)
