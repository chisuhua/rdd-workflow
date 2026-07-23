# fix-stale-suggestions-warning

**优先级**: P2 | **来源**: 会话复盘 2026-07-23 — proposal-suggestions.md 过时警告
**阶段**: v2.1 | **分类**: docs
**类型**: feature

## 架构依据

- `proposal-suggestions.md` 底部显示："⚠️ 以上提案的实际 .md 文件尚未从旧 JSON 格式迁移"
- 迁移脚本 (`migrate_proposals.py`) 已在 2026-07-23 执行完毕，45 个文件全部创建
- 警告已过时，误导后续开发者

## 范围

- **In Scope**:
  - 从 `proposal-suggestions.md` 中移除过时警告
  - 在 `list_improvements` 函数中增加检测：若 improvements/ 目录存在 .md 文件，跳过警告
  - 或者：迁移脚本执行后自动从索引中移除该警告行
- **Out Scope**:
  - 不修改提案迁移逻辑

## 关键场景

- GIVEN improvements/ 目录有 45 个 .md 文件, WHEN 查看 proposal-suggestions.md, THEN 无"尚未迁移"警告

## 技术约束

- MUST 仅移除警告文本，不修改索引表内容
- SHOULD 在迁移脚本中增加自动移除警告的逻辑

## 验收标准

- proposal-suggestions.md 底部无"尚未从旧 JSON 格式迁移"警告
- 迁移脚本再次执行时自动移除警告
