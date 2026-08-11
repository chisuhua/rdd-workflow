# ship-delete-branch-safety

**优先级**: P1 | **来源**: 会话复盘 2026-07-23 — 分支删除导致 3 个 commit 丢失
**阶段**: v2.1 | **分类**: core
**类型**: feature

## 架构依据

- `git branch -D openspec/add-session-progress-view` 删除了包含 3 个关键 commit 的未合并分支
- 需通过 `git reflog` + `cherry-pick` 恢复（操作复杂且易出错）
- guide-ship Phase 4 删除分支时应先检查合并状态

## 范围

- **In Scope**:
  - guide-ship Phase 4 删除分支前调用 `git branch --merged master | grep openspec/<name>` 检查
  - 未合并时输出警告并列出未合并的 commit，要求用户二次确认
  - 支持 `FORCE_BRANCH_DELETE=yes` 跳过检查（与现有 archive.sh 一致）
- **Out Scope**:
  - 不修改 git 行为
  - 不修改现有的 `cleanup_worktree_and_branch` 函数签名

## 关键场景

- GIVEN 分支已合并到 master, WHEN 删除分支, THEN 正常进行
- GIVEN 分支未合并, WHEN 尝试删除, THEN 警告"分支含 N 个未合并 commit"并要求确认

## 技术约束

- MUST 在 `cleanup_worktree_and_branch` 或 ship Phase 4 中实现
- MUST 与现有 `FORCE_BRANCH_DELETE` 环境变量兼容
- SHOULD 列出未合并的 commit hash 和 subject

## 验收标准

- 未合并分支删除时被阻止并显示警告
- FORCE_BRANCH_DELETE=yes 可跳过
- 已合并分支正常删除