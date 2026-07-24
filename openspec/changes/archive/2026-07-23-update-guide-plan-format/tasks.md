# Tasks: update-guide-plan-format

## Implementation Steps

- [ ] 更新 `skills/guide-plan/SKILL.md` Phase 1 scan 代码块
  - 从 `json.load(proposal-suggestions.md)` 改为读取 `proposal-approved.md` 表格
  - 使用 `grep`/`sed` 解析 Markdown 表格
- [ ] 更新 Phase 2 propose 候选展示代码块
  - 从 JSON 解析改为 Markdown 表格解析
  - 使用 `grep '^|'` + `tail -n +3` 跳过表头
- [ ] 更新 Phase 2.5 fill 的 suggestion 读取
  - 改为 `improvements/` 文件扫描
  - 替代 JSON 条目查找
- [ ] 更新"职责边界"描述
  - 移除 proposal-suggestions.md 属于 plan 端的说明
  - 更新消费者列表与实际一致

## Verification (验收标准)

- [ ] guide-plan SKILL.md 中无 `json.load(proposal-suggestions.md)` 引用
- [ ] Phase 2 代码块示例使用 `grep`/`sed` 解析 Markdown 表格
- [ ] 文档中的消费者列表与实际一致

## Key Scenarios (关键场景)

- [ ] GIVEN 开发者阅读 guide-plan SKILL.md, WHEN 看到 Phase 2 代码示例, THEN 示例使用 Markdown 表格解析而非 `json.load`
- [ ] GIVEN AI 被分配 guide-plan 任务, WHEN 按照文档执行, THEN 代码块可直接运行
