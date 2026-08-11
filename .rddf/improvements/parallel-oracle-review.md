# parallel-oracle-review

**优先级**: P1 | **来源**: 会话复盘 2026-07-23 — arch Phase 5.5 Oracle 审查串行瓶颈
**阶段**: v2.1 | **分类**: performance
**类型**: feature

## 架构依据

- 当前 arch Phase 5.5 按优先级分三次调用 Oracle（P0 → P1 → P2），每次 1-5 分钟，串行总耗时 ~10 分钟
- 三次 Oracle 调用之间完全独立（审查不同优先级的提案），无数据依赖
- 如果并行发起 3 次 Oracle 调用，总耗时可压缩到单次最长调用时间（~5 分钟）

## 范围

- **In Scope**:
  - `guide-arch/SKILL.md` Phase 5.5 中增加并行审查选项：用户选择"全部审查"时，P0/P1/P2 三组同时调用 Oracle
  - 结果汇总展示：三组完成后统一输出审批建议
  - 保持现有的"按优先级逐个审查"作为备选模式
- **Out Scope**:
  - 不修改 Oracle 的审查逻辑本身
  - 不引入自动批准机制

## 关键场景

- GIVEN arch Phase 5.5 有 40+ 提案待审查, WHEN 用户选择"并行审查", THEN P0/P1/P2 三组同时发起 Oracle 调用
- GIVEN 并行审查完成, WHEN 展示结果, THEN 统一表格汇总三组审批建议

## 技术约束

- MUST 使用已有 `task(subagent_type="oracle", run_in_background=true)` 机制
- MUST 保持现有"按优先级逐个审查"模式不变
- SHOULD 三组审查的 prompt 模板一致

## 验收标准

- `guide-arch` Phase 5.5 新增"并行审查"选项
- 并行发起 3 次 Oracle 时不产生数据竞争
- 结果汇总表格正确合并三组输出
