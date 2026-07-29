## Why

guide-ship Phase 3 归档时，`openspec archive --yes` 对 tasks.md 中全部 `[ ]` 的 change 仅 warning 不阻断，导致未实现即归档的问题。需要增加"实现完成"验证门控。

## What Changes

- guide-ship Phase 3 归档前增加门控检查：`grep -c '\[x\]' tasks.md` ≥ 1 才能归档
- 0 个完成任务的 change 提示"未实现，确认归档？"并要求二次确认
- 支持 `FORCE_ARCHIVE_INCOMPLETE=yes` 跳过检查

## Capabilities

### New Capabilities
- `archive-completion-gate`: 归档前验证 tasks.md 完成状态

### Modified Capabilities
- `archive-flow`: 在归档流程中增加完成度门控

## Impact

- 修改文件：skills/_lib/archive.sh 或 skills/guide-ship/scripts/ship_archive.sh
- 影响流程：guide-ship Phase 3 归档流程
- 新增环境变量：FORCE_ARCHIVE_INCOMPLETE
