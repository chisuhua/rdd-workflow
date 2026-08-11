# agent-completion-contract

**优先级**: P1 | **来源**: Session 复盘 2026-07-21
**阶段**: v2.1 | **分类**: planning
**类型**: feature

## 架构依据
- 复盘发现：8 个 deep agent 中仅 3 个完成了完整的自清理（archive 目录 + iteration sync + worktree/branch 删除）
- 5/8 个 agent 需要手动介入清理残留 worktree 或归档目录

## 范围
- **In Scope**:
  - 在 guide-ship 的 Agent 任务 prompt 模板中增加明确的完成契约清单（3 项强制验收点）
  - 新增 `verify-agent-completion.sh` — orchestrator 在每个 agent 完成后运行，检查 archive 目录存在、iteration.json 已 sync、worktree 已删
  - 失败时输出警告并尝试自动修复（force-remove worktree、补写 iteration 条目）
  - 2 个 bats 测试：三契约全部通过、一项失败时的修复行为
- **Out Scope**:
  - 不修改 agent 框架本身（prompt 模板变更即可）

## 关键场景
（无）

## 技术约束
（无）

## 验收标准
- prompt 模板包含 3 项完成契约
- verify 脚本能检测并修复缺失的清理步骤
- 2 个 bats 测试通过
