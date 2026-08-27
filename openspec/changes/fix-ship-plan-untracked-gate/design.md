# fix-ship-plan-untracked-gate — Design

## Context

`skills/guide-ship/scripts/ship_plan.sh` 中的 `check_artifacts_committed` 函数使用 `git status --porcelain "$change_dir/"` 检查 working tree 是否有未提交改动。
这个判断**过度严格**:它把 `untracked` 文件(如 `openspec/changes/<name>/specs/<capability>/spec.md`)也当作"未提交修改"拒绝,要求先 commit 才能创建 worktree。
后果:

- 2026-08-27 ship 3 个 P1 change 时,`specs/` 子目录是新 untracked 的(为 `openspec validate` 准备),worktree 创建失败并提示"请先 commit"。

## Goals / Non-Goals

**Goals:**
- `check_artifacts_committed` 改用 `git status --porcelain <tracked_files>` 或类似方法,排除 untracked 干扰。
- 区分"tracked modification"(真实污染) vs "untracked addition"(合法新增) vs "deleted"(不阻塞)。
- 文档更新: `guide-ship/SKILL.md` Phase 1 的 COMMIT GATE 说明。
- GIVEN `openspec/changes/<name>/{proposal.md, design.md, tasks.md, .openspec.yaml}` 已 commit,`specs/<capability>/spec.md` 是新 untracked
- GIVEN `openspec/changes/<name>/proposal.md` 有 uncommitted modification (tracked file dirty)

**Non-Goals:**
- 修改 `git add -A` 的默认行为(已经修复 `improve-commit-scope-discipline` 提案)。
- 改变 worktree 创建机制本身。

## Decisions

### 1. MUST: 仍阻塞 tracked 文件的 modification(防止 ship 半成品)

Implementation MUST satisfy this constraint.

### 2. MUST: 不阻塞 untracked 文件(可能是 ship 阶段新增的合法文件)

Implementation MUST satisfy this constraint.


## Risks / Trade-offs

- No identified risks beyond standard implementation discipline.

- **SHOULD**: SHOULD: 提供 `--strict-untracked` flag 兼容极端场景(把所有 untracked 当作污染)
- **SHOULD**: SHOULD: 在 stderr 输出明确指出"tracked dirty" vs "untracked addition" 的区别