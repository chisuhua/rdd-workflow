# Tasks: Submodule-Aware Project Root Resolution

**Change**: submodule-aware-project-root
**ADR**: ADR-0033
**Phase**: v2.2 | **Category**: core-impl | **Priority**: P0
**Date**: 2026-08-25

> **TDD Discipline (v2.0+)**: Each task follows 5-step structure:
> 1. Write failing test
> 2. Verify test fails (red)
> 3. Implement minimal fix
> 4. Verify test passes (green)
> 5. Commit

## Task 1: `main_repo_root()` submodule detection (P0)

- [ ] **1.1** Write failing test: in `tests/integration/test_submodule_root_resolution.bats`, create bats fixture (git repo + submodule), source `_lib/worktree.sh`, assert `main_repo_root` returns submodule own root
- [ ] **1.2** Verify test fails (current `main_repo_root` returns superproject's `.git/modules/...` parent)
- [ ] **1.3** Implement: Add submodule detection at `_lib/worktree.sh:67` entry using `--show-superproject-working-tree`
- [ ] **1.4** Verify test passes (submodule root returned)
- [ ] **1.5** Verify P0-8 regression: `test_execute_main_root.bats` still all-green (worktree contract preserved)
- [ ] **1.6** Commit: `fix(worktree): submodule-aware main_repo_root`

## Task 2: `resolve_project_root()` submodule detection (P0)

- [ ] **2.1** Write failing test: in `tests/unit/test_cli_routing.py`, mock subprocess to simulate submodule (`--show-superproject-working-tree` returns superproject root), assert `resolve_project_root()` returns submodule own root
- [ ] **2.2** Verify test fails (current returns `.git/modules/...` parent)
- [ ] **2.3** Implement: Add submodule detection in `_lib/cli/__main__.py:39` before worktree branch
- [ ] **2.4** Verify test passes
- [ ] **2.5** Commit: `fix(cli): submodule-aware resolve_project_root`

## Task 3: `_is_in_worktree()` submodule short-circuit (P0)

- [ ] **3.1** Write failing test: in `tests/unit/test_cli_routing.py`, mock submodule condition, assert `_is_in_worktree()` returns False (not True)
- [ ] **3.2** Verify test fails (current comparison logic returns True because `--git-common-dir == --git-dir` in submodule)
- [ ] **3.3** Implement: Submodule detection at `_lib/cli/__main__.py:82` entry, return False if submodule
- [ ] **3.4** Verify test passes
- [ ] **3.5** Commit: included in Task 2 commit (same file)

## Task 4: `validate_cmd.py` `--git-dir` → `--show-toplevel` (P1)

- [ ] **4.1** Write failing test: in `tests/unit/test_validate_cmd.py`, mock `--git-dir` failing in submodule context, assert validate passes
- [ ] **4.2** Verify test fails
- [ ] **4.3** Implement: Change `_lib/cli/validate_cmd.py:63` from `--git-dir` to `--show-toplevel`
- [ ] **4.4** Verify test passes
- [ ] **4.5** Commit: `fix(cli): validate_cmd use --show-toplevel for git repo check`

## Task 5: `select_worktree.sh` containment check (P1)

- [ ] **5.1** Write failing test: in `tests/integration/test_select_worktree_submodule.bats`, set up RDDF_EXECUTION_ROOT=submodule_root, assert containment check produces clear error
- [ ] **5.2** Verify test fails (current `--git-common-dir` containment returns confusing result)
- [ ] **5.3** Implement: Update `skills/execute/scripts/select_worktree.sh:52,54` to use `--show-toplevel` for containment
- [ ] **5.4** Verify test passes + error message is clear
- [ ] **5.5** Commit: `fix(execute): select_worktree containment uses --show-toplevel`

## Task 6: 5 处 `--git-dir` 用法加注释 (P2, docs only)

- [ ] **6.1** Add comment to `install.sh:349` documenting submodule behavior of `--git-dir`
- [ ] **6.2** Add comment to `tools/archive_on_main.sh:90`
- [ ] **6.3** Add comment to `skills/roadmap/scripts/roadmap_migrate.sh:176`
- [ ] **6.4** Add comment to `skills/spoke-system-prompt-injection/scripts/deploy.sh:69`
- [ ] **6.5** Add comment to `_lib/cli/__main__.py:98`
- [ ] **6.6** Commit: `docs(cli): document --git-dir submodule behavior in 5 callers`

## Task 7: 文档更新 (P2)

- [ ] **7.1** Update `AGENTS.md` "关键约定" 章节: add submodule entry under `main_repo_root()` contract
- [ ] **7.2** Update `skills/guide/SKILL.md` or `USAGE.md`: 1 段说明 submodule 使用
- [ ] **7.3** Update `_lib/worktree.sh::main_repo_root()` docstring: submodule vs worktree vs main repo 行为矩阵
- [ ] **7.4** Commit: `docs(workflow): document submodule support in main_repo_root + guide`

## Task 8: 全量回归验证 (MANDATORY before archive)

- [ ] **8.1** Run `./test.sh --quick` → 全绿
- [ ] **8.2** Run `./test.sh --full --regression` → 无新增失败(baseline 已知失败可放行)
- [ ] **8.3** Manual smoke: 在 PTX-EMU submodule 内运行 `rddf dashboard`,不再输出 `not a rdd-workflow project`
- [ ] **8.4** Commit verification report (if any)

## Task 9: Archive change (Phase 4 of guide-ship)

- [ ] **9.1** All tasks above completed + committed
- [ ] **9.2** `./test.sh --full --regression` 全绿
- [ ] **9.3** `guide-ship` archive change 流程触发 `archive_change_for_mode`
- [ ] **9.4** Verify `openspec/changes/archive/<date>-submodule-aware-project-root/` 创建
- [ ] **9.5** Verify `iteration.json` 中 `submodule-aware-project-root` status=`archived`
- [ ] **9.6** Verify 后续 commit `archive(submodule-aware-project-root): archive completed`

## Out-of-Scope Tasks (tracked separately)

- Fix `openspec validate` schema check (this change's `.openspec.yaml` triggers "Invalid metadata" — unrelated to submodule bug, file as separate P2 issue)
- Add `specs/<capability>/spec.md` with delta headers for openspec CLI strict compliance
- Worktree-in-submodule (submodule of a worktree) edge case