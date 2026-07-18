## Why

`iteration.py` 739 行是项目中最大的单 Python 文件，混合 schema 定义 + CRUD + CLI 渲染 + merge 逻辑 4 类职责。每次新增 hook 需通读全文，PR review 成本高。v2.1 中与 iteration schema bump 同步拆分。

## What Changes

- 创建 `skills/_lib/iteration/` 子目录
- `iteration/schema.py` — schema 定义 + validation
- `iteration/store.py` — CRUD + atomic write + merge
- `iteration/render.py` — CLI/status 渲染
- `iteration/__init__.py` — 兼容 re-export（保持现有 import 路径）
- 迁移现有 4-5 个 iteration 相关 unit 测试
- 不修改 iteration.json schema，不改变公有 API 签名

## Capabilities

### New Capabilities
- （无——纯重构，不引入新功能）

### Modified Capabilities
- （无）

## Impact

- **Affected code**: `skills/_lib/iteration.py`（删除）→ `skills/_lib/iteration/`（4 文件）
- **Scope**: 模块内部重组，公有 API 不变
- **Risk**: 中——需确保 re-export 兼容所有现有 import
- **Effort**: 1-2 天