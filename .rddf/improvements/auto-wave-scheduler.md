# auto-wave-scheduler

**优先级**: P0 | **来源**: 复盘改进 #3 + #4 — 自动 Wave 调度 + iteration 状态自动化
**阶段**: v2.1 | **分类**: core
**类型**: feature

## 架构依据
- 复盘发现：Wave 切换靠人工判断、iteration.json 状态转换手动操作。manual_deps 已有依赖数据，缺的是自动化消费方。

## 范围
- **In Scope**:
  - guide-arch/guide-plan/guide-ship 入口 hook 自动迭代状态转换（planned→proposed→in_worktree→archived）
  - archived hook 扫描 iteration.json 中 blocker 已解除的 planned change
  - 输出建议信息“bloker 已解除: change-x, change-y 可以执行”
  - 不影响现有 hook 行为
- **Out Scope**:
  - 不自动调用 guide-ship（仅建议，用户确认）
  - 不修改 DependencyScheduler（ADR-0010 v2.1 完整版留待后续）

## 关键场景
（无）

## 技术约束
（无）

## 验收标准
- 归档 change-a 后，若 change-b 的 manual_deps=[change-a]，自动打印“建议: change-b blocker 已解除”
- guide-plan 入口自动设 stage_plan session 状态
- 测试覆盖 archived→unblocked→suggest 链路
