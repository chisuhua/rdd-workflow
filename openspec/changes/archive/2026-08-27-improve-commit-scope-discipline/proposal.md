# improve-commit-scope-discipline

## Why

2026-08-27 ship sync-package-skills-to-disk 时,使用 `git add -A` 暂存所有改动,导致 commit 中混入了:

- 3 个 pre-existing dirty 文件(README.md, USAGE.md, AGENTS.md,worktree 之前的 dirty 状态)
- 2 个意外空文件(`.gitignorebash`, `python3`,均为 0 字节,某次外部工具创建)

后果:

- 第一次 commit 包含 17 个文件,其中 5 个不是 ship scope。
- 需要 `git reset --soft HEAD~1` + 重新 stage 精确文件 + 重做 commit,浪费 3 步操作。
- commit 8 个文件是有效 ship scope,12 个文件(包括新增 `.rddf/plans/`)是 pollution。

期望行为: 禁止在非干净工作树中使用 `git add -A`。要么先 commit/stash pre-existing dirty,要么用精确文件列表 add。

## What Changes

**In Scope**:

- `guide-ship` Phase 2 在执行 `git add -A` 之前,运行 `git status --porcelain | grep -v "^??"` 检查非 untracked 改动:
- 如果有 pre-existing dirty → 警告并要求 user 决策
- 默认行为改为提示"建议用精确 git add <files>"
- 新增 `git_safety_check.sh` helper 函数,在所有 ship 相关 commit 前调用。

### 关键场景

- GIVEN 工作树包含 pre-existing dirty 文件(README.md modified)
  WHEN `guide-ship` Phase 2 准备 commit
  THEN 警告"工作树不干净,建议先 stash 或 commit 这些改动",列出 dirty 文件

- GIVEN 工作树只有当前 change 的 staged + untracked (specs/) 文件
  WHEN `git_safety_check.sh` 运行
  THEN PASS,允许 commit

**Out of Scope**:

- 修改 git 本身的 `git add -A` 行为(不可能)。
- 强制 git clean(可能丢失未保存改动)。
- 修改 commit message 格式(已有 conventional commit)。

## Capabilities

- MUST: 不破坏现有正常 ship flow(完全干净的工作树必须 PASS)
- MUST: 不阻止 commit(只是 WARNING,user 可选 --force-continue)
- SHOULD: 提供 `STRICT_COMMIT_SCOPE=yes` env var 升级 WARNING 为 block

## Impact

- MUST NOT: 修改 git config 或 hooks

## Acceptance

- [ ] `git_safety_check.sh` 实现,检测 pre-existing dirty + untracked
- [ ] `guide-ship` Phase 2 execute 步骤前调用 safety check
- [ ] 新增 unit test 覆盖 3 个 scenarios:
  - clean → PASS
  - pre-existing dirty → WARNING
  - untracked (合法) → PASS
- [ ] `STRICT_COMMIT_SCOPE=yes` 环境变量升级 WARNING → ERROR
- [ ] `guide-ship/SKILL.md` 文档更新
- [ ] 不修改 git config / hooks

