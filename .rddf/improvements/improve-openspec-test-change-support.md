# improve-openspec-test-change-support

**优先级**: P0 | **来源**: 改进分析报告 #2
**阶段**: default | **分类**: developer-experience
**类型**: test-only

## 架构依据
（无）

## 范围
- In Scope:
  - roadmap-meta.yaml 添加 `change_type: test-only | doc-only | refactor-only | feature`
  - openspec CLI 跳过 test-only 的 delta 检查
  - execute 阶段自动同步 tasks.md 进度（或移除 tasks.md）
- Out Scope:
  - 不修改现有 change 的 delta 要求
  - 不修改 openspec 核心逻辑

## 关键场景
（无）

## 技术约束
（无）

## 验收标准
- test-only change 归档无警告
- tasks.md 自动同步或移除
