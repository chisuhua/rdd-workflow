## 1. Three-Phase Architecture Split (P4-T1)

- [ ] 1.1 Create `skills/guide-arch.md` (architecture definition phase)
- [ ] 1.2 Implement 5 sub-phases: setup, adr-create, architecture, roadmap-define, arch-done
- [ ] 1.3 Integrate arch_done gate check (from v2-core-foundation)
- [ ] 1.4 Create `skills/guide-plan.md` (change generation phase)
- [ ] 1.5 Fork from `guide-spec.md` removing roadmap-related logic
- [ ] 1.6 Implement 4 sub-phases: scan, propose, deps, plan-done
- [ ] 1.7 Integrate plan_done gate check
- [ ] 1.8 Update `skills/guide.md` recommender for three-phase scan
- [ ] 1.9 Create `.zcf/.arch-handoff.json` (ADR count, roadmap state, gap analysis)
- [ ] 1.10 Create `.zcf/.plan-handoff.json` (active changes, artifacts state, deps)
- [ ] 1.11 Modify `skills/guide-spec.md` to be alias that calls arch → plan
- [ ] 1.12 Write tests: guide-arch phases, guide-plan phases, alias behavior, handoff JSONs

## 2. Unit Test Suite (P4-T2)

- [ ] 2.1 Create `tests/unit/` directory
- [ ] 2.2 Write `tests/unit/test_state_vector.py` (read/write, concurrent, validate, reset)
- [ ] 2.3 Write `tests/unit/test_event_log.py` (write/query/progress/ID uniqueness)
- [ ] 2.4 Write `tests/unit/test_gate.py` (checklist, failure handling, plugin)
- [ ] 2.5 Write `tests/unit/test_config.py` (parse, priority, validation)
- [ ] 2.6 Write `tests/unit/test_loop_engine.py` (main loop, safety, goal detection)
- [ ] 2.7 Write `tests/unit/test_detectors.py` (8 detectors)
- [ ] 2.8 Write `tests/unit/test_actions.py` (7 actions)
- [ ] 2.9 Write `tests/unit/test_tribunal.py` (scoring, threshold, degradation)
- [ ] 2.10 Write `tests/unit/test_memory.py` (record, query, recovery, warning, cap)
- [ ] 2.11 Write `tests/unit/test_session.py` (CRUD, parent-child, state transitions)
- [ ] 2.12 Verify unit test coverage ≥ 80%
- [ ] 2.13 All tests pass with 0 failures, 0 errors
- [ ] 2.14 Test execution time < 5 minutes

## 3. Integration Test Suite (P4-T2 cont.)

- [ ] 3.1 Write `tests/integration/test_loop_flow.py` (full scan→plan→execute→verify→adapt)
- [ ] 3.2 Write `tests/integration/test_gate_transition.py` (pass/fail/force)
- [ ] 3.3 Write `tests/integration/test_phase_switch.py` (arch→plan→ship)
- [ ] 3.4 Write `tests/integration/test_three_modes.py` (loop/menu/hybrid)
- [ ] 3.5 All integration tests pass

## 4. Migration Documentation (P4-T3)

- [ ] 4.1 Enhance `docs/migration/v1-to-v2.md` (already drafted in commit 9b9018e)
- [ ] 4.2 Add "Quick Start for v1.x Users" section
- [ ] 4.3 Add "Conceptual Changes" section (state machine → loop)
- [ ] 4.4 Add "Backward Compatibility" section (guide-spec alias, sync layer)
- [ ] 4.5 Add "FAQ" section

## 5. README and USAGE Updates (P4-T3)

- [ ] 5.1 Update `README.md` with v2.0 features list
- [ ] 5.2 Update workflow diagram to three phases
- [ ] 5.3 Add "Quick Start" section for v2.0
- [ ] 5.4 Update `USAGE.md` skill list (add guide-arch, guide-plan)
- [ ] 5.5 Add Loop engine usage example
- [ ] 5.6 Add configuration example

## 6. Complete Documentation (P4-T4)

- [ ] 6.1 Write Loop engine tutorial (quick start → config → best practices → troubleshooting)
- [ ] 6.2 Update `docs/v2-developer-guide.md` with extension examples
- [ ] 6.3 Update `docs/v2-api-reference.md` with final APIs
- [ ] 6.4 Verify all 12 v2 docs cross-link correctly
- [ ] 6.5 Verify no broken links

## 7. Final Verification

- [ ] 7.1 All unit tests pass: `pytest tests/unit/`
- [ ] 7.2 All integration tests pass: `pytest tests/integration/`
- [ ] 7.3 Coverage report shows ≥ 80%
- [ ] 7.4 v1.x integration tests still pass: `bats tests/integration/`
- [ ] 7.5 Migration guide reviewed by at least 2 v1.x users
- [ ] 7.6 README/USAGE updated and reviewed
