# Tasks: add-workflow-synthesizer

> **For agentic workers:** REQUIRED SUB-SKILL: Use `skill_use("execute")` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

## Task 1: Dataclass skeleton + imports

**Files:**
- Create: `skills/_lib/workflow_synthesizer.py`
- Test: `tests/unit/test_workflow_synthesizer.py`

- [ ] Write failing test: `test_phase_status_immutable` and `test_workflow_recommendation_immutable` verify frozen dataclass
- [ ] Run test -> FAIL (module not found)
- [ ] Implement `PhaseStatus` and `WorkflowRecommendation` frozen dataclasses with importable module
- [ ] Run test -> PASS
- [ ] Commit: `feat(synthesizer): add dataclass skeleton + module shell`

## Task 2: synthesize() happy path - arch missing (path 1)

**Files:**
- Modify: `skills/_lib/workflow_synthesizer.py`
- Test: `tests/unit/test_workflow_synthesizer.py`

- [ ] Write failing test: `test_synthesize_arch_missing_recommends_guide_arch` (no .arch-handoff.json -> suggested_action="guide-arch", confidence="high")
- [ ] Run test -> FAIL (synthesize not implemented)
- [ ] Implement `synthesize()` with `_phase_status_arch`, `_phase_status_plan`, `_phase_status_ship` stubs returning defaults and the path-1 branch
- [ ] Run test -> PASS
- [ ] Commit: `feat(synthesizer): implement path 1 - arch missing -> guide-arch`

## Task 3: Paths 2-5 (arch + plan handoff decision tree)

**Files:**
- Modify: `skills/_lib/workflow_synthesizer.py`
- Test: `tests/unit/test_workflow_synthesizer.py`

- [ ] Write 4 failing tests: adr_count<1, arch done plan missing, plan-handoff 0 active, plan-handoff N active
- [ ] Run tests -> FAIL (only path 1 implemented)
- [ ] Implement paths 2-5 in `_decision_tree()`
- [ ] Run tests -> PASS
- [ ] Commit: `feat(synthesizer): implement paths 2-5 - handoff decision tree`

## Task 4: Paths 6-9 (worktree + git state)

**Files:**
- Modify: `skills/_lib/workflow_synthesizer.py`
- Test: `tests/unit/test_workflow_synthesizer.py`

- [ ] Write 4 failing tests: worktree w/ incomplete tasks, detached worktrees, worktree tasks done, committed change in HEAD
- [ ] Run tests -> FAIL
- [ ] Implement `_worktree_in_progress()`, `_committed_change_in_head()` helpers; wire paths 6-9
- [ ] Run tests -> PASS
- [ ] Commit: `feat(synthesizer): implement paths 6-9 - worktree + git state`

## Task 5: Paths 10-13 (fallbacks) + unblocked_changes

**Files:**
- Modify: `skills/_lib/workflow_synthesizer.py`
- Test: `tests/unit/test_workflow_synthesizer.py`

- [ ] Write 4 failing tests: no roadmap, no openspec/changes, pending proposal-suggestions, default
- [ ] Write 2 failing tests: `test_unblocked_changes_filters_blocker`, `test_unblocked_changes_empty_iteration`
- [ ] Run tests -> FAIL
- [ ] Implement paths 10-13 + `_unblocked_changes()`
- [ ] Run tests -> PASS
- [ ] Commit: `feat(synthesizer): implement paths 10-13 + unblocked_changes`

## Task 6: rddf-session integration (active_session + orphaned_sessions)

**Files:**
- Modify: `skills/_lib/workflow_synthesizer.py`
- Test: `tests/unit/test_workflow_synthesizer.py`

- [ ] Write 2 failing tests: active session bound when OPENCODE_SESSION_ID set, orphaned sessions listed
- [ ] Run tests -> FAIL
- [ ] Implement `_active_session()`, `_orphaned_sessions()`
- [ ] Run tests -> PASS
- [ ] Commit: `feat(synthesizer): rddf-session binding + orphan scan`

## Task 7: Phase status summary (3 phases)

**Files:**
- Modify: `skills/_lib/workflow_synthesizer.py`
- Test: `tests/unit/test_workflow_synthesizer.py`

- [ ] Write failing test: `test_phase_status_summary_3_phases` asserts tuple has 3 PhaseStatus entries with correct `phase` field values
- [ ] Run test -> FAIL
- [ ] Implement full `_phase_status_arch/plan/ship` with `detail` strings
- [ ] Run test -> PASS
- [ ] Commit: `feat(synthesizer): phase status summary for 3 phases`

## Task 8: Never-raises contract + corrupt state resilience

**Files:**
- Modify: `skills/_lib/workflow_synthesizer.py`
- Test: `tests/unit/test_workflow_synthesizer.py`

- [ ] Write 2 failing tests: corrupt sessions.json returns fallback recommendation, missing iteration.json returns fallback
- [ ] Run tests -> FAIL
- [ ] Wrap `synthesize()` body in try/except, return fallback `WorkflowRecommendation` on any exception
- [ ] Run tests -> PASS
- [ ] Commit: `feat(synthesizer): never-raises contract + corrupt state fallback`

## Task 9: Integration into guide.md with fallback

**Files:**
- Modify: `skills/guide/SKILL.md`
- Test: `tests/integration/test_guide_skill.bats`

- [ ] Write failing test (bats): assert `guide.md` includes Python synthesizer call block AND retains scan_state fallback
- [ ] Run test -> FAIL
- [ ] Modify guide.md to call Python synthesizer with fallback to scan_state
- [ ] Run test -> PASS
- [ ] Commit: `feat(guide): integrate workflow synthesizer with fallback to scan-state`

## Task 10: Regression tests + smoke verification

**Files:**
- Test: `tests/unit/test_workflow_synthesizer.py`

- [ ] Add comprehensive path-coverage test: iterate all 12+1 decision paths via parametrized fixture, assert (suggested_action, confidence) pairs
- [ ] Run `pytest tests/unit/test_workflow_synthesizer.py -v` -> all PASS
- [ ] Run `bats tests/integration/test_guide_skill.bats` -> all PASS
- [ ] Run `pytest tests/unit/ -q` -> no regressions
- [ ] Commit: `test(synthesizer): add parametrized 13-path coverage + regression suite`
