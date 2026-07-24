## Context

- 目录命名 `skills/rddf-session/`（连字符）vs 导入 `skills.rddf_session`（下划线）
- conftest.py 的 dash-bridge 对 LSP 不生效
- 每个 Python 测试文件都被 LSP 标红（实际运行正常）

## Goals / Non-Goals

**Goals:**

- - 
  - pyrightconfig.json 添加 executionEnvironments 和 extraPaths
  - 或在 skills/ 各子目录添加 py.typed + __init__.py
- Out Scope:
  - 不修改目录命名（Breaking change）
  - 不修改 conftest.py（已生效）

## 验收标准
- LSP 不再报告 `Import could not be resolved` 错误
- 实际运行测试仍通过

**Non-Goals:**
- 不修改现有功能

## Decisions

- 采用方案 A：直接修复问题
- 不引入 Breaking Change

## Risks / Trade-offs

- **低风险**：改进项，不修改核心逻辑
- **工作量**: 30min
