# improve-execution-mode-per-change

## Why

`skills/guide-ship/scripts/ship_plan.sh` 的 `detect_execution_mode` 当前逻辑只看两个条件:

```bash
if [ "$existing_wt" -gt 0 ] || [ "$total_changes" -gt 1 ]; then
    echo "worktree"
fi
```

后果:

- 3 个 docs-only P1 changes(sync-package-skills-to-disk, sync-agents-md-five-stage, rdd-doctor-docs-consistency)每个都 ≤ 5 个文件修改,但都被强制走 worktree 模式(因为 `total_changes > 1`)。
- 实际 sync-agents-md-five-stage 只改 AGENTS.md 1 个文件,worktree 模式带来不必要的 `git worktree add/remove` 开销。
- ship cycle 总耗时增加 ~30%(worktree 创建 + cleanup)。

期望行为: `detect_execution_mode` 应按单个 change 的复杂度(file count, task count, risk keywords)决策,而非只看总 change 数。

## What Changes

**In Scope**:

- `detect_execution_mode` 接受 `change_name` 参数(已有),按单个 change 评估。
- 新增 per-change 评估维度:
- file_count(`git diff main --stat | wc -l`)
- task_count(从 `proposal.md` 或 tasks.md)
- risk_keywords(grep "refactor|migration|breaking")
- 综合分数 > 阈值 → worktree;否则 lightweight。

### 关键场景

- GIVEN `sync-agents-md-five-stage` 只改 AGENTS.md 1 个文件
  WHEN `detect_execution_mode` 调用
  THEN 返回 `lightweight`(直接 master 分支执行,跳过 worktree)

- GIVEN `rdd-doctor-docs-consistency` 修改 5+ 文件 + 新增模块
  WHEN `detect_execution_mode` 调用
  THEN 返回 `worktree`(按文件数 / 风险评分)

**Out of Scope**:

- 完全替换现有 detect_execution_mode(保留 fallback 到 current behavior)。
- 改变 `.plan-handoff.json::execution_mode_decisions` schema。

## Capabilities

- MUST: 保留 `existing_wt > 0` 的 fallback(有活跃 worktree 仍然走 worktree 避免冲突)
- MUST: `execution_mode_decisions` 在 `.plan-handoff.json` 仍然正确写
- SHOULD: 在 `guide-ship` Phase 1 显示 per-change 的 mode decision 解释

## Impact

- MUST NOT: 改变 ADR-0024 的 deps-driven 决策语义

## Acceptance

- [ ] `detect_execution_mode` 接受 per-change file count 维度
- [ ] 阈值可配置(默认: file_count ≤ 2 → lightweight)
- [ ] 回归测试:`sync-agents-md-five-stage` 类(1 file)→ lightweight
- [ ] 回归测试:`rdd-doctor-docs-consistency` 类(>5 files)→ worktree
- [ ] `existing_wt > 0` 的 fallback 行为不变
- [ ] `guide-ship/SKILL.md` Phase 1 表格更新显示新逻辑

