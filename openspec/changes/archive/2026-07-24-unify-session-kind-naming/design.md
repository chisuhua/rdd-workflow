## Context

- 用户预期：`create_session(kind="guide-plan")`
- 实际要求：`create_session(kind="stage_plan")`
- 错误：`Invalid kind: guide-plan. Must be one of ('stage_arch', 'stage_plan', 'stage_ship')`

## Goals / Non-Goals

**Goals:**

- - 
  - 方案 A：统一为 `guide-arch` / `guide-plan` / `guide-ship`（与 skill 名称一致）
  - 方案 B：在 _VALID_KINDS 同时接受两种命名
  - 更新所有现有代码和测试
- Out Scope:
  - 不修改 ADR 或文档中的术语定义

## 验收标准
- 用户可用直觉命名的 kind 参数
- 所有测试通过

**Non-Goals:**
- 不修改现有功能

## Decisions

- 采用方案 A：直接修复问题
- 不引入 Breaking Change

## Risks / Trade-offs

- **低风险**：改进项，不修改核心逻辑
- **工作量**: 1h
