# worktree-archive-workflow

## Why

AGENTS.md 写"execute 阶段不 commit/push",但 `_lib/archive.sh::archive_change` 通过 `check_worktree_commits` 要求 worktree 分支有 commits。本次会话中 5 个 archive 都在 worktree 内手动 commit working tree 后再归档。该模式隐含在 archive-history 的 commit message(`feat(rddf-session): add --archive-orphans flag`)中,但缺乏显式文档。

此外,5 个顺序归档导致 master 落后 5+ commits,每次都需要 no-ff merge,效率不高。

## What Changes

**In Scope**:

- AGENTS.md / guide-ship SKILL.md 显式规则:
- execute 阶段:worktree 内修改,**worktree 内 commit**(working tree)
- archive 阶段:由 `archive_change_for_mode` 自动 merge + openspec archive
- 文档化 commit message 风格(参考 archive-history 的 `feat(<scope>): ...` 模式)
- 跨 worktree 批量归档策略(可选研究):
- rebase 所有 worktree 到最新 master 后逐个 archive
- 或批量 no-ff merge 优化
- 修改 archive.sh 核心逻辑
- 修改 git worktree 行为

**Out of Scope**:

- (TBD)

## Capabilities

- (TBD)

## Impact

- (TBD)

## Acceptance

- [ ] (TBD — 验收标准 from improvements 头部未提供)

