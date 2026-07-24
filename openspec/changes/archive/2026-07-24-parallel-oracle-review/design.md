# Design: parallel-oracle-review

## Context

当前 arch Phase 5.5 按优先级分三次调用 Oracle（P0 -> P1 -> P2），每次 1-5 分钟，串行总耗时 ~10 分钟。三次 Oracle 调用之间完全独立，无数据依赖。并行可压缩到单次最长调用时间。

## Goals / Non-Goals

### Goals

- Phase 5.5 新增"并行审查"选项，P0/P1/P2 三组同时调用 Oracle
- 使用已有 `task(subagent_type="oracle", run_in_background=true)` 机制
- 结果汇总展示：三组完成后统一输出审批建议表格
- 保持"按优先级逐个审查"模式不变
- 三组审查的 prompt 模板一致

### Non-Goals

- 不修改 Oracle 审查逻辑本身
- 不引入自动批准机制

## Decisions

在 Phase 5.5 增加用户选择菜单：

```
审查模式:
  1) 按优先级逐个审查 (当前模式, P0 -> P1 -> P2)
  2) 并行审查 (P0/P1/P2 同时发起, ~5 分钟)
```

选择"并行审查"时：
1. 按 P0/P1/P2 分组提案
2. 对每组同时发起 `task(subagent_type="oracle", run_in_background=true)`
3. 等待三个 background task 全部完成
4. 汇总三组结果为统一审批建议表格

由于三组审查不同提案集，无共享状态，不产生数据竞争。

## Implementation

**关键修改文件:**

- `skills/guide-arch/SKILL.md` — Phase 5.5 增加并行审查选项
  - 新增用户选择菜单（逐个 vs 并行）
  - 并行模式：3 个 `run_in_background=true` 的 oracle task
  - 结果汇总：`background_output` 收集 + 统一表格输出
  - prompt 模板提取为共享变量，三组使用相同模板
