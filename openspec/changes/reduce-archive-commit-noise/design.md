# reduce-archive-commit-noise

## Context

**症状 (2026-08-31 ship 阶段, 2 个 P1 change archive)**:

archive `reduce-rdd-workflow-tool-call-friction` 后 git log：

```
0e771f8 chore(post-archive): clean residue from reduce-rdd-workflow-tool-call-friction
aa1d84f chore(post-archive): clean residue from reduce-rdd-workflow-tool-call-friction
69c061b archive(reduce-rdd-workflow-tool-call-friction): archive completed
5e18ed4 merge: reduce-rdd-workflow-tool-call-friction change
```

- merge（1 个）+ archive 主体（1 个）+ post-archive cleanup（2 个：stage + commit）→ 4 个 commit
- 同一 pattern 出现在 worktree-context-persistence（也是 4 个）
- 两个 post-archive cleanup commit（`aa1d84f` + `0e771f8`）内容相同（都是 clean residue），属重复

**根因分析**:

`skills/_lib/archive.sh::archive_change()` 流程（v2.0.5 起）：

1. `git merge`（worktree 分支并入 master）→ commit 1
2. `openspec archive <name> --yes`（文件移动）
3. `commit_archive_moves <name> <main_root>` → commit 2（archive 主体）
4. `post_archive_cleanup.sh` → 检测残留 tracked 文件（deleted `.rddf/plans/<name>.md` 等）+ `git commit` → commit 3
5. 同一 cleanup 脚本再跑一次（幂等保护）→ 又 commit 4（当有残留时）

第 4 步的 `post_archive_cleanup` 独立 commit 是可合并的：它清理的是同一 change 的残留，应与 archive 主体（commit 2）合并为 1 个。

**影响范围**:

- 每个 change archive 产生 4-5 个 commit（理想应为 2-3 个：merge + archive，cleanup 并入）
- N 个 change 的批量 archive（如 9 个并行）产生 36-45 个 commit，历史噪音显著
- git log 难以区分「archive 主体」与「cleanup 残留」commit
- 后续 `rddf archive-history` 分析（基于 commit message 前缀）可能误读

## Goals

**In Scope**:

- 修改 `skills/_lib/post_archive_cleanup.sh`：
- cleanup 检测到残留时，**不独立 commit**，而是 stage 改动到 archive 主体的 commit（`git commit --amend --no-edit` 或合并 stage）
- 或：`archive.sh::archive_change` 在调用 `commit_archive_moves` 之前先跑 cleanup（cleanup 的 stage 合并到 archive commit），最后统一 commit 1 次
- 目标：每 change archive 产生 2 个 commit（merge + archive-with-cleanup）
- 幂等性保留：cleanup 二次运行无残留时立即 exit 0（无新 commit）
- 默认保留 2-commit 模式（merge + archive）兼容现有测试
- `ARCHIVE_SINGLE_COMMIT=yes` 时 merge + archive 合并为 1 个 commit（squash）
- 提供用户选择：verbose（2-3 commit）vs 简洁（1 commit）
- 默认 off（不动现有行为），opt-in 简洁模式
- 现有 `tests/integration/test_commit_archive_moves.bats`（3 个 test）适配 cleanup 合并
- `tests/integration/test_post_archive_cleanup.bats`（如有）更新断言 commit 数
- 新增 `tests/integration/test_archive_commit_count.bats`：
- `archive-commit-count: single change produces ≤2 commits (merge + archive)`
- `archive-commit-count: ARCHIVE_SINGLE_COMMIT=yes produces 1 commit`
- `archive-commit-count: no residue → no extra cleanup commit`
- **不修改** `commit_archive_moves` 的既有逻辑（archive 主体 commit message 格式不变）
- **不重写** `post_archive_cleanup.sh` 的残留检测逻辑（只改提交策略）
- **不修改** merge 策略（ff-only vs no-ff 由 archive_change 决定）
- **不修改** `SKIP_ARCHIVE_AUTO_COMMIT` 语义（opt-out 保留）

### 关键场景

### 场景 1: archive 无残留（正常 case）

- **GIVEN** change archive 后无残留 tracked 文件（clean）
- **WHEN** `archive_change` 完成
- **THEN** git log 显示 2 个 commit：merge + archive
- **AND** 无额外 cleanup commit

### 场景 2: archive 有残留（plan 文件等）

- **GIVEN** `.rddf/plans/<name>.md` 等残留 tracked 文件
- **WHEN** `archive_change` 完成
- **THEN** cleanup stage 合并到 archive commit（`--amend`），git log 仍 2 个 commit
- **AND** 残留文件已删除（cleanup 生效）

### 场景 3: `ARCHIVE_SINGLE_COMMIT=yes`

- **GIVEN** 用户设置 `ARCHIVE_SINGLE_COMMIT=yes`
- **WHEN** `archive_change` 完成
- **THEN** merge + archive + cleanup 合并为 1 个 commit
- **AND** git log 显示 1 个 commit

### 场景 4: cleanup 二次运行幂等

- **GIVEN** 无残留（已清理）
- **WHEN** `post_archive_cleanup.sh` 再跑
- **THEN** 立即 exit 0，无新 commit（保留现有幂等性）

**Out of Scope**:

- (no items specified)

## Decisions

- **MUST NOT**: 修改 `commit_archive_moves` 的 archive 主体 commit message（`archive(<name>): archive completed` 约定保留）
- **MUST NOT**: 修改 merge 策略（ff-only/no-ff 由 archive_change 现有逻辑决定）
- **MUST NOT**: 引入新依赖（git 原生 `--amend` / `--squash`）
- **MUST**: 与 `SKIP_ARCHIVE_AUTO_COMMIT=yes` 兼容（cleanup 合并也应遵守该 opt-out）
- **MUST**: 幂等性保留（重复运行无副作用）
- **SHOULD**: cleanup 合并用 `git commit --amend --no-edit` 而非 squash（保留 archive 主体 message）
- **SHOULD**: 与 `post-archive-cleanup-hook` 提案（既有）不冲突：该提案是 hook 自动化，本提案是 commit 合并策略

## Risks

- (no items specified)
