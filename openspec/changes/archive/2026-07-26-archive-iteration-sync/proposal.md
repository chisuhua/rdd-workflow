## Why

复盘发现：archive 流程完成后，iteration.json 中 5/8 个 change 缺少 `archived_at` 时间戳，`feature_view.archived_count` 与实际值差 5。根因是 skeleton→archive 快速路径跳过了 iteration 同步步骤。

`mark_iteration_archived` 辅助函数已在 `skills/_lib/archive.sh` 中实现，worktree 模式和轻量模式均已集成调用。但缺少以下保障：
1. 回归测试覆盖（正常归档、重复归档幂等、archive 失败不写入）
2. skeleton→archive 快速路径的迭代同步验证
3. `feature_view.archived_count` 动态计算验证（不依赖缓存字段）

## What Changes

- **Add** 3 bats 回归测试覆盖 `mark_iteration_archived` 行为：
  - 正常归档：archive 后 iteration.json 中 `archived_at` 存在且 `status == "archived"`
  - 重复归档幂等：对已归档 change 再次调用，不报错且 `archived_at` 不变
  - archive 失败不写入：模拟 openspec archive 失败场景，`iteration.json` 无变更
- **Verify** `feature_view.archived_count` 从 iteration 动态计算（已有 `feature_progress()` 实现，确认无缓存字段依赖）
- **Document** skeleton→archive 路径的迭代同步契约

## Capabilities

### New Capabilities
- `archive-iteration-sync-regression`: 3 个 bats 测试锁定 `mark_iteration_archived` 行为，防止回归

### Modified Capabilities
- `archive-iteration-sync`: `mark_iteration_archived` 已有完整实现，需测试验证

## Impact

- **New code**: ~120 lines (3 bats tests) + ~20 lines (test helpers, fixtures)
- **Dependencies**: None (uses existing `skills._lib.iteration` module and `archive.sh`)
- **Compatibility**: 100% backward compatible — no behavioral change
- **Risk**: Low — additive testing; no production code changes
- **Source**: Session 复盘 2026-07-21, improvement `archive-iteration-sync`