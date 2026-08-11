# worktree-archive-workflow

**优先级**: P0 | **来源**: 2026-08-04 session 复盘
**阶段**: default | **分类**: core-impl
**类型**: improvement

## 架构依据

AGENTS.md 写"execute 阶段不 commit/push",但 `_lib/archive.sh::archive_change` 通过 `check_worktree_commits` 要求 worktree 分支有 commits。本次会话中 5 个 archive 都在 worktree 内手动 commit working tree 后再归档。该模式隐含在 archive-history 的 commit message(`feat(rddf-session): add --archive-orphans flag`)中,但缺乏显式文档。

此外,5 个顺序归档导致 master 落后 5+ commits,每次都需要 no-ff merge,效率不高。

## 范围

**In Scope**:
- AGENTS.md / guide-ship SKILL.md 显式规则:
  - execute 阶段:worktree 内修改,**worktree 内 commit**(working tree)
  - archive 阶段:由 `archive_change_for_mode` 自动 merge + openspec archive
- 文档化 commit message 风格(参考 archive-history 的 `feat(<scope>): ...` 模式)
- 跨 worktree 批量归档策略(可选研究):
  - rebase 所有 worktree 到最新 master 后逐个 archive
  - 或批量 no-ff merge 优化

**Out of Scope**:
- 修改 archive.sh 核心逻辑
- 修改 git worktree 行为

## 设计

### 显式规则(写入 AGENTS.md + guide-ship SKILL.md)

```markdown
## Worktree Commit Flow

每个 change 在 worktree 内执行时:

1. **Phase 2 execute**:修改文件 + 运行测试 + 更新 plan checkboxes (-[ ] → -[x])。
   不逐任务 commit(遵循现有约定 — 仓库的 commit 集中在 archive 阶段)。

2. **Phase 2 完成(全部 task 通过后)**:用 conventional commit 在 worktree 内 commit working tree:
   - `feat(<scope>): <description>` for new features
   - `fix(<scope>): <description>` for bug fixes
   - `test(<scope>): <description>` for test changes
   - `chore(<scope>): <description>` for tooling changes

   参考 `archive-history-keep-semantics` 的 commit `50950c5` 风格。

3. **Phase 3 archive**:由 `skills/guide-ship/scripts/ship_archive.sh::archive_change_for_mode`
   自动 merge → openspec archive → cleanup worktree/branch。
```

### 批量归档优化(可选)

研究方案:
- 所有 worktree rebase 到最新 master(若 worktree 内有 commits)
- `archive_change` 接受 `--skip-rebase` 选项(默认 off,仅批量场景启用)
- 减少顺序归档的 merge 开销

## 影响

- **正向**: 新用户/agent 不会困惑于 "execute 不 commit 但 archive 需要 commits" 的矛盾
- **正向**: 批量归档可减少 master 落后 commits 数
- **风险**: rebase 操作可能引入冲突(需 worktree 协调)
- **兼容性**: 不破坏现有 execute/archive 流程,仅文档化 + 优化

## 验收

- AGENTS.md 含"Worktree Commit Flow"小节
- guide-ship SKILL.md Phase 1.5 显式提到"worktree 内 commit working tree"
- 5 个新执行 change 按规则正确 commit(全部 archive 成功)
- 批量归档策略(若实施)减少总耗时 30%+