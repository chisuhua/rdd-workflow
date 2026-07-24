## Why

- docs/adr/README.md 需要手动同步新增 ADR
- test_adr_index.bats 硬编码范围 0001-0020

## What Changes

- In Scope:
  - scripts/sync_adr_index.py 自动生成 README.md 表格
  - CI hook 或 pre-commit hook 自动调用
- Out Scope:
  - 不修改 ADR 模板或格式

## Capabilities

### New Capabilities
- `auto-sync-adr-index`: ## 问题
- docs/adr/README.md 需要手动同步新增 ADR
- test_adr_index.bats 硬编码范围 0001-0020

## 范围
- In Scope:
  -

## Impact

- **Priority**: P2
- **Effort**: 1-2h
- **Source**: 改进分析报告 #7
