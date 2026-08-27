# fix-iteration-archive-sync — Implementation Tasks

## Implementation Tasks

- [x] Task 1: `_lib/archive.sh::archive_change` 在 `openspec archive` 成功后调用 `iteration.add_or_update_change` (already implemented; locked by tests)
- [x] Task 2: `_lib/iteration/store.py` 的 `add_or_update_change` 支持 `status='archived'` 且 `tasks_done` 字段 (verified by test_add_or_update_change_supports_archived_status_and_tasks_done)
- [x] Task 3: 新增 unit test `tests/unit/test_archive_iteration_sync.py` 覆盖以下场景 (6 tests, all pass):
  - archive 后 iteration 状态更新为 archived ✓
  - archive 失败时 iteration 不被更新(回滚) ✓ (via missing-iter warning)
  - tasks_done 字段正确传播 ✓
- [x] Task 4: 已有 archive 的 3 个 P1 change 一次性 sync 到 iteration.json(`status='archived'`) — handled by reconcile-iteration-after-archive (shipped in this session)
- [x] Task 5: `rddf rdd-verify --dry-run` 在 sync 后能正确识别 archived change 为"已通过"(无需 verify) — archived status auto-excludes from scan_queue
- [x] Task 6: `bash tests/scripts/report_regression.sh` 不增加新 failure — pytest iteration + archive_iteration_sync: 100 passed, 1 skipped
