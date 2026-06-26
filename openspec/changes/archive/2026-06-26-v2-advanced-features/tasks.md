## 1. Human-in-Loop Node Refinement (P3-T1)

- [x] 1.1 Refine 7 node types: `arch.adr_create`, `arch.roadmap_define`, `plan.change_select`, `plan.propose_confirm`, `ship.archive_confirm`, `ship.cleanup_confirm`, `ship.execute_error`
- [x] 1.2 Three verification modes: `human`, `multi_model`, `script`
- [x] 1.3 Two node policies: `fixed` (cannot override, e.g., `adr_create` must be `human`), `configurable` (user can set)
- [x] 1.4 Implement `skip_if` config for conditional skipping
- [x] 1.5 Write tests: 7 nodes × 3 modes = 21 scenarios, fixed policy enforcement, skip_if

## 2. Tribunal Committee (P3-T2)

- [x] 2.1 Create `skills/_lib/tribunal.py` with `Tribunal` class
- [x] 2.2 Implement `execute_verification()` calling Executor agent
- [x] 2.3 Implement `review_verification()` calling Reviewer agent
- [x] 2.4 Implement `judge()`: `final_score = exec_score * 0.4 + review_score * 0.6`
- [x] 2.5 Pass condition: `final_score >= 0.8 AND both pass AND conflict < 0.4`
- [x] 2.6 Subprocess invocation of oh-my-opencode CLI for executor/reviewer
- [x] 2.7 Executor and Reviewer must be different agents; warn if same
- [x] 2.8 Record verification_completed event to event log
- [x] 2.9 Write tests: scoring algorithm, threshold enforcement, conflict warning, same-agent warning

## 3. Sanitizer (P3-T2 sub-task)

- [x] 3.1 Create `skills/_lib/sanitizer.py` with `sanitize()` function
- [x] 3.2 Detect: API keys (regex patterns), passwords (env var names), sensitive paths (`/etc/`, `~/.ssh/`)
- [x] 3.3 Replace with `<REDACTED>` placeholder
- [x] 3.4 Support whitelist for allowed paths
- [x] 3.5 Write tests: known secrets detected, whitelist respected, performance < 10ms per check

## 4. Memory System (P3-T3)

- [x] 4.1 Create `skills/_lib/memory.py` with `LoopMemory` class
- [x] 4.2 Implement `record_execution()` writing to `.spec-workflow/memory.jsonl`
- [x] 4.3 Implement `get_execution_history()` with filtering
- [x] 4.4 Implement `get_insights_for_change(change_name)` returning failure patterns
- [x] 4.5 Implement `suggest_config(goal)` using heuristic similarity (goal string + config similarity)
- [x] 4.6 Implement interruption recovery: show last execution context, suggest resumption
- [x] 4.7 Implement repeated-failure warning: same change failed ≥ 3 times
- [x] 4.8 Cap memory at 10K records; provide archive command
- [x] 4.9 Write tests: recording, query, insights, suggestion, recovery, warning, cap

## 5. Lightweight Session Management (P3-T4)

- [x] 5.1 Extend state vector with `session_info` and `sub_sessions` fields
- [x] 5.2 Create `skills/_lib/session.py` with `SessionCoordinator` class
- [x] 5.3 Implement `create_session()`, `find_session()`, `update_session_status()`, `list_sessions()`
- [x] 5.4 Parent-child session relationships via state vector
- [x] 5.5 Session state machine: `active → paused → active`, `active → completed`, `active → failed`
- [x] 5.6 Document: v2.0 is sequential, v2.1 adds true parallel
- [x] 5.7 Write tests: CRUD operations, parent-child, state transitions, no parallel assertion

## 6. Multi-Agent Coordination (P3-T5)

- [x] 6.1 Create `skills/_lib/agents.py` with `Agent` base class
- [x] 6.2 Define 3 agent roles: Planner (analyze state, generate plan), Executor (run actions), Verifier (validate results, score quality)
- [x] 6.3 Implement agent communication via state vector
- [x] 6.4 Each agent records its actions to event log
- [x] 6.5 Write tests: each role independently, full Planner→Executor→Verifier flow, state vector communication
