## Context

- `npm test` 只跑 bats
- Python 测试需要单独 `pytest tests/`
- 容易遗漏 Python 测试

## Goals / Non-Goals

**Goals:**

- - 
  - package.json 添加 test:python 脚本
  - npm test 改为并行运行 bats + pytest
- Out Scope:
  - 不修改测试本身

## 验收标准
- `npm test` 运行所有 bats + Python 测试

**Non-Goals:**
- 不修改现有功能

## Decisions

- 采用方案 A：直接修复问题
- 不引入 Breaking Change

## Risks / Trade-offs

- **低风险**：改进项，不修改核心逻辑
- **工作量**: 10min
