## 1. Verify `mark_iteration_archived` is called in both archive paths (T1)

- [ ] 1.1 **Verify**: `skills/_lib/archive.sh` has `mark_iteration_archived` at line 331-377, called in `archive_change()` at line 306
- [ ] 1.2 **Verify**: `skills/guide-ship/scripts/ship_archive.sh` calls `mark_iteration_archived` in lightweight path at line 196
- [ ] 1.3 **Verify**: Existing structural test `tests/integration/test_archive_iteration_sync.bats` confirms both paths call `mark_iteration_archived`
- [ ] 1.4 **Run**: `bats tests/integration/test_archive_iteration_sync.bats` — 3 tests pass (structural grep for lightweight + worktree paths + Python module verification)
- [ ] 1.5 **Run**: `bats tests/integration/test_iteration_archive_hook.bats` — 7 tests pass (functional behavior: status change, field preservation, error tolerance, corrupt file, missing entry)

## 2. Verify `feature_view.archived_count` is dynamically computed (T2)

- [ ] 2.1 **Verify**: `skills/_lib/iteration/store.py` → `feature_progress()` (L470-482) computes `archived_count` as `sum(1 for c in changes if c.get("status") == "archived")` — no cache field
- [ ] 2.2 **Verify**: `list_archived()` (L308-315) sorts by `archived_at` dynamically — no cache
- [ ] 2.3 **Run**: `python3 -m pytest tests/unit/ -k "feature_progress" -q --tb=short` — confirm feature_progress tests pass

## 3. Archive iteration sync summary (T3)

- [ ] 3.1 **Summary**: `mark_iteration_archived` is fully implemented in both worktree path (via `archive_change`) and lightweight path (direct call in `ship_archive.sh`)
- [ ] 3.2 **Coverage**: 10 existing tests (3 structural + 7 behavioral) cover all scenarios from the improvement spec:
  - ✅ 正常归档 → `test_iteration_archive_hook.bats` L53-63 (status=archived, archived_at set)
  - ✅ 重复归档幂等 → `mark_archived` in Python is idempotent (overwrites archived_at)
  - ✅ Archive 失败不写入 → `mark_iteration_archived` is only called after successful openspec archive
  - ✅ `feature_view.archived_count` 动态计算 → `feature_progress()` uses sum over changes array
- [ ] 3.3 **Verification**: Run `bats tests/integration/test_archive_iteration_sync.bats tests/integration/test_iteration_archive_hook.bats` — all pass