## Context

**背景**: - docs/adr/ 目录不存在
- docs/proposal-suggestions-format.md 假设存在 ADR 引用
- 9 个 skill 中隐含架构决策未结构化记录

**当前状态**: rdd-workflow 项目当前阶段,需要为后续实施奠定基础。

**约束**:
- MUST 使用 bats-core 1.10+
- MUST 不修改 skill 文件的元数据
- MUST 与现有测试目录结构对齐

## Goals / Non-Goals

**Goals:**
In Scope**:
  - 创建 docs/adr/ 目录结构
  - 添加 ADR 模板(ADR-0000-template.md)
  - 编写首个 ADR(rdd-workflow 架构选型)
- **

**Non-Goals:**
Out Scope**:
  - 不迁移现有 skill 中的隐含决策
  - 不修改 proposal-suggestions-format.md 引用规则

## Decisions

### 决策 1: 使用 bats 作为测试框架
- **理由**: README.md 前置条件已声明 bats-core 1.10+
- **替代方案**: tap / shunit2 / 自研 → 选 bats 因其声明为依赖

### 决策 2: 每个 skill 一个独立 test.bats 文件
- **理由**: 与现有 tests/ 目录结构一致
- **替代方案**: 单文件多测试 → 拒绝,违反单一职责

## Risks / Trade-offs

- **风险**: bats 框架与 Markdown skill 的耦合度低 → **缓解**: 在 tests/_lib/ 提供 skill 加载辅助函数
- **权衡**: 测试覆盖范围 vs 维护成本 → 当前选择覆盖面优先
