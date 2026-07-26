# Tasks: add-workflow-synthesizer

## Task 1: Dataclass skeleton + imports

**Files:**
- Create: `skills/_lib/workflow_synthesizer.py`
- Test: `tests/unit/test_workflow_synthesizer.py`

- [x] Write failing test: `test_phase_status_immutable` and `test_workflow_recommendation_immutable` verify frozen dataclass
- [x] Run test -> FAIL (module not found)
- [x] Implement `PhaseStatus` and `WorkflowRecommendation` frozen dataclasses with importable module
- [x] Run test -> PASS
- [x] Commit: `feat(synthesizer): add dataclass skeleton + module shell`

## Task 2: synthesize() happy path - arch missing (path 1)

**Files:**
- Modify: `skills/_lib/workflow_synthesizer.py`
- Test: `tests/unit/test_workflow_synthesizer.py`

- [x] Write failing test: `test_synthesize_arch_missing_recommends_guide_arch` (no .arch-handoff.json -> suggested_action="guide-arch", confidence="high")
- [x] Run test -> FAIL (synthesize not implemented)
- [x] Implement `synthesize()` with phase status helpers and path-1 branch
- [x] Run test -> PASS
- [x] Commit: `feat(synthesizer): implement path 1 - arch missing -> guide-arch`

## Task 3: Paths 2-5 (arch + plan handoff decision tree)

**Files:**
- Modify: `skills/_lib/workflow_synthesizer.py`
- Test: `tests/unit/test_workflow_synthesizer.py`

- [x] Write 4 failing tests: adr_count<1, arch done plan missing, plan-handoff 0 active, plan-handoff N active
- [x] Run tests -> FAIL (only path 1 implemented)
- [x] Implement paths 2-5 in `_decision_tree()`
- [x] Run tests -> PASS
- [x] Commit: `feat(synthesizer): implement paths 2-5 - handoff decision tree`

## Task 4: Paths 6-9 (worktree + git state)

**Files:**
- Modify: `skills/_lib/workflow_synthesizer.py`
- Test: `tests/unit/test_workflow_synthesizer.py`

- [x] Write 4 failing tests: worktree w/ incomplete tasks, detached worktrees, worktree tasks done, committed change in HEAD
- [x] Run tests -> FAIL
- [x] Implement `_worktree_has_incomplete_tasks()`, `_committed_change_in_head()`, `_list_worktrees()` helpers; wire paths 6-9
- [x] Run tests -> PASS
- [x] Commit: `feat(synthesizer): implement paths 6-9 - worktree + git state`

## Task 5: Paths 10-13 (fallbacks) + unblocked_changes

**Files:**
- Modify: `skills/_lib/workflow_synthesizer.py`
- Test: `tests/unit/test_workflow_synthesizer.py`

- [x] Write 4 failing tests: no roadmap, no openspec/changes, pending proposal, default
- [x] Write 2 failing tests: `test_unblocked_changes_filters_blocker`, `test_unblocked_changes_empty_iteration`
- [x] Run tests -> FAIL
- [x] Implement paths 10-13 + `_unblocked_changes()`
- [x] Run tests -> PASS
- [x] Commit: `feat(synthesizer): implement paths 10-13 + unblocked_changes`

## Task 6: rddf-session integration (active_session + orphaned_sessions)

**Files:**
- Modify: `skills/_lib/workflow_synthesizer.py`
- Test: `tests/unit/test_workflow_synthesizer.py`

- [x] Write 2 failing tests: active session bound when OPENCODE_SESSION_ID set, orphaned sessions listed
- [x] Run tests -> FAIL
- [x] Implement `_active_session()`, `_orphaned_sessions()`
- [x] Run tests -> PASS
- [x] Commit: `feat(synthesizer): rddf-session binding + orphan scan`

## Task 7: Phase status summary (3 phases)

**Files:**
- Modify: `skills/_lib/workflow_synthesizer.py`
- Test: `tests/unit/test_workflow_synthesizer.py`

