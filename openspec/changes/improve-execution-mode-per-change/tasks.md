# improve-execution-mode-per-change — Implementation Tasks

## Implementation Tasks

- [ ] Task 1: `detect_execution_mode` 接受 per-change file count 维度
- [ ] Task 2: 阈值可配置(默认: file_count ≤ 2 → lightweight)
- [ ] Task 3: 回归测试:`sync-agents-md-five-stage` 类(1 file)→ lightweight
- [ ] Task 4: 回归测试:`rdd-doctor-docs-consistency` 类(>5 files)→ worktree
- [ ] Task 5: `existing_wt > 0` 的 fallback 行为不变
- [ ] Task 6: `guide-ship/SKILL.md` Phase 1 表格更新显示新逻辑
- [ ] Task 7: Run `bash tests/scripts/report_regression.sh` to confirm no new failures