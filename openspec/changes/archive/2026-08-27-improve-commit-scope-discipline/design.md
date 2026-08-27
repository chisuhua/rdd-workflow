# improve-commit-scope-discipline — Design

## Context

2026-08-27 ship sync-package-skills-to-disk 时,使用 `git add -A` 暂存所有改动,导致 commit 中混入了:

- 3 个 pre-existing dirty 文件(README.md, USAGE.md, AGENTS.md,worktree 之前的 dirty 状态)
- 2 个意外空文件(`.gitignorebash`, `python3`,均为 0 字节,某次外部工具创建)

后果:

- 第一次 commit 包含 17 个文件,其中 5 个不是 ship scope。
- 需要 `git reset --soft HEAD~1` + 重新 stage 精确文件 + 重做 commit,浪费 3 步操作。
- commit 8 个文件是有效 ship scope,12 个文件(包括新增 `.rddf/plans/`)是 pollution。

## Goals / Non-Goals

**Goals:**
- `guide-ship` Phase 2 在执行 `git add -A` 之前,运行 `git status --porcelain | grep -v "^??"` 检查非 untracked 改动:
- 如果有 pre-existing dirty → 警告并要求 user 决策
- 默认行为改为提示"建议用精确 git add <files>"
- 新增 `git_safety_check.sh` helper 函数,在所有 ship 相关 commit 前调用。
- GIVEN 工作树包含 pre-existing dirty 文件(README.md modified)

**Non-Goals:**
- 修改 git 本身的 `git add -A` 行为(不可能)。
- 强制 git clean(可能丢失未保存改动)。
- 修改 commit message 格式(已有 conventional commit)。

## Decisions

### 1. MUST: 不破坏现有正常 ship flow(完全干净的工作树必须 PASS)

Implementation MUST satisfy this constraint.

### 2. MUST: 不阻止 commit(只是 WARNING,user 可选 --force-continue)

Implementation MUST satisfy this constraint.


## Risks / Trade-offs

- No identified risks beyond standard implementation discipline.

- **SHOULD**: SHOULD: 提供 `STRICT_COMMIT_SCOPE=yes` env var 升级 WARNING 为 block