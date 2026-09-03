# ADR-0039: design-handoff runtime filter over on-disk cleanup

> **状态**: 已采纳 (2026-09-01)
> **日期**: 2026-09-01
> **决策者**: sisyphus

## Status
已采纳 (2026-09-01, fix-plan-intake-stale-pre-created-changes P1)

## Context

`.rddf/state/.design-handoff.json` v2 schema 包含 `changes_pre_created: [name, ...]` 字段。该字段在 `guide-design` Phase 5 落盘，描述 design 阶段批准并已直接创建 openspec/changes/<name>/ 的 change 名字，供 `guide-plan` Phase 0 intake 消费（跳过重复 propose）。

**问题**：`changes_pre_created` 一旦落盘后**永不过期**。后续 plan/ship 把这些 change 执行并归档到 `openspec/changes/archive/`，但 design-handoff.json 从不被 archive 阶段触达。

**下游症状**：2026-09-01 session 中，`plan_intake.sh` 报告
```
✅ design-done handoff 已验证 (v2 schema, 19 个预建 changes)
```
但这 19 个全部已归档。AI agent 看到名字后盲目调用 `propose --create`，被 propose 的幂等保护兜住，但体验严重退化。

## Decision

**设计/执行阶段分离 + 运行时过滤**：
- **不**修改 design-handoff.json v2 schema（保留历史审计线索）
- **不**在 archive 阶段清理 changes_pre_created（保留 design/执行阶段边界）
- **在 plan_intake 运行时**对 changes_pre_created 做归档/创建过滤

实现层：
- `plan_intake.sh::count_pending_proposals()`：Python 一次性计算 proposal-approved.md 中真正待创建的提案数（排除已实施区 + 已创建 + 已归档）
- `plan_intake.sh::classify_pre_created_changes()`：Python 一次性分类 changes_pre_created 为 pending/active/archived 三类
- `plan_intake.sh::is_design_pre_created_pending()`：name 在数组且未创建未归档时返回 0（用于下游消费）
- 输出新格式：`📋 待创建 proposal: N` + `(v2 schema, K 个预建 changes: P 待处理, A 已创建, M 已归档)`

## Alternatives Considered

1. **archive 阶段清理 changes_pre_created**
   - 拒绝原因：破坏 design/执行阶段边界；archive 不知道 design 的审计语义；可能误删设计阶段记录的"曾经预建过哪些 change"的信息

2. **v3 schema 引入 `archived_at` 字段**
   - 拒绝原因：向后不兼容；需要迁移所有现存 v2 handoff；与 v2 短生命周期设计不匹配

3. **保留 v2 schema 但加 `stale_after` 字段**
   - 拒绝原因：仍需消费者按时间过滤；增加复杂度但未解决根问题

4. **运行时过滤（采纳）**
   - 优点：纯前向兼容；不破坏设计/执行边界；用 ~10ms Python 计算换取精确状态
   - 缺点：每次 plan_intake 多一次磁盘扫描（可接受，< 50ms）

## Consequences

- ✅ AI agent 决策不再被过期 changes_pre_created 误导
- ✅ plan_intake 第一屏真实反映"待处理"状态
- ✅ 设计/执行阶段边界保持（archive 不触达 design handoff）
- ⚠️ `is_design_pre_created` 与 `is_design_pre_created_pending` 两个 helper 并存（前者向后兼容；后者用于"真正待处理"判断）
- ⚠️ `changes_pre_created` 内部数组保留全部历史名字（不删）；展示层做分类，但下游消费者需要明确选择用哪个 helper

## Implementation

- `skills/guide-plan/scripts/plan_intake.sh`：新增 3 个 helper
- `tests/integration/test_plan_intake_archived_filtering.bats`：14 个新测试
- `tests/integration/test_plan_intake_edges.bats`：1 个测试更新（grep 模式从"已批准提案"改为"待创建 proposal"）

## References

- 提案：`.rddf/improvements/fix-plan-intake-stale-pre-created-changes.md`
- 关联 ADR：ADR-0016 (arch 发现契约) — design handoff v1 字段定义
- 关联 ADR：ADR-0025 (design 阶段独立化) — design-handoff 所有权迁移到 guide-design
