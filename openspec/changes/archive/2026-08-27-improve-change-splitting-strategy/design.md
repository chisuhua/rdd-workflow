# improve-change-splitting-strategy — Design

## Context

2026-08-27 同时 ship `sync-package-skills-to-disk`(改 AGENTS.md line 72/118) 和 `sync-agents-md-five-stage`(改 AGENTS.md line 84/148/159)。
两个 change **共享同一个文件 AGENTS.md**,导致 ship 期间:

- 第 1 个 change commit 后,第 2 个 change 的 worktree 中的 AGENTS.md 已经包含了第 1 个 change 的修改(因为 worktree 从 master 创建)。
- 第 2 个 change 的 commit 时,如果不精确 patch,会把第 1 个 change 的内容也带进去(`git add -A` 污染案例)。

## Goals / Non-Goals

**Goals:**
- `guide-design` Phase 2 增加检测: 待审查 proposals 之间是否有共享文件修改(从 `.rddf/improvements/*.md` 的 ## 范围节 grep 文件路径)。
- 如果有冲突,提示用户:
- 合并为单一 change,或
- 强制串行 ship
- `guide-ship` 在 worktree 创建后,run `git diff main -- <file>` 显示冲突文件,要求 user 确认 patch 边界。

**Non-Goals:**
- 自动合并 proposals(高风险,需 user 决策)
- 修改 AGENTS.md 模板拆分

## Decisions

### 1. MUST: 检测基于 `.rddf/improvements/*.md` 的 ## 范围节,不是 proposal.md(已 commit 时才可读)

Implementation MUST satisfy this constraint.

### 2. MUST: 检测结果作为 WARNING 输出,不阻断 ship

Implementation MUST satisfy this constraint.


## Risks / Trade-offs

- No identified risks beyond standard implementation discipline.

- **SHOULD**: SHOULD: 提供 `--strict-change-split` flag,启用时阻断冲突 ship