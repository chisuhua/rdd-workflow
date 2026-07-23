# auto-skip-archived-proposals

**优先级**: P0 | **来源**: 会话复盘 2026-07-23 — 43 个已归档提案全部重新审查
**阶段**: v2.1 | **分类**: performance
**类型**: feature

## 架构依据

- arch Phase 5.5 审批时，43 个提案中全部 43 个已归档（ALREADY_DONE），Oracle 审查了已无实际价值
- 应在审批前自动检测 `openspec/changes/archive/` 中已存在的 change
- 对已归档提案自动标记为"已完成"并跳过 Oracle，仅对真正未实施的提案发起审查

## 范围

- **In Scope**:
  - `guide-arch/scripts/approve_proposal.sh` 或 Phase 5.5 入口增加 archive 检测
  - 自动检查 `openspec/changes/archive/<date>-<name>/` 是否存在
  - 已归档的提案自动追加到 proposal-approved.md 的 `## 已实施` 表格
  - 输出汇总：`N 个已归档自动批准 | M 个待审查`
- **Out Scope**:
  - 不修改 Oracle 审查逻辑
  - 不修改提案文件格式

## 关键场景

- GIVEN improvements/xxx.md 对应的 change 已在 archive/, WHEN arch Phase 5.5 执行, THEN 自动标记为已完成并跳过审查
- GIVEN 10 个提案中 8 个已归档, WHEN Phase 5.5 扫描, THEN 仅展示 2 个待审查提案

## 技术约束

- MUST 检测 archive 目录命名模式 `20\d{2}-\d{2}-\d{2}-<name>`
- MUST 保留手动审查选项（用户可选择查看已归档提案的详情）
- SHOULD 输出清晰：区分"自动批准（已归档）"和"Oracle 审查通过"

## 验收标准

- 43 个已归档提案自动跳过审查（减少 100% 的无效 Oracle 调用）
- 仅真正待实施的提案进入 Oracle 审查
- 汇总输出包含自动批准数量
