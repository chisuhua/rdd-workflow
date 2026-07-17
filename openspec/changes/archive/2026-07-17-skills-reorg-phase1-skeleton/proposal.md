---
SCOPE: shared
STATUS: PROPOSED
---

## Why

`skills/` 目录当前是扁平结构：13 个 `.md` 文件 + 90+ 个 `_lib/` 文件全部平铺在一个目录下。参考 `/workspace/project/PKGM-Web/PKGM-Wiki/skills/` 的 PKGM-Wiki 模式，每个技能应是一个独立子目录 (`SKILL.md` + `scripts/` + `references/`)。

本 change（Phase 1）做最小风险的结构性改变：创建子目录骨架、移动 SKILL.md 文件、更新 INSTALL.md 复制逻辑。因 `$(dirname ...)` 的解析目录从 `skills/` 变为 `skills/<name>/`，需要进行约 15 处机械性的 `source` 路径调整（`_lib/X.sh` → `../_lib/X.sh`，sed 批量替换）。**不涉及 import 路径或 _lib/ 内部文件改动**。

## What Changes

1. 为 12 个 skill 创建 per-skill 子目录 (`skills/<name>/`)，各含 `scripts/` 和 `references/` 骨架
2. 将 12 个 `skills/<name>.md` 移入对应子目录的 `SKILL.md`
3. 更新 `skills/INSTALL.md`（保持在顶层）的复制逻辑：从 `cp skills/*.md` 改为递归复制整个子目录
4. 保留 `skills/_lib/`、`skills/__init__.py`、`skills/loop_engine.py` 原位不动

## Impact

- **`source` 路径需调整**：`$(dirname ...)` 从 `skills/` 变为 `skills/<name>/`，所有 `_lib/X.sh` 引用需加 `../` 前缀（sed 批量替换，约 15 处）
- **`import` 路径不受影响**：Python 使用点分隔路径（`from skills._lib.X import Y`），sed 无法匹配
- **`skill_use()` 不受影响**：基于 `name` 字段查找，不依赖文件路径
- 仅影响 `INSTALL.md` 复制逻辑和 `package.json` `skills` 数组（name 字段不变,仅文件位置变）

## Dependencies

- **前置 change**: 无
- **后续 change**: `skills-reorg-phase2-single-skill`（将单 skill helper 迁移到 `scripts/`）