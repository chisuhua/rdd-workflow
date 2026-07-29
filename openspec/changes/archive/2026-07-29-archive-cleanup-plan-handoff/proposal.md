## Why

`add-cudart-unit-tests` 归档后 `.rddf/state/.plan-handoff.json` 仍然指向已归档的 change，没有任何步骤清理或重置这个 handoff 文件，导致 handoff 状态与文件系统实际状态不一致。

## What Changes

- ship_archive.sh::archive_change() 末尾增加 handoff 清理步骤
- handoff 清理格式：追加 `archived_at` 时间戳，记录已归档的 change 名称
- 如果所有 changes 已归档，将 `active_changes` 置 0
- 如果还有未归档的 changes，只更新归档 change 的记录，保留 `active_changes` 计数
- 幂等保证：重复归档同一 change 不报错

## Capabilities

### New Capabilities
- `plan-handoff-cleanup`: 归档后清理 plan-handoff 状态

### Modified Capabilities
- `archive-flow`: 在归档流程末尾增加 handoff 清理

## Impact

- 修改文件：skills/guide-ship/scripts/ship_archive.sh
- 影响文件：.rddf/state/.plan-handoff.json
- 向后兼容：老版本没有 archived_at 字段也能正常读取
