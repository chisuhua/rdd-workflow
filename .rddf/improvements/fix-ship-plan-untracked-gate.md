# fix-ship-plan-untracked-gate

**优先级**: P1 | **来源**: 2026-08-27 ship audit (3 P1 docs-consistency changes ship)
**阶段**: default | **分类**: governance
**类型**: improvement

**主题**: 2026-08-26 文档与代码一致性审计后续修复

## 架构依据

`skills/guide-ship/scripts/ship_plan.sh` 中的 `check_artifacts_committed` 函数使用 `git status --porcelain "$change_dir/"` 检查 working tree 是否有未提交改动。这个判断**过度严格**:它把 `untracked` 文件(如 `openspec/changes/<name>/specs/<capability>/spec.md`)也当作"未提交修改"拒绝,要求先 commit 才能创建 worktree。

后果:

- 2026-08-27 ship 3 个 P1 change 时,`specs/` 子目录是新 untracked 的(为 `openspec validate` 准备),worktree 创建失败并提示"请先 commit"。
- 实际修复方式: 先手工 `git add` 一个无关的 `chore(specs): add openspec validate specs/ for 2 remaining active changes` commit,才能创建后续 worktree。
- 这是 worktree 阶段的不必要阻塞 — `untracked` 文件是预期的 ship 准备状态,不是污染。

期望行为: `check_artifacts_committed` 应只检查**已 tracked 文件**的 modification,而不拒绝 untracked 文件(后者可能是 ship 阶段的合法新增)。

## 范围

**In Scope**:

- `check_artifacts_committed` 改用 `git status --porcelain <tracked_files>` 或类似方法,排除 untracked 干扰。
- 区分"tracked modification"(真实污染) vs "untracked addition"(合法新增) vs "deleted"(不阻塞)。
- 文档更新: `guide-ship/SKILL.md` Phase 1 的 COMMIT GATE 说明。

**Out of Scope**:

- 修改 `git add -A` 的默认行为(已经修复 `improve-commit-scope-discipline` 提案)。
- 改变 worktree 创建机制本身。

## 关键场景

- GIVEN `openspec/changes/<name>/{proposal.md, design.md, tasks.md, .openspec.yaml}` 已 commit,`specs/<capability>/spec.md` 是新 untracked
  WHEN `check_artifacts_committed <project_root> <name>` 调用
  THEN 返回 0 (exit OK),不阻塞 worktree 创建

- GIVEN `openspec/changes/<name>/proposal.md` 有 uncommitted modification (tracked file dirty)
  WHEN `check_artifacts_committed <project_root> <name>` 调用
  THEN 返回 1 (exit FAIL),要求先 commit 或 reset

## 技术约束

- MUST: 仍阻塞 tracked 文件的 modification(防止 ship 半成品)
- MUST: 不阻塞 untracked 文件(可能是 ship 阶段新增的合法文件)
- MUST NOT: 完全放弃 pre-flight 检查(否则 `git worktree add` 会失败)
- SHOULD: 提供 `--strict-untracked` flag 兼容极端场景(把所有 untracked 当作污染)
- SHOULD: 在 stderr 输出明确指出"tracked dirty" vs "untracked addition" 的区别

## 验收标准

- [ ] `check_artifacts_committed` 重构,只检查 tracked files 的 `M`/`D` 状态,忽略 `??`(untracked)
- [ ] 新增 unit test 覆盖 3 个场景:
  - tracked modification → FAIL
  - untracked addition → PASS
  - clean → PASS
- [ ] `--strict-untracked` flag 在 `guide-plan` / `guide-ship` 入口作为 opt-in
- [ ] 删除历史 workaround commit `13ad3ba chore(specs): add openspec validate specs/ for 2 remaining active changes` (合并到新的归档操作内)
- [ ] `guide-ship/SKILL.md` COMMIT GATE 段更新解释新行为

## 相关

- 关联: `improve-commit-scope-discipline` (本会话同组提案)
- 来源: 2026-08-27 全链路工作流审计
- 文件: `skills/guide-ship/scripts/ship_plan.sh` `check_artifacts_committed` 函数
