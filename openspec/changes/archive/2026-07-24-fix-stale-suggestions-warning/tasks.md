# Tasks: fix-stale-suggestions-warning

## Implementation Steps

- [ ] 从 `proposal-suggestions.md` 移除过时警告文本
  - 删除底部 `⚠️ 以上提案的实际 .md 文件尚未从旧 JSON 格式迁移` 行
  - 仅移除警告，不修改索引表内容
- [ ] 在 `skills/_lib/state.sh` 的 `list_improvements` 函数增加检测
  - 检查 `improvements/` 目录是否存在 .md 文件
  - 若存在则跳过"尚未迁移"警告输出
- [ ] 在 `migrate_proposals.py` 末尾增加自动移除警告逻辑
  - 迁移完成后 `sed` 删除警告行
  - 确保再次执行时自动清理

## Verification (验收标准)

- [ ] proposal-suggestions.md 底部无"尚未从旧 JSON 格式迁移"警告
- [ ] 迁移脚本再次执行时自动移除警告

## Key Scenarios (关键场景)

- [ ] GIVEN improvements/ 目录有 45 个 .md 文件, WHEN 查看 proposal-suggestions.md, THEN 无"尚未迁移"警告
