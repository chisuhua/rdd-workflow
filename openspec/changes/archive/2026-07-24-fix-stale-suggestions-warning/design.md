# Design: fix-stale-suggestions-warning

## Context

`proposal-suggestions.md` 底部显示过时警告："⚠️ 以上提案的实际 .md 文件尚未从旧 JSON 格式迁移"。迁移脚本已在 2026-07-23 执行完毕，45 个文件全部创建。警告误导后续开发者。

## Goals / Non-Goals

### Goals

- 从 `proposal-suggestions.md` 中移除过时警告文本
- 在 `list_improvements` 函数中增加检测：improvements/ 目录有 .md 文件时跳过警告
- 迁移脚本执行后自动移除警告行
- 仅移除警告文本，不修改索引表内容

### Non-Goals

- 不修改提案迁移逻辑

## Decisions

两层处理：

1. **即时修复**：直接从 `proposal-suggestions.md` 移除警告行
2. **防御性检测**：在 `list_improvements` 函数中，输出警告前检查 `improvements/` 目录是否有 .md 文件，有则不输出警告

迁移脚本 `migrate_proposals.py` 末尾增加 `sed` 删除警告行的逻辑，确保再次执行时自动清理。

## Implementation

**关键修改文件:**

- `proposal-suggestions.md` — 移除底部 `⚠️ 以上提案的实际 .md 文件尚未从旧 JSON 格式迁移` 行
- `skills/_lib/state.sh` — `list_improvements` 函数增加 improvements/ .md 文件检测
- `migrate_proposals.py` — 末尾增加自动移除警告行的逻辑