- [x] Write failing test: `test_phase_status_summary_3_phases` asserts tuple has 3 PhaseStatus entries with correct phase field values
- [x] Run test -> FAIL
- [x] Implement full `_build_phase_status()` with detail strings
- [x] Run test -> PASS
- [x] Commit: `feat(synthesizer): phase status summary for 3 phases`

## Task 8: Never-raises contract + MenuOption + all_options builder

**Files:**
- Modify: `skills/_lib/workflow_synthesizer.py`
- Test: `tests/unit/test_workflow_synthesizer.py`

- [x] Write 2 failing tests: corrupt sessions.json returns fallback recommendation, missing iteration.json returns fallback
- [x] Run tests -> FAIL
- [x] Wrap `synthesize()` body in try/except, return fallback `WorkflowRecommendation` on any exception
- [x] Implement `MenuOption` dataclass with 4 groups (recommended, stages, session, utilities)
- [x] Implement `_build_all_options()` producing full interactive menu
- [x] Run tests -> PASS
- [x] Commit: `feat(synthesizer): never-raises contract + menu options builder`

## Task 9: WorkingTreeIssue + git status scan

**Files:**
- Modify: `skills/_lib/workflow_synthesizer.py`
- Test: `tests/unit/test_workflow_synthesizer.py`

- [x] Write failing test: `test_detect_working_tree_issues_deleted` detects deleted tracked files
- [x] Run test -> FAIL
- [x] Implement `WorkingTreeIssue` dataclass with category/severity/fix_command
- [x] Implement `_detect_working_tree_issues()` scanning git status for deleted, modified, staged, untracked_dirs
- [x] Implement `_deduplicate_issues()` removing duplicate safe_auto_fix entries
- [x] Run tests -> PASS
- [x] Commit: `feat(synthesizer): working tree issue detection + auto-fix suggestions`

## Task 10: state_reader.py shared data layer

**Files:**
- Create: `skills/_lib/state_reader.py`
- Test: (tested indirectly via synthesizer tests)

- [x] Implement 8 read-only functions: `read_arch_handoff`, `read_plan_handoff`, `read_iteration`, `read_sessions`, `read_roadmap_state`, `list_worktrees`, `list_change_dirs`, `read_proposal_approved`
- [x] All functions never-raises: return `None`/`[]` on error
- [x] `read_iteration` uses `iteration.store._read_unlocked()` (not `load()` — avoids writing `.corrupt.*` backup)
- [x] `list_worktrees` parses `git worktree list --porcelain`
- [x] Commit: `feat(state-reader): shared read-only data layer with 8 functions`

## Task 11: Integration into guide_entry.sh with fallback

**Files:**
- Modify: `skills/guide/scripts/guide_entry.sh`
- Test: `tests/integration/test_guide_skill.bats`, `tests/integration/test_guide_entry.bats`

- [x] Write failing test (bats): assert `guide_entry.sh` includes Python synthesizer call block AND retains scan_state fallback
- [x] Run test -> FAIL
- [x] Modify `guide_entry.sh` to call Python synthesizer with fallback to scan_state
- [x] Add `ALL_OPTIONS_JSON` and `WT_ISSUES_JSON` env var exports
- [x] Add 4-tier path resolution (env var → BASH_SOURCE → $0 → walk-up from cwd)
- [x] Run tests -> PASS
- [x] Commit: `feat(guide-entry): integrate workflow synthesizer with fallback to scan-state`

## Task 12: Regression tests + smoke verification

**Files:**
- Test: `tests/unit/test_workflow_synthesizer.py`

- [x] Add parametrized 13-path coverage test: iterate all decision paths via parametrized fixture, assert (suggested_action, confidence) pairs
- [x] Add all_options builder tests: recommended first, stages, session, utilities, cleanup
- [x] Add working tree issue tests: deleted, modified, staged, untracked_dirs, deduplication
- [x] Run `pytest tests/unit/test_workflow_synthesizer.py -v` -> all PASS
- [x] Run `bats tests/integration/test_guide_skill.bats` -> all PASS
- [x] Run `bats tests/integration/test_guide_entry.bats` -> all PASS
- [x] Run `pytest tests/unit/ -q` -> no regressions
- [x] Commit: `test(synthesizer): add parametrized 13-path coverage + regression suite`