## Why

`skills/loop_engine.py`（358 行）是 v2.0 引擎入口，却放在 `skills/` 根目录与其他 13 个 `.md` skill 文件并列。这是历史遗留，应迁入 `skills/_lib/` 并加 re-export shim。

## What Changes

- `skills/loop_engine.py` → `skills/_lib/loop_engine.py`（迁移）
- `skills/loop_engine.py` 保留为 re-export shim：`from skills._lib.loop_engine import *`
- 更新所有 import 路径
- 更新 AGENTS.md 和 README 中 loop_engine.py 的路径引用

## Capabilities

### New Capabilities
- （无——纯文件移动）

### Modified Capabilities
- （无——公有 API 不变）

## Impact

- **Affected code**: `skills/loop_engine.py`（变 shim）+ `skills/_lib/loop_engine.py`（新位置）
- **Scope**: 文件移动 + re-export shim
- **Risk**: 低——保持向后兼容
- **Effort**: 半天