# unify-test-entry-points

**优先级**: P1 | **来源**: 改进分析报告 #5
**阶段**: default | **分类**: developer-experience
**类型**: test-only

## 架构依据
（无）

## 范围
- In Scope:
  - package.json 添加 test:python 脚本
  - npm test 改为并行运行 bats + pytest
- Out Scope:
  - 不修改测试本身

## 关键场景
（无）

## 技术约束
（无）

## 验收标准
- `npm test` 运行所有 bats + Python 测试
