# improve-execution-mode-per-change — Design

## Context

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

## Goals / Non-Goals

**Goals:**
- `detect_execution_mode` 接受 `change_name` 参数(已有),按单个 change 评估。
- 新增 per-change 评估维度:
- file_count(`git diff main --stat | wc -l`)
- task_count(从 `proposal.md` 或 tasks.md)
- risk_keywords(grep "refactor|migration|breaking")

**Non-Goals:**
- 完全替换现有 detect_execution_mode(保留 fallback 到 current behavior)。
- 改变 `.plan-handoff.json::execution_mode_decisions` schema。

## Decisions

### 1. MUST: 保留 `existing_wt > 0` 的 fallback(有活跃 worktree 仍然走 worktree 避免冲突)

Implementation MUST satisfy this constraint.

### 2. MUST: `execution_mode_decisions` 在 `.plan-handoff.json` 仍然正确写

Implementation MUST satisfy this constraint.


## Risks / Trade-offs

- No identified risks beyond standard implementation discipline.

- **SHOULD**: SHOULD: 在 `guide-ship` Phase 1 显示 per-change 的 mode decision 解释