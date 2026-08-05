# worktree-archive-workflow — Design

## Context

AGENTS.md 写"execute 阶段不 commit/push",但 `_lib/archive.sh::archive_change` 通过 `check_worktree_commits` 要求 worktree 分支有 commits。本次会话中 5 个 archive 都在 worktree 内手动 commit working tree 后再归档。该模式隐含在 archive-history 的 commit message(`feat(rddf-session): add --archive-orphans flag`)中,但缺乏显式文档。

此外,5 个顺序归档导致 master 落后 5+ commits,每次都需要 no-ff merge,效率不高。

## Goals / Non-Goals

**Goals:**

- AGENTS.md / guide-ship SKILL.md 显式规则:
  - execute 阶段:worktree 内修改,**worktree 内 commit**(working tree)
  - archive 阶段:由 `archive_change_for_mode` 自动 merge + openspec archive
- 文档化 commit message 风格(参考 archive-history 的 `feat(<scope>): ...` 模式)
- 跨 worktree 批量归档策略(可选研究):
  - rebase 所有 worktree 到最新 master 后逐个 archive
  - 或批量 no-ff merge 优化

**Non-Goals:**

- 修改 archive.sh 核心逻辑
- 修改 git worktree 行为

## Decisions

### 显式规则(写入 AGENTS.md + guide-ship SKILL.md)

```markdown

## Risks / Trade-offs

- **正向**: 新用户/agent 不会困惑于 "execute 不 commit 但 archive 需要 commits" 的矛盾
- **正向**: 批量归档可减少 master 落后 commits 数
- **风险**: rebase 操作可能引入冲突(需 worktree 协调)
- **兼容性**: 不破坏现有 execute/archive 流程,仅文档化 + 优化

## Migration Plan

1. 本提案在主仓库实施,通过 guide-plan + guide-ship 工作流
2. 执行完成后 openspec archive 归档到 openspec/changes/archive/YYYY-MM-DD-worktree-archive-workflow/
3. 不涉及运行时数据迁移(纯 workflow 增强)

## Open Questions

无 — 提案中所有关键场景(S1-S6 等)已定义清晰。
