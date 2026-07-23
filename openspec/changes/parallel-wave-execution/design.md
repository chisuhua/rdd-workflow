## Context

- Wave 2 的 4 个 changes 可以并行执行
- 实际串行执行，每次都要人工选择

## Goals / Non-Goals

**Goals:**

- - 
  - guide-ship 添加 --parallel 模式
  - 自动并行执行同一 wave 的所有独立 changes
  - 依赖检测确保正确顺序
- Out Scope:
  - 不修改 deps 分析逻辑

## 验收标准
- `guide-ship --wave 2 --parallel` 自动并行执行

**Non-Goals:**
- 不修改现有功能

## Decisions

- 采用方案 A：直接修复问题
- 不引入 Breaking Change

## Risks / Trade-offs

- **低风险**：改进项，不修改核心逻辑
- **工作量**: 4-6h
