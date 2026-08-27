# fix-iteration-archive-sync — Implementation Tasks

## Implementation Tasks

- [ ] Task 1: `_lib/archive.sh::archive_change` 在 `openspec archive` 成功后调用 `iteration.add_or_update_change`
- [ ] Task 2: `_lib/iteration/store.py` 的 `add_or_update_change` 支持 `status='archived'` 且 `tasks_done` 字段
- [ ] Task 3: 新增 unit test `tests/unit/test_archive_iteration_sync.py` 覆盖以下场景:
- [ ] Task 4: 已有 archive 的 3 个 P1 change 一次性 sync 到 iteration.json(`status='archived'`)
- [ ] Task 5: `rddf rdd-verify --dry-run` 在 sync 后能正确识别 archived change 为"已通过"(无需 verify)
- [ ] Task 6: `bash tests/scripts/report_regression.sh` 不增加新 failure
- [ ] Task 7: Run `bash tests/scripts/report_regression.sh` to confirm no new failures