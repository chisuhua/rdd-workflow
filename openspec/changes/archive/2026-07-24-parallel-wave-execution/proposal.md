## Why

- Wave 2 的 4 个 changes 可以并行执行
- 实际串行执行，每次都要人工选择

## What Changes

- In Scope:
  - guide-ship 添加 --parallel 模式
  - 自动并行执行同一 wave 的所有独立 changes
  - 依赖检测确保正确顺序
- Out Scope:
  - 不修改 deps 分析逻辑

## Capabilities

### New Capabilities
- `parallel-wave-execution`: ## 问题
- Wave 2 的 4 个 changes 可以并行执行
- 实际串行执行，每次都要人工选择

## 范围
- In Scope:
  - guide-ship 添加 --paralle

## Impact

- **Priority**: P1
- **Effort**: 4-6h
- **Source**: 改进分析报告 #6
