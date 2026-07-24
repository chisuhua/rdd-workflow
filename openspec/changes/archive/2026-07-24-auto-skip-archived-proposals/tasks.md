# Tasks: auto-skip-archived-proposals

## Implementation Steps

- [ ] 在 `skills/guide-arch/scripts/approve_proposal.sh` 中新增 `check_archived()` 函数
  - 接收提案名参数
  - 用 glob 检测 `openspec/changes/archive/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-<name>` 模式
  - 返回 0=已归档，1=未归档
- [ ] 在 Phase 5.5 审批入口增加预过滤循环
  - 遍历待审查提案列表
  - 对每个提案调用 `check_archived()`
  - 已归档：调用 `mark_approved_completed` 追加到 `## 已实施` 表格
  - 未归档：收集到"待 Oracle 审查"列表
- [ ] 实现汇总输出
  - 格式：`N 个已归档自动批准 | M 个待审查`
  - 区分"自动批准（已归档）"和"Oracle 审查通过"
- [ ] 保留手动审查选项
  - 用户可选择查看已归档提案的详情（`--show-archived` 参数）
- [ ] 更新 `skills/guide-arch/SKILL.md` Phase 5.5 描述
  - 增加"自动跳过已归档提案"说明
  - 更新输出示例

## Verification (验收标准)

- [ ] 43 个已归档提案自动跳过审查（减少 100% 的无效 Oracle 调用）
- [ ] 仅真正待实施的提案进入 Oracle 审查
- [ ] 汇总输出包含自动批准数量

## Key Scenarios (关键场景)

- [ ] GIVEN improvements/xxx.md 对应的 change 已在 archive/, WHEN arch Phase 5.5 执行, THEN 自动标记为已完成并跳过审查
- [ ] GIVEN 10 个提案中 8 个已归档, WHEN Phase 5.5 扫描, THEN 仅展示 2 个待审查提案
