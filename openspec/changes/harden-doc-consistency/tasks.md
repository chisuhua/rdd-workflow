# Tasks: harden-doc-consistency

## 1. Setup

- [ ] 1.1 Read proposal.md, design.md and confirm scope
- [ ] 1.2 Capture baseline test results: `bats tests/integration/test_doc_phase_consistency.bats` (expect 3/5)
- [ ] 1.3 Identify orphan helpers: `grep -E "safe_python_json|safe_python_yaml|read_suggestions|write_suggestions|is_change_committed" skills/*.md tests/`

## 2. Code Fixes (run-time behavior)

- [ ] 2.1 Fix `find_default_branch` in `skills/_lib/worktree.sh:43-51`: use `git config --get init.defaultBranch` or probe main/master/develop branches in main repo (not worktree)
- [ ] 2.2 Delete orphan `is_change_committed` from `skills/_lib/worktree.sh:31-37` (zero callers verified)
- [ ] 2.3 Delete orphan helpers from `skills/_lib/state.sh`: `safe_python_json`, `safe_python_yaml`, `read_suggestions`, `write_suggestions` (zero callers verified)
- [ ] 2.4 Remove inline `wt_path_for_branch_inline` from `skills/status.md:158-162`; use `_lib/worktree.sh::wt_path_for_branch` (after sourcing)
- [ ] 2.5 Remove inline `wt_path_for_branch_inline` from `skills/execute.md:305-309`; use `_lib/worktree.sh::wt_path_for_branch`
- [ ] 2.6 Source `_lib/worktree.sh` at the top of `skills/status.md` (currently not sourced)

## 3. Skill Documentation Fixes

- [ ] 3.1 Fix `skills/status.md` L324: hardcoded `main` → `${DEFAULT_BRANCH:-master}` (✅ done)
- [ ] 3.2 Fix `skills/status.md` L464: hardcoded `main` → default branch description (✅ done)
- [ ] 3.3 Fix `skills/status.md` L466: "从 main TUI session" → "从主仓库 TUI session" (✅ done)
- [ ] 3.4 Fix `skills/status.md` L68-70: `/path/to/CppHDL` → `/path/to/PROJECT_ROOT` (✅ done)
- [ ] 3.5 Fix `skills/guide-spec.md` L148, L262: `当前分支: main` → `当前分支: master` (✅ done)
- [ ] 3.6 Fix `skills/guide-ship.md` L188: error message uses `${DEFAULT_BRANCH:-master}` (✅ done)
- [ ] 3.7 Fix `skills/execute.md` L169: `避免对 main 分支` → `避免对 default branch` (✅ done)
- [ ] 3.8 Fix `skills/propose.md` L193: `ADR-NNN:` → `ADR-NNNN:` (4-digit) (✅ done)

## 4. Top-level Documentation Fixes

- [ ] 4.1 Fix `USAGE.md` L48: `plan → execute → status → archive` → `plan → execute → archive → cleanup` (✅ done)
- [ ] 4.2 Fix `USAGE.md` L75, L654: ship-side phase count `4 阶段` → `5 阶段 + ship-done 退出` (✅ done)
- [ ] 4.3 Expand `USAGE.md` state-file table to include `.zcf/.handoff.json`, `.zcf/.roadmap-state.json`, `.zcf/.deps-*.json`, `.zcf/index.md` (✅ done)
- [ ] 4.4 Fix `USAGE.md` "Execute 只写 tasks.md" → qualified statement (roadmap mode adds `.zcf/.roadmap-state.json`) (✅ done)
- [ ] 4.5 Update `USAGE.md` test infrastructure tree to match actual files (✅ done)

## 5. ADR & INSTALL.md Fixes

- [ ] 5.1 Rewrite `docs/adr/ADR-0001-propose-plan-execute-state-machine.md` Decision section to use actual current architecture (✅ done)
- [ ] 5.2 Update `docs/adr/ADR-0001` title from "propose → plan → execute → status → archive" to "spec 端 / ship 端状态机分离" (✅ done)
- [ ] 5.3 Update `docs/adr/README.md` ADR-0001 title in index table (✅ done)
- [ ] 5.4 Fix `skills/INSTALL.md` L3: skill list 6 → 10, add `prometheus-planning` (✅ done)
- [ ] 5.5 Bump `skills/INSTALL.md` version `1.0` → `1.1.0` (3 sites: L5, L114, L203) (✅ done)
- [ ] 5.6 Update `skills/INSTALL.md` heredoc package.json: add `prometheus-planning` to skills array (✅ done)

## 6. Format & Test Doc Fixes

- [ ] 6.1 Fix `docs/proposal-suggestions-format.md` L7: consumer list 4 → 5 (add `deps`) (✅ done)
- [ ] 6.2 Add row to `docs/proposal-suggestions-format.md` consumer table for `deps.md` (✅ done)
- [ ] 6.3 Update `tests/README.md` Layout tree to include `smoke.bats` and `test_helper.bash` at root (✅ done)

## 7. Verification

- [ ] 7.1 Run `bats tests/integration/test_doc_phase_consistency.bats` (expect 5/5)
- [ ] 7.2 Run `bats tests/integration/test_status_skill.bats` (expect 4/4)
- [ ] 7.3 Run `bats tests/integration/test_skill_metadata_consistency.bats` (expect 4/4)
- [ ] 7.4 Run `bats tests/integration/test_install_skill.bats` (expect 4/4)
- [ ] 7.5 Run `bats tests/integration/test_adr_directory.bats` (expect 13/14; test 13 passes after commit)
- [ ] 7.6 Add `test_find_default_branch_in_worktree.bats` to verify bug fix
- [ ] 7.7 Run `openspec validate harden-doc-consistency --strict` (expect "is valid")
- [ ] 7.8 Verify no regression: `bats tests/integration/test_prometheus_planning.bats` (17/17)

## 8. Archive

- [ ] 8.1 Commit all 11 modified files + new change artifacts to a feature branch
- [ ] 8.2 Run `archive_change harden-doc-consistency` (per prior pattern)
- [ ] 8.3 Verify `openspec/changes/archive/2026-06-09-harden-doc-consistency/` created

> Tasks marked (✅ done) were completed in the pre-change audit phase.
> Tasks 2.1-2.6 and 7.6 are the NEW execution work for this change.

## Notes (pre-existing issues to address in v1.2)

- [ ] 9.0 **Ghost change cleanup** (deferred to v1.2): Master currently tracks
      `openspec/changes/{add-skill-bats-tests,implement-deps-subagent-analysis,init-adr-directory}/`
      AND has untracked copies at `openspec/changes/archive/<date>-<name>/`. The prior
      `archive_change` calls created archive copies but did NOT remove the originals from
      master's tracked tree. This is a pre-existing bug, NOT caused by harden-doc-consistency.
      Fix in v1.2: `git rm -r openspec/changes/{add-skill-bats-tests,implement-deps-subagent-analysis,init-adr-directory}/`
      then commit.
