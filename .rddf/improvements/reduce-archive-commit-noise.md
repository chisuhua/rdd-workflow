# reduce-archive-commit-noise

**优先级**: P2 | **来源**: 2026-08-31 ship 阶段复盘 — 每个 change archive 产生 4-5 个 commit，git history 噪音大
**阶段**: v2.2 | **分类**: infra-setup / archive
**类型**: refactor

> **症状**：每次 archive 一个 change，实际产生 4-5 个 commit（merge → archive → 2× post-archive cleanup stage → cleanup commit），违反「git history 干净」的 ship 原则。
> **根因**：`archive.sh::archive_change` 的 post-archive cleanup（`post_archive_cleanup.sh`）独立 `git commit`，未合并到 archive 主体 commit。
> **触发**：2026-08-31 archive `reduce-rdd-workflow-tool-call-friction` 时 git log 显示 5 个 commit（merge / archive / 2 cleanup stage / cleanup commit）。

## 架构依据

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

## 范围

### In Scope

**A. post_archive_cleanup 合并到 archive 主体 commit**:

- 修改 `skills/_lib/post_archive_cleanup.sh`：
  - cleanup 检测到残留时，**不独立 commit**，而是 stage 改动到 archive 主体的 commit（`git commit --amend --no-edit` 或合并 stage）
  - 或：`archive.sh::archive_change` 在调用 `commit_archive_moves` 之前先跑 cleanup（cleanup 的 stage 合并到 archive commit），最后统一 commit 1 次
- 目标：每 change archive 产生 2 个 commit（merge + archive-with-cleanup）
- 幂等性保留：cleanup 二次运行无残留时立即 exit 0（无新 commit）

**B. 可选 `ARCHIVE_SINGLE_COMMIT=yes` 开关**:

- 默认保留 2-commit 模式（merge + archive）兼容现有测试
- `ARCHIVE_SINGLE_COMMIT=yes` 时 merge + archive 合并为 1 个 commit（squash）
- 提供用户选择：verbose（2-3 commit）vs 简洁（1 commit）
- 默认 off（不动现有行为），opt-in 简洁模式

**C. 测试更新**:

- 现有 `tests/integration/test_commit_archive_moves.bats`（3 个 test）适配 cleanup 合并
- `tests/integration/test_post_archive_cleanup.bats`（如有）更新断言 commit 数
- 新增 `tests/integration/test_archive_commit_count.bats`：
  - `archive-commit-count: single change produces ≤2 commits (merge + archive)`
  - `archive-commit-count: ARCHIVE_SINGLE_COMMIT=yes produces 1 commit`
  - `archive-commit-count: no residue → no extra cleanup commit`

### Out Scope

- **不修改** `commit_archive_moves` 的既有逻辑（archive 主体 commit message 格式不变）
- **不重写** `post_archive_cleanup.sh` 的残留检测逻辑（只改提交策略）
- **不修改** merge 策略（ff-only vs no-ff 由 archive_change 决定）
- **不修改** `SKIP_ARCHIVE_AUTO_COMMIT` 语义（opt-out 保留）

## 关键场景

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

## 技术约束

- **MUST NOT**: 修改 `commit_archive_moves` 的 archive 主体 commit message（`archive(<name>): archive completed` 约定保留）
- **MUST NOT**: 修改 merge 策略（ff-only/no-ff 由 archive_change 现有逻辑决定）
- **MUST NOT**: 引入新依赖（git 原生 `--amend` / `--squash`）
- **MUST**: 与 `SKIP_ARCHIVE_AUTO_COMMIT=yes` 兼容（cleanup 合并也应遵守该 opt-out）
- **MUST**: 幂等性保留（重复运行无副作用）
- **SHOULD**: cleanup 合并用 `git commit --amend --no-edit` 而非 squash（保留 archive 主体 message）
- **SHOULD**: 与 `post-archive-cleanup-hook` 提案（既有）不冲突：该提案是 hook 自动化，本提案是 commit 合并策略

