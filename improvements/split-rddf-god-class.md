# split-rddf-god-class

**优先级**: P2 | **来源**: .omo/plans/rddf-session-improvement-plan.md — W2-1
**阶段**: v2.1 | **分类**: refactor
**类型**: refactor-only

## 架构依据
- RddfSessionCoordinator 507 行，自认 god class
- 拆分方案: facade + _store.py + _commands.py + _binding.py + _types.py

## 范围
- **In Scope**:
  - 拆分 RddfSessionCoordinator 为 5 个模块
  - facade 保留全部公共方法签名不变
  - 所有现有调用点不受影响
- **Out Scope**:
  - 不修改 schema validation（已在 W0-1 修复）
  - 不修改会话数据模型

## 关键场景
（无）

## 技术约束
（无）

## 验收标准
- 所有现有 24+10 测试通过（回归）
- lsp_find_references 验证无遗漏调用点
