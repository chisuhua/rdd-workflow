## Context

- docs/adr/README.md 需要手动同步新增 ADR
- test_adr_index.bats 硬编码范围 0001-0020

## Goals / Non-Goals

**Goals:**

- - 
  - scripts/sync_adr_index.py 自动生成 README.md 表格
  - CI hook 或 pre-commit hook 自动调用
- Out Scope:
  - 不修改 ADR 模板或格式

## 验收标准
- 新增 ADR 后 README.md 自动更新

**Non-Goals:**
- 不修改现有功能

## Decisions

- 采用方案 A：直接修复问题
- 不引入 Breaking Change

## Risks / Trade-offs

- **低风险**：改进项，不修改核心逻辑
- **工作量**: 1-2h
