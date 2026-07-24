## Context

- split-rddf-god-class 成功拆分了 507 行的 RddfSessionCoordinator
- 其他大文件可能也有类似问题

## Goals / Non-Goals

**Goals:**

- - 
  - 添加代码质量门控：单文件超过 300 行触发 warning
  - 或在 arch-quality-gate 中添加检查
- Out Scope:
  - 不修改现有代码

## 验收标准
- 超过 300 行的文件在 CI 中触发警告

**Non-Goals:**
- 不修改现有功能

## Decisions

- 采用方案 A：直接修复问题
- 不引入 Breaking Change

## Risks / Trade-offs

- **低风险**：改进项，不修改核心逻辑
- **工作量**: 1h
