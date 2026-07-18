## Why

AGENTS.md 的"关键目录"章节中 `skills/_lib/` 列表缺少 `core/` / `loop/` / `schedulers/` 子目录标注。这导致审查者误以为 `loop_state.py` / `event_queue.py` 等文件不存在。AGENTS.md 是项目主要文档入口，模块地图过时影响所有下游开发者和 AI 审查者。

## What Changes

- AGENTS.md "关键目录"章节 _lib/ 部分更新：标注 core/（6 文件）、loop/（15 文件）、schedulers/ 子目录
- 更新 Python 模块描述列表，标注每个模块的子目录归属
- 添加简单树形结构展示子目录层次
- 更新文件计数以反映实际文件数

## Capabilities

### New Capabilities
- （无——纯文档更新）

### Modified Capabilities
- （无）

## Impact

- **Affected code**: 仅 `AGENTS.md`
- **Scope**: 1 个文件，约 20 行更新
- **Risk**: 极低
- **Effort**: 10 分钟