# fix-plan-intake-stale-pre-created-changes

## Why

`plan_intake.sh` 误导性计数 + `.design-handoff.json` `changes_pre_created` 永不过期，导致 AI agent 把已归档 change 当作待创建。2026-09-01 session 实际触发：plan_intake 输出 "225 个已批准提案但无活跃 change"，agent 看到 `changes_pre_created` 19 个名字后盲目调用 `propose --create`，但这 19 个全部已归档到 `openspec/changes/archive/`。

## What Changes

### In Scope

- `plan_intake.sh::run_plan_intake` 修正 `PENDING_PROPOSALS` 计数：仅统计 `## 已实施` 分区**之前**且未创建、未归档的提案
- `plan_intake.sh::check_design_handoff` 读入 `CHANGES_PRE_CREATED` 后做归档过滤：分类展示待处理 / 已创建 / 已归档
- 新增 helper `is_design_pre_created_pending`（仅名字在数组且未创建未归档时返回 0）
- 导出 env vars `CHANGES_PENDING_COUNT` / `CHANGES_ARCHIVED_COUNT` 供下游展示层消费

### Out Scope

- 不修改 `.design-handoff.json` v2 schema
- 不在 archive 阶段触达 design handoff（保留设计/执行阶段边界）
- 不删除已归档 change 在 `changes_pre_created` 中的记录（审计价值）

## Capabilities

- MUST: `plan_intake` 真实反映「待创建」提案数（排除已归档/已创建）
- MUST: `check_design_handoff` 分类展示预建 changes
- MUST: 既有 `is_design_pre_created` helper 语义不变
- MUST NOT: 修改 `.design-handoff.json` v2 schema
- MUST NOT: 在 archive 阶段触达 design handoff

## Impact

- MUST: plan_intake 第一屏输出不再误导 AI agent
- MUST: v1 schema + SKIP_DESIGN_HANDOFF=yes + 空数组 三种兼容路径保持原行为
- SHOULD: AI agent 决策正确性提升
- MUST NOT: 引入新依赖
- MUST NOT: 改变 proposal-approved.md 文件结构

## Acceptance

- [ ] `./test.sh --quick` 全绿
- [ ] `./test.sh --unit` Python 单测全绿
- [ ] `./test.sh --bats` bats 全量无新增失败
- [ ] `run_plan_intake` 不再输出"X 个已批准提案但无活跃 change"误导
- [ ] 输出新格式：`✅ design-done handoff 已验证 (v2 schema, K 个预建 changes: P 待处理, M 已创建/已归档)`
- [ ] `is_design_pre_created` 既有 8 个测试全绿
- [ ] 4 个新增 bats 测试 + 2 个扩展测试 PASS
