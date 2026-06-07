## Context

**背景**: - skills/deps.md:345:`<!-- TODO: 子代理语义分析尚未实现。当前仅执行 Step 2 静态分析。后续可由独立 change 实现完整 subagent 调用。 -->`
- docs/audit/2026-06-05-workflow-audit.md:490:L320 TODO 同源
- 3 处文档(deps.md L345/L499/L566)明确标注占位符待实现

**当前状态**: spec-workflow 项目当前阶段,需要为后续实施奠定基础。

**约束**:
- MUST 使用 bats-core 1.10+
- MUST 不修改 skill 文件的元数据
- MUST 与现有测试目录结构对齐

## Goals / Non-Goals

**Goals:**
In Scope**:
  - 在 skills/deps.md Step 3 实现子代理语义分析
  - 调用 subagent 读取各 change 的 proposal.md/design.md/tasks.md
  - 输出补充的依赖关系到 .zcf/.deps-output.md
- **

**Non-Goals:**
Out Scope**:
  - 不修改 Step 2 静态三轴分析逻辑
  - 不改 .zcf/.deps-candidates.json 格式

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