## 验收标准

### 单元与集成测试

- [ ] `tests/integration/test_archive_commit_count.bats` 新增 3 个测试 PASS
  - [ ] single change → ≤2 commits（merge + archive）
  - [ ] ARCHIVE_SINGLE_COMMIT=yes → 1 commit
  - [ ] no residue → no extra cleanup commit
- [ ] 现有 `test_commit_archive_moves.bats` 3 个测试适配后 PASS
- [ ] `test_post_archive_cleanup.bats`（如有）更新后 PASS

### 端到端验证

- [ ] 复测 2026-08-31 场景：archive 1 个 change，git log 从 4 commit 降至 2 commit
- [ ] 批量 archive 3 个 change，git log 总 commit 数 ≤ 6（此前 12-15）
- [ ] `SKIP_ARCHIVE_AUTO_COMMIT=yes` 时 behavior 不变（不合并也不独立 commit）

### 文档化

- [ ] AGENTS.md "Archive Auto-Commit" 段更新：说明 cleanup 合并到 archive 主体 + ARCHIVE_SINGLE_COMMIT 开关
- [ ] `docs/adr/ADR-0036-archive-commit-merging.md`（新 ADR 或并入现有）

### 兼容性验证

- [ ] `rddf archive-history`（基于 commit message 前缀）仍正确解析（archive 主体 message 不变）
- [ ] 既有 `archive(NAME): archive completed` 约定不被破坏
- [ ] 与 `bypass-audit-mechanism`（延迟）无交互

### 副作用监测

- [ ] ship 后 30 天：archive 相关 commit 数下降 ≥ 50%（4 → 2）
- [ ] 不引入新的 KNOWN_FAILURES 条目

## Why

- **现状痛点**：每个 change archive 产生 4-5 个 commit（merge + archive + 2 cleanup），批量 archive 时 git history 噪音显著。本次 2 个 change 就产生 8 个 archive 相关 commit。
- **修复价值**：commit 数降 50%+，git history 更干净，`archive-history` / 复盘更准确。低成本（cleanup 提交策略改动 + 测试更新）。
- **Why now**: 2026-08-31 session 首次观察到 4-commit pattern，且批量 archive（9+ change）场景会放大。P2 而非 P1 因为它不阻塞 flow（仅历史噪音），且改动涉及 archive 核心逻辑需谨慎测试。

## What Changes

- `skills/_lib/post_archive_cleanup.sh`: cleanup 提交策略（stage 合并到 archive 主体，~10 行）
- `skills/_lib/archive.sh::archive_change`: 调用顺序调整（cleanup 在 commit_archive_moves 之前或 --amend 合并）
- `skills/_lib/ship_archive.sh`: ARCHIVE_SINGLE_COMMIT=yes 开关接线（~10 行）
- `tests/integration/test_archive_commit_count.bats`: 新测试（3 cases）
- `tests/integration/test_commit_archive_moves.bats`: 适配（断言更新）
- AGENTS.md / ADR: 文档更新

## Capabilities

- MUST: archive 后 git log ≤2 commits（merge + archive-with-cleanup）
- MUST: ARCHIVE_SINGLE_COMMIT=yes → 1 commit
- MUST NOT: 破坏 `archive(NAME): archive completed` message 约定
- MUST NOT: 引入额外失败（幂等保留）

## Impact

- MUST: 与 `SKIP_ARCHIVE_AUTO_COMMIT` 兼容
- MUST: `rddf archive-history` 解析不变
- SHOULD: 批量 archive 场景 commit 数显著下降
- MUST NOT: 改变 merge/archive 的功能语义

## Acceptance

- [ ] archive 1 个 change → git log ≤2 commit
- [ ] ARCHIVE_SINGLE_COMMIT=yes → 1 commit
- [ ] 无残留 → 无额外 cleanup commit
- [ ] `test_archive_commit_count.bats` 3 个测试 PASS
- [ ] 现有 archive 测试适配后全绿
- [ ] AGENTS.md / ADR 更新