# fix-ship-plan-untracked-gate — Implementation Tasks

## Implementation Tasks

- [ ] Task 1: `check_artifacts_committed` 重构,只检查 tracked files 的 `M`/`D` 状态,忽略 `??`(untracked)
- [ ] Task 2: 新增 unit test 覆盖 3 个场景:
- [ ] Task 3: `--strict-untracked` flag 在 `guide-plan` / `guide-ship` 入口作为 opt-in
- [ ] Task 4: 删除历史 workaround commit `13ad3ba chore(specs): add openspec validate specs/ for 2 remaining active changes` (合并到新的归档操作内)
- [ ] Task 5: `guide-ship/SKILL.md` COMMIT GATE 段更新解释新行为
- [ ] Task 6: Run `bash tests/scripts/report_regression.sh` to confirm no new failures