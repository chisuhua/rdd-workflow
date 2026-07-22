## Context

**背景**: - README.md 前置条件:bats-core 1.10+ 是测试基础设施
- USAGE.md §3 描述测试驱动开发
- 9 个 skill 全部无 bats 单元测试(高风险回归)

**当前状态**: rdd-workflow 项目当前阶段,需要为后续实施奠定基础。

**约束**:
- MUST 使用 bats-core 1.10+
- MUST 不修改 skill 文件的元数据
- MUST 与现有测试目录结构对齐

## Goals / Non-Goals

**Goals:**
In Scope**:
  - 为 skills/*.md 中的每个 skill 添加 bats 测试文件
  - 测试覆盖:9 个 skill(INSTALL, deps, execute, guide, guide-ship, guide-spec, propose, roadmap, status)
  - 在 tests/ 下建立 _lib 共享辅助函数
- **

**Non-Goals:**
Out Scope**:
  - 不修改 skill 内容本身
  - 不替换 bats 框架

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
