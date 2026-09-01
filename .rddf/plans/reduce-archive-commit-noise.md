# reduce-archive-commit-noise Implementation Plan

**Goal**: 合并 `post_archive_cleanup.sh` 的独立 commit 到 archive 主体 commit,降低每个 archive 产生 4-5 个 commit 的噪音(v2.0.5+ commit flow 已准备 `--amend` 合并点)。

**Approach**: 修改 `_lib/archive.sh` 的 `archive_change` 函数,在 `commit_archive_moves` 后 amend 合并 cleanup 的 stage,保留原 idempotency。

**Tech Stack**: bash 4.x, git。

## Tasks

### Task 1: 合并 cleanup 到 archive commit

- [ ] **Step 1**: 看 archive.sh 的 archive_change 函数,定位 commit_archive_moves 与 post_archive_cleanup 顺序
- [ ] **Step 2**: 修改 post_archive_cleanup 阶段: 不独立 commit, 而是 stage 改动让 commit_archive_moves 包含(若已 commit 则 no-op)
- [ ] **Step 3**: 验证 idempotency: cleanup 二次运行无残留 → 立即 exit 0,无新 commit
- [ ] **Step 4**: 跑现有 archive 相关 bats 不 regression
- [ ] **Step 5**: Defer commit

### Task 2: 文档 + tasks.md + commit + archive

[Standard pattern]
