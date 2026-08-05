# subagent-orchestrator-execution-strategy — Design

## Context

2026-08-04 会话中,5 个并行 `task()` 调度因 `kimi-code/kimi-k2.7-code` 配额耗尽全部失败;用户切换到串行后仍遭遇配额问题,最终 4 个变更由 orchestrator(minimax 模型)直接执行完成。子代理调度的可靠性不可预测,需要明确的执行策略和自动降级路径,避免每次 80+ 分钟的返工。

## Goals / Non-Goals

**Goals:**

- 调度前小规模配额探测(`task()` ping test)
- 决策规则矩阵:根据任务类型(单文件/跨文件/跨 worktree)和配额状态选择执行模式
- 配额耗尽时自动降级到 orchestrator 直接执行
- 子代理失败重试次数上限(默认 1 次),超过后切到 orchestrator

**Non-Goals:**

- 修改 `task()` 工具本身的实现
- 引入新的子代理模型

## Decisions

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

## Risks / Trade-offs

- **正向**: 子代理配额不稳定时不再浪费 80+ 分钟重试
- **正向**: orchestrator 直接执行更快(无子代理上下文切换)
- **风险**: 决策规则增加复杂度,需文档化在 SKILL.md
- **兼容性**: 不破坏现有 `task()` 调用,仅在其上添加决策层

## Migration Plan

1. 本提案在主仓库实施,通过 guide-plan + guide-ship 工作流
2. 执行完成后 openspec archive 归档到 openspec/changes/archive/YYYY-MM-DD-subagent-orchestrator-execution-strategy/
3. 不涉及运行时数据迁移(纯 workflow 增强)

## Open Questions

无 — 提案中所有关键场景(S1-S6 等)已定义清晰。
