# unify-session-kind-naming

**优先级**: P0 | **来源**: 改进分析报告 #3
**阶段**: default | **分类**: api-design
**类型**: feature

## 架构依据
（无）

## 范围
- In Scope:
  - 方案 A：统一为 `guide-arch` / `guide-plan` / `guide-ship`（与 skill 名称一致）
  - 方案 B：在 _VALID_KINDS 同时接受两种命名
  - 更新所有现有代码和测试
- Out Scope:
  - 不修改 ADR 或文档中的术语定义

## 关键场景
（无）

## 技术约束
（无）

## 验收标准
- 用户可用直觉命名的 kind 参数
- 所有测试通过
