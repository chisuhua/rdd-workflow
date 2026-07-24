## Why

- `npm test` 只跑 bats
- Python 测试需要单独 `pytest tests/`
- 容易遗漏 Python 测试

## What Changes

- In Scope:
  - package.json 添加 test:python 脚本
  - npm test 改为并行运行 bats + pytest
- Out Scope:
  - 不修改测试本身

## Capabilities

### New Capabilities
- `unify-test-entry-points`: ## 问题
- `npm test` 只跑 bats
- Python 测试需要单独 `pytest tests/`
- 容易遗漏 Python 测试

## 范围
- In Scope:
  - p

## Impact

- **Priority**: P1
- **Effort**: 10min
- **Source**: 改进分析报告 #5
