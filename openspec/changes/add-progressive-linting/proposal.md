## Why

项目有 7,382 LOC Python 后端，48 处 `Any` 用法，但 CI 无 lint 和类型检查。重构时类型回归无保护。Round A/B/C 提取了 ~1,500 行 bash，下一步若提取 Python，缺类型检查会放大回归风险。v2.1 渐进式引入。

## What Changes

- CI 加入 `ruff check skills/_lib/`（快，1 分钟接 CI）
- CI 加入 `mypy --strict skills/_lib/core/`（仅 6 个内核文件）
- `requirements.txt` 加入 `ruff` + `mypy`
- 修复 ruff 发现的明显问题（未用 import、显然 bug）
- 不对 loop/ 子目录强制类型（动态性高，性价比低）

## Capabilities

### New Capabilities
- `progressive-linting`: CI 中的渐进式 Python 代码质量检查

### Modified Capabilities
- （无）

## Impact

- **Affected code**: `.github/workflows/test.yml`、`requirements.txt`、可能修复少量源码
- **Scope**: CI 配置 + 依赖 + 少量源码修复
- **Risk**: 低——新增步骤不阻塞 CI（配置为 warning 级别）
- **Effort**: 半天