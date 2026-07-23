# fix-lsp-dash-bridge

**优先级**: P0 | **来源**: 改进分析报告 #1
**阶段**: default | **分类**: developer-experience
**类型**: test-only

## 架构依据
（无）

## 范围
- In Scope:
  - pyrightconfig.json 添加 executionEnvironments 和 extraPaths
  - 或在 skills/ 各子目录添加 py.typed + __init__.py
- Out Scope:
  - 不修改目录命名（Breaking change）
  - 不修改 conftest.py（已生效）

## 关键场景
（无）

## 技术约束
（无）

## 验收标准
- LSP 不再报告 `Import could not be resolved` 错误
- 实际运行测试仍通过
