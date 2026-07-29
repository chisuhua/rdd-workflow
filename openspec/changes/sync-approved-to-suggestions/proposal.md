## Why

`proposal-approved.md` 有 42 个批准条目，但 `proposal-suggestions.md` 中对应条目未更新状态。`append_approved` 只写 approved.md，不更新 suggestions.md，双索引缺乏自动同步机制，人工维护成本高。

## What Changes

- `append_approved` 函数中增加：同步更新 `proposal-suggestions.md` 中对应条目
- `mark_approved_completed` 中增加：同步更新 suggestions.md
- 或新增 `sync_suggestions_index` 函数，按 approved.md 状态批量更新 suggestions.md

## Capabilities

### New Capabilities
- `suggestions-sync`: 双索引自动同步机制

### Modified Capabilities
- `proposal-state-management`: 扩展 append_approved 和 mark_approved_completed 的同步逻辑

## Impact

- 修改文件：skills/_lib/state.sh
- 影响文件：proposal-approved.md, proposal-suggestions.md
- 容错：suggestions.md 中找不到对应条目时静默跳过
