# plan-execute-commit-policy-consistency

**优先级**: P1 | **来源**: Session 复盘 2026-08-04 — 三 change guide-ship 全流程
**阶段**: v2.1 | **分类**: planning
**类型**: fix

## 架构依据
- 实测：`rdd-workflow-writing-plans` 生成的 plan 每个 Task 都有 Step 5 `git commit`，但 AGENTS.md 明确约定"execute 阶段不 commit/push — commit 留到 archive 阶段"
- 2026-08-04 会话执行 3 个 change 时被迫在 Execute 开始前向用户确认策略（"Defer commits to Archive"），plan 文件与仓库约定存在结构性矛盾
- 根因：plan 模板继承自 superpowers/writing-plans 的 TDD 5 步结构，未适配 rdd-workflow 的"commit 集中在 archive"约定

## 范围
- **In Scope**:
  - `rdd-workflow-writing-plans` 生成 plan 时根据执行策略调整 Step 5：默认输出"暂不 commit，留待 archive 阶段统一提交"的说明，或提供 `COMMIT_IN_EXECUTE=yes` 开关
  - AGENTS.md / execute SKILL.md 与 plan 模板的提交策略描述统一
  - 1 个 bats 测试：验证生成的 plan 在默认策略下不含 `git commit` 步骤（或含明确的 defer 提示）
- **Out Scope**:
  - 不改变 archive 阶段的提交逻辑（archive.sh 不变）
  - 不改变 TDD 5 步结构本身（仅调整 Step 5 内容）

## 关键场景
- **GIVEN** 用户运行 guide-ship 生成 plan
  **WHEN** 查看 `.rddf/plans/<name>.md` 的 Task Step 5
  **THEN** 默认显示"本 change 按仓库约定不逐任务 commit，execute 完成后统一在 archive 阶段提交"，不再与 AGENTS.md 冲突

## 技术约束
- 不得破坏 execute 技能现有的 tasks.md 回写与 TDD 纪律

## 验收标准
- 新生成的 plan 默认不含要求逐任务 `git commit` 的步骤（或含 defer 提示）
- 1 个 bats 测试锁定该行为
- 存量 plan（含本会话 3 个）不受影响
