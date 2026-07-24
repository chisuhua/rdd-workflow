# Proposal: parallel-oracle-review

## Why

当前 arch Phase 5.5 按优先级分三次调用 Oracle（P0 -> P1 -> P2），每次 1-5 分钟，串行总耗时 ~10 分钟。三次 Oracle 调用之间完全独立（审查不同优先级的提案），无数据依赖。如果并行发起 3 次 Oracle 调用，总耗时可压缩到单次最长调用时间（~5 分钟）。

来源: 会话复盘 2026-07-23

## What Changes

- `guide-arch/SKILL.md` Phase 5.5 中增加并行审查选项：用户选择"全部审查"时，P0/P1/P2 三组同时调用 Oracle
- 结果汇总展示：三组完成后统一输出审批建议
- 保持现有的"按优先级逐个审查"作为备选模式
- 不修改 Oracle 的审查逻辑本身
- 不引入自动批准机制

## Capabilities

### New Capabilities: parallel-oracle-review

在 arch Phase 5.5 新增"并行审查"选项，使用 `task(subagent_type="oracle", run_in_background=true)` 机制同时发起 P0/P1/P2 三组 Oracle 审查。结果汇总为统一表格。保持"按优先级逐个审查"作为备选模式。三组审查的 prompt 模板一致。

## Impact

**受影响文件:**
- `skills/guide-arch/SKILL.md` — Phase 5.5 增加并行审查选项

**不受影响:**
- Oracle 审查逻辑本身
- 自动批准机制（不引入）
