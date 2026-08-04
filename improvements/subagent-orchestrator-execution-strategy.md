# subagent-orchestrator-execution-strategy

**优先级**: P0 | **来源**: 2026-08-04 session 复盘(5 changes ship 时子代理配额耗尽)
**阶段**: default | **分类**: core-impl
**类型**: refactor

## 架构依据

2026-08-04 会话中,5 个并行 `task()` 调度因 `kimi-code/kimi-k2.7-code` 配额耗尽全部失败;用户切换到串行后仍遭遇配额问题,最终 4 个变更由 orchestrator(minimax 模型)直接执行完成。子代理调度的可靠性不可预测,需要明确的执行策略和自动降级路径,避免每次 80+ 分钟的返工。

## 范围

**In Scope**:
- 调度前小规模配额探测(`task()` ping test)
- 决策规则矩阵:根据任务类型(单文件/跨文件/跨 worktree)和配额状态选择执行模式
- 配额耗尽时自动降级到 orchestrator 直接执行
- 子代理失败重试次数上限(默认 1 次),超过后切到 orchestrator

**Out of Scope**:
- 修改 `task()` 工具本身的实现
- 引入新的子代理模型

## 设计

### 决策矩阵

| 任务类型 | 配额充足 | 配额紧张/未知 |
|---------|---------|------------|
| 单文件小改(<50 行) | orchestrator 直接 | orchestrator 直接 |
| 单文件大改(>50 行) | 子代理 | orchestrator 直接 |
| 跨文件 + TDD 多步 | 子代理 | 子代理(降级:orchestrator 直接) |
| 跨 worktree 并行 N 个 | 子代理并行 | 串行子代理 → 失败则 orchestrator |
| 计划生成(无副作用) | 子代理并行 | 串行子代理 |

### 配额探测

```python
def probe_subagent_quota():
    try:
        result = task(subagent_type="general", prompt="ping", timeout=30)
        return result.status != "quota_exceeded"
    except QuotaError:
        return False
```

### 降级路径

当 `task()` 返回 `quota_exceeded` 或类似错误:
1. 重试 1 次(同一任务)
2. 重试失败 → 切到 orchestrator 直接执行(本会话已实践)
3. 记录到 `.rddf/state/quota_failures.json` 用于工作流改进

## 影响

- **正向**: 子代理配额不稳定时不再浪费 80+ 分钟重试
- **正向**: orchestrator 直接执行更快(无子代理上下文切换)
- **风险**: 决策规则增加复杂度,需文档化在 SKILL.md
- **兼容性**: 不破坏现有 `task()` 调用,仅在其上添加决策层

## 验收

- 配额充足场景:子代理执行时间 ≤ 直接执行的 1.5x(超时则切到 orchestrator)
- 配额耗尽场景:重试 1 次后自动降级到 orchestrator,无用户介入
- 决策矩阵文档化在 `skills/rdd-workflow-writing-plans/SKILL.md` 或新建 `skills/subagent-strategy/`
- 5 次连续测试中,决策正确率 > 90%
- `.rddf/state/quota_failures.json` 在降级时自动记录