# guide-plan-noninteractive

**优先级**: P0 | **来源**: 复盘改进 #1 — guide-plan 无交互模式
**阶段**: v2.1 | **分类**: core
**类型**: feature

## 架构依据
- 复盘发现：guide-plan 是人际交互状态机（菜单+read），AI 编排器无法调用。propose_change.py 虽可用但绕过完整流程。

## 范围
- **In Scope**:
  - guide-plan.md 入口检测 `--non-interactive` 或 `SKIP_GUIDE_PLAN_MENU=yes` env var
  - non-interactive 模式跳过菜单，执行默认流程（scan→propose→deps→plan-done）
  - propose 增加 `--batch-create` 批量从 proposal-suggestions.md 创建 skeleton
  - 测试覆盖两种模式
- **Out Scope**:
  - 不修改人际交互菜单（向后兼容）
  - 不修改 guide-ship

## 关键场景
（无）

## 技术约束
（无）

## 验收标准
- `SKIP_GUIDE_PLAN_MENU=yes skill_use("guide-plan")` 自动执行完整 plan 流程
- `skill_use("propose", "--batch-create")` 创建所有 pending 建议的 skeleton
- 不影响现有交互体验
