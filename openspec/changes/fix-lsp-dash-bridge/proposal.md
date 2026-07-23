## Why

- 目录命名 `skills/rddf-session/`（连字符）vs 导入 `skills.rddf_session`（下划线）
- conftest.py 的 dash-bridge 对 LSP 不生效
- 每个 Python 测试文件都被 LSP 标红（实际运行正常）

## What Changes

- In Scope:
  - pyrightconfig.json 添加 executionEnvironments 和 extraPaths
  - 或在 skills/ 各子目录添加 py.typed + __init__.py
- Out Scope:
  - 不修改目录命名（Breaking change）
  - 不修改 conftest.py（已生效）

## Capabilities

### New Capabilities
- `fix-lsp-dash-bridge`: ## 问题
- 目录命名 `skills/rddf-session/`（连字符）vs 导入 `skills.rddf_session`（下划线）
- conftest.py 的 dash-bridge

## Impact

- **Priority**: P0
- **Effort**: 30min
- **Source**: 改进分析报告 #1
