# Proposal: fix-stale-suggestions-warning

## Why

`proposal-suggestions.md` 底部显示："⚠️ 以上提案的实际 .md 文件尚未从旧 JSON 格式迁移"。迁移脚本 (`migrate_proposals.py`) 已在 2026-07-23 执行完毕，45 个文件全部创建。警告已过时，误导后续开发者。

来源: 会话复盘 2026-07-23

## What Changes

- 从 `proposal-suggestions.md` 中移除过时警告
- 在 `list_improvements` 函数中增加检测：若 improvements/ 目录存在 .md 文件，跳过警告
- 或者：迁移脚本执行后自动从索引中移除该警告行
- 不修改提案迁移逻辑

## Capabilities

### New Capabilities: fix-stale-suggestions-warning

移除 `proposal-suggestions.md` 中过时的"尚未从旧 JSON 格式迁移"警告。在 `list_improvements` 函数中增加检测：若 `improvements/` 目录存在 .md 文件则跳过警告。迁移脚本执行后自动移除警告行。

## Impact

**受影响文件:**
- `proposal-suggestions.md` — 移除底部警告文本
- `skills/_lib/state.sh` — `list_improvements` 函数增加检测逻辑
- `migrate_proposals.py` — 增加自动移除警告逻辑（可选）

**不受影响:**
- 提案迁移逻辑
