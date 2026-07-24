## Context

- test-only change 被要求提供 specs/ 目录下的 capability spec
- 归档时有警告：`Change must have at least one delta`
- tasks.md 状态与实际执行不同步

## Goals / Non-Goals

**Goals:**

- - 
  - roadmap-meta.yaml 添加 `change_type: test-only | doc-only | refactor-only | feature`
  - openspec CLI 跳过 test-only 的 delta 检查
  - execute 阶段自动同步 tasks.md 进度（或移除 tasks.md）
- Out Scope:
  - 不修改现有 change 的 delta 要求
  - 不修改 openspec 核心逻辑

## 验收标准
- test-only change 归档无警告
- tasks.md 自动同步或移除

**Non-Goals:**
- 不修改现有功能

## Decisions

- 采用方案 A：直接修复问题
- 不引入 Breaking Change

## Risks / Trade-offs

- **低风险**：改进项，不修改核心逻辑
- **工作量**: 2-3h
