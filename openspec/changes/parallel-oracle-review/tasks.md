# Tasks: parallel-oracle-review

## Implementation Steps

- [ ] 在 `skills/guide-arch/SKILL.md` Phase 5.5 增加审查模式选择菜单
  - 选项 1: 按优先级逐个审查（当前模式）
  - 选项 2: 并行审查（P0/P1/P2 同时发起）
- [ ] 实现并行审查逻辑
  - 按 P0/P1/P2 分组提案
  - 对每组发起 `task(subagent_type="oracle", run_in_background=true)`
  - 三组使用相同的 prompt 模板
- [ ] 实现结果汇总
  - 等待三个 background task 全部完成
  - `background_output` 收集三组结果
  - 统一表格输出审批建议
- [ ] 保持"按优先级逐个审查"模式不变
  - 现有逻辑作为备选，不修改

## Verification (验收标准)

- [ ] `guide-arch` Phase 5.5 新增"并行审查"选项
- [ ] 并行发起 3 次 Oracle 时不产生数据竞争
- [ ] 结果汇总表格正确合并三组输出

## Key Scenarios (关键场景)

- [ ] GIVEN arch Phase 5.5 有 40+ 提案待审查, WHEN 用户选择"并行审查", THEN P0/P1/P2 三组同时发起 Oracle 调用
- [ ] GIVEN 并行审查完成, WHEN 展示结果, THEN 统一表格汇总三组审批建议
