## 1. Loop Engine Core (P2-T1)

- [x] 1.1 Create `skills/loop-engine.py` with `LoopEngine` class implementing `run()` main loop
- [x] 1.2 Implement 5 building blocks: `verify_goal`, `scan_state`, `generate_plan`, `execute_plan`, `verify_results`, `adapt`
- [x] 1.3 Implement safety mechanisms: max_iterations (default 100), max_retries (default 3), oscillation detection (5 same states), 30-min action timeout, circuit breaker (3 failures)
- [x] 1.4 Implement goal-achievement detection supporting multiple goal types from config (`success_criteria`)
- [x] 1.5 Implement plan generation: detector→action matching with priority + dependency analysis
- [x] 1.6 Write unit tests: full cycle, safety triggers, oscillation detection, goal detection, event log coverage
- [x] 1.7 Write integration test: scan→plan→execute→verify→adapt with mock state

## 2. Detectors (P2-T2)

- [x] 2.1 Create `skills/_lib/detectors.py` with `Detector` base class and `DetectionResult` (type, data, message)
- [x] 2.2 Implement 8 built-in detectors: `detect_worktrees`, `detect_pending_changes`, `detect_archived_changes`, `detect_roadmap_state`, `detect_adr_status`, `detect_health_issues`, `detect_test_gaps`, `detect_stale_branches`
- [x] 2.3 Implement plugin loading from `.spec-workflow/detectors/`
- [x] 2.4 All detectors return structured `DetectionResult`
- [x] 2.5 All 8 detectors run in < 500ms total
- [x] 2.6 Write unit tests for each detector + plugin loading

## 3. Actions (P2-T3)

- [x] 3.1 Create `skills/_lib/actions.py` with `Action` base class and `ActionResult` (success, data, error)
- [x] 3.2 Implement 7 built-in actions: `action_create_worktree`, `action_generate_plan`, `action_execute_worktree`, `action_archive_change`, `action_cleanup_stale`, `action_update_roadmap`, `action_create_adr`
- [x] 3.3 Subprocess invocation with stdout/stderr capture + 30-min timeout
- [x] 3.4 Plugin loading from `.spec-workflow/actions/`
- [x] 3.5 Write unit tests: each action (mocked subprocess), error handling, timeout, event log integration

## 4. Three Interaction Modes (P2-T4)

- [x] 4.1 Implement Loop mode (autonomous, skip all human nodes except on error)
- [x] 4.2 Implement Menu mode (manual, every decision point shows menu)
- [x] 4.3 Implement Hybrid mode (default, automatic for routine + human at key nodes)
- [x] 4.4 Implement Human-in-Loop node registry with verification modes (human/multi_model/script)
- [x] 4.5 Menu system with options: select/skip/modify/abort
- [x] 4.6 Mode switchable at runtime via parameter
- [x] 4.7 Write tests: each mode in isolation, mode switching mid-loop

## 5. Design-First Phase (P2-T5)

- [x] 5.1 Implement Goal Design (display goal + completion criteria, await confirmation)
- [x] 5.2 Implement Verification Design (configure Executor/Reviewer agents)
- [x] 5.3 Implement Control Design (configure max_iterations, max_retries, oscillation threshold)
- [x] 5.4 User can modify design parameters before loop starts
- [x] 5.5 Design result saved to state vector
- [x] 5.6 Write tests: design phase runs before loop, modifications persist, defaults applied

## 6. Flowchart Generator (P2-T6)

- [x] 6.1 Create `skills/_lib/flowchart.py` reading state vector + event log
- [x] 6.2 Generate ASCII flowchart showing current phase, gate status, progress
- [x] 6.3 Real-time display: refresh on each iteration
- [x] 6.4 Include: current phase, gate status, errors/warnings, iteration count
- [x] 6.5 Write tests: flowchart format stable, updates on state change
