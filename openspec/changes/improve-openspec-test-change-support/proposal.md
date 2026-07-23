## Why

- test-only change 被要求提供 specs/ 目录下的 capability spec
- 归档时有警告：`Change must have at least one delta`
- tasks.md 状态与实际执行不同步

## What Changes

- In Scope:
  - roadmap-meta.yaml 添加 `change_type: test-only | doc-only | refactor-only | feature`
  - openspec CLI 跳过 test-only 的 delta 检查
  - execute 阶段自动同步 tasks.md 进度（或移除 tasks.md）
- Out Scope:
  - 不修改现有 change 的 delta 要求
  - 不修改 openspec 核心逻辑

## Capabilities

### New Capabilities
- `improve-openspec-test-change-support`: ## 问题
- test-only change 被要求提供 specs/ 目录下的 capability spec
- 归档时有警告：`Change must have at least one d

## Impact

- **Priority**: P0
- **Effort**: 2-3h
- **Source**: 改进分析报告 #2
