## Context

- 用户问 "What did we do so far?" 时需要手动总结
- 没有自动的进度追踪视图

## Goals / Non-Goals

**Goals:**

- - 
  - rddf-session progress 子命令
  - 显示 wave 执行状态和归档情况
  - 支持按 session 过滤
- Out Scope:
  - 不修改 guide-ship 执行逻辑

## 验收标准
- `rddf-session progress` 显示清晰的进度视图

**Non-Goals:**
- 不修改现有功能

## Decisions

- 采用方案 A：直接修复问题
- 不引入 Breaking Change

## Risks / Trade-offs

- **低风险**：改进项，不修改核心逻辑
- **工作量**: 2-3h
