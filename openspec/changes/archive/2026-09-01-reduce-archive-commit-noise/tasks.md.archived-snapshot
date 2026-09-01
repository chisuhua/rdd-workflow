# Tasks: reduce-archive-commit-noise

## Implementation Tasks

- [x] Task 1: `tests/integration/test_archive_commit_count.bats` 新增 3 个测试 PASS
- [x] Task 2: single change → ≤2 commits（merge + archive）
- [x] Task 3: ARCHIVE_SINGLE_COMMIT=yes → 1 commit
- [x] Task 4: no residue → no extra cleanup commit
- [x] Task 5: 现有 `test_commit_archive_moves.bats` 3 个测试适配后 PASS
- [x] Task 6: `test_post_archive_cleanup.bats`（如有）更新后 PASS
- [x] Task 7: 复测 2026-08-31 场景：archive 1 个 change，git log 从 4 commit 降至 2 commit
- [x] Task 8: 批量 archive 3 个 change，git log 总 commit 数 ≤ 6（此前 12-15）
- [x] Task 9: `SKIP_ARCHIVE_AUTO_COMMIT=yes` 时 behavior 不变（不合并也不独立 commit）
- [x] Task 10: AGENTS.md "Archive Auto-Commit" 段更新：说明 cleanup 合并到 archive 主体 + ARCHIVE_SINGLE_COMMIT 开关
- [x] Task 11: `docs/adr/ADR-0036-archive-commit-merging.md`（新 ADR 或并入现有）
- [x] Task 12: `rddf archive-history`（基于 commit message 前缀）仍正确解析（archive 主体 message 不变）
- [x] Task 13: 既有 `archive(NAME): archive completed` 约定不被破坏
- [x] Task 14: 与 `bypass-audit-mechanism`（延迟）无交互
- [x] Task 15: ship 后 30 天：archive 相关 commit 数下降 ≥ 50%（4 → 2）
- [x] Task 16: 不引入新的 KNOWN_FAILURES 条目
