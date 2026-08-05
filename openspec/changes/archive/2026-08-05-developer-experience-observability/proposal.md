# developer-experience-observability

## Why

本次会话中 hook 在必要注释上多次误报:
- `BASH_SOURCE[0]` direct-execution guard 注释(必要,因为 bash idiom 不直观)
- 100ms→150ms timing threshold 解释注释(必要,防止未来维护者"修复"回 100ms)
- worktree 源 LSP 错误(实际是 worktree 隔离的副作用,非代码 bug)

此外,缺乏工具调用统计和失败重试数据,工作流改进无数据基础(本次 session 复盘只能凭记忆)。

## What Changes

**In Scope**:

- hook 白名单规则:
- bash idiom 注释(`BASH_SOURCE`, `set -u`, `set -e`, `set -o pipefail`)
- "为什么是这个数字/值"的注释(timing threshold, retry counts, magic numbers)
- TODO 引用(issue/ticket 编号)
- `.rddf/state/session_stats.json`:
- 工具调用计数(bash, read, edit, write, task)
- 失败重试次数(子代理超时、配额耗尽)
- 阶段耗时(plan, execute, archive)
- 工作流改进的数据可视化(可选,后续)
- 修改 hook 工具本身
- 实时监控仪表板
- 跨 session 统计聚合(后续迭代)

**Out of Scope**:

- (TBD)

## Capabilities

- (TBD)

## Impact

- (TBD)

## Acceptance

- [ ] (TBD — 验收标准 from improvements 头部未提供)

