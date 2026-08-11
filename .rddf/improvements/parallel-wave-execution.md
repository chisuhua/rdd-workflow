# parallel-wave-execution

**优先级**: P1 | **来源**: 改进分析报告 #6
**阶段**: default | **分类**: performance
**类型**: feature

## 架构依据
（无）

## 范围
- In Scope:
  - guide-ship 添加 --parallel 模式
  - 自动并行执行同一 wave 的所有独立 changes
  - 依赖检测确保正确顺序
- Out Scope:
  - 不修改 deps 分析逻辑

## 关键场景
（无）

## 技术约束
（无）

## 验收标准
- `guide-ship --wave 2 --parallel` 自动并行执行
