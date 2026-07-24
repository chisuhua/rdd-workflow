## Why

- 用户预期：`create_session(kind="guide-plan")`
- 实际要求：`create_session(kind="stage_plan")`
- 错误：`Invalid kind: guide-plan. Must be one of ('stage_arch', 'stage_plan', 'stage_ship')`

## What Changes

- In Scope:
  - 方案 A：统一为 `guide-arch` / `guide-plan` / `guide-ship`（与 skill 名称一致）
  - 方案 B：在 _VALID_KINDS 同时接受两种命名
  - 更新所有现有代码和测试
- Out Scope:
  - 不修改 ADR 或文档中的术语定义

## Capabilities

### New Capabilities
- `unify-session-kind-naming`: ## 问题
- 用户预期：`create_session(kind="guide-plan")`
- 实际要求：`create_session(kind="stage_plan")`
- 错误：`In

## Impact

- **Priority**: P0
- **Effort**: 1h
- **Source**: 改进分析报告 #3
