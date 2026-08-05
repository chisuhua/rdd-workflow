# subagent-orchestrator-execution-strategy

## Why

2026-08-04 会话中,5 个并行 `task()` 调度因 `kimi-code/kimi-k2.7-code` 配额耗尽全部失败;用户切换到串行后仍遭遇配额问题,最终 4 个变更由 orchestrator(minimax 模型)直接执行完成。子代理调度的可靠性不可预测,需要明确的执行策略和自动降级路径,避免每次 80+ 分钟的返工。

## What Changes

**In Scope**:

- 调度前小规模配额探测(`task()` ping test)
- 决策规则矩阵:根据任务类型(单文件/跨文件/跨 worktree)和配额状态选择执行模式
- 配额耗尽时自动降级到 orchestrator 直接执行
- 子代理失败重试次数上限(默认 1 次),超过后切到 orchestrator
- 修改 `task()` 工具本身的实现
- 引入新的子代理模型

**Out of Scope**:

- (TBD)

## Capabilities

- (TBD)

## Impact

- (TBD)

## Acceptance

- [ ] (TBD — 验收标准 from improvements 头部未提供)

