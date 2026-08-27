# improve-execution-mode-per-change — Implementation Tasks

## Implementation Tasks

- [x] Task 1: `detect_execution_mode` 接受 `change_name` 参数 (已有, 按单个 change 评估)
- [x] Task 2: 新增 per-change 评估维度 (file_count, task_count, risk_keywords)
- [x] Task 3: 综合分数 > 阈值 → worktree; 否则 lightweight (file_count>5 OR risk>0 OR task_count>5)
- [x] Task 4: 保留 `existing_wt > 0` fallback (有活跃 worktree 仍然 worktree)
- [x] Task 5: 新增 bats 测试覆盖所有决策分支 (6 tests, all pass)
- [x] Task 6: execution_mode_decisions 在 .plan-handoff.json 仍然正确写 (无 schema 变化)
