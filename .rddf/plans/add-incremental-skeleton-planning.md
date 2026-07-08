# 实施计划: add-incremental-skeleton-planning

> 对应 ADR-0013（待创建）: Incremental Skeleton Planning
> 基于: tasks.md 中的 7 组 22 任务
> 实施位置: `.rddf/wt/add-incremental-skeleton-planning/`

## 概览

| 阶段 | 任务组 | 工作量 | 风险 |
|------|--------|--------|------|
| Schema 与状态基础设施 | 1.1-1.5 | 5 任务 | 低（schema 变更） |
| Propose 骨架模式 | 2.1-2.4 | 4 任务 | 中（影响扫描逻辑） |
| Guide-Plan Fill 阶段 | 3.1-3.4 | 4 任务 | 中（门控放宽） |
| Deps 骨架容错 | 4.1-4.5 | 5 任务 | 中（混合分析） |
| Guide-Ship Archive 触发 | 5.1-5.4 | 4 任务 | 低（只读扫描） |
| Status 模式适配 | 6.1-6.3 | 3 任务 | 低 |
| ADR 与文档 | 7.1-7.3 | 3 任务 | 低 |

## 实施策略

**按依赖顺序分组**：1 → 2 → 3 → 4 → 5 → 6 → 7

每个任务组完成后立即运行对应的单元测试 + 集成测试。

## 关键文件

| 文件 | 操作 | 来源任务 |
|------|------|---------|
| `skills/_lib/schemas/iteration_schema.json` | MODIFY | 1.1 |
| `skills/_lib/schemas/deps_analysis_schema.json` | MODIFY | 1.3 |
| `skills/_lib/iteration.py` | MODIFY | 1.2 |
| `skills/propose.md` | MODIFY | 2.1-2.3 |
| `skills/guide-plan.md` | MODIFY | 3.1-3.3 |
| `skills/deps.md` | MODIFY | 4.1-4.4 |
| `skills/guide-ship.md` | MODIFY | 5.1-5.3 |
| `skills/status.md` | MODIFY | 6.1-6.2 |
| `docs/adr/ADR-0013-incremental-skeleton-planning.md` | CREATE | 7.1 |
| `skills/guide.md` | MODIFY | 7.2 |
| `tests/unit/test_iteration.py` | MODIFY | 1.4 |
| `tests/integration/test_propose_skeleton.bats` | CREATE | 2.4 |
| `tests/integration/test_guide_plan_fill.bats` | CREATE | 3.4 |
| `tests/integration/test_deps_skeleton.bats` | CREATE | 4.5 |
| `tests/integration/test_guide_ship_archive_hook.bats` | CREATE | 5.4 |
| `tests/integration/test_status_planned.bats` | CREATE | 6.3 |

## 实施步骤

按 tasks.md 的顺序逐项实施，每个任务完成后立即 commit。

## 验收标准

1. `propose --skeleton` 创建 change 仅写入 `.openspec.yaml` + `roadmap-meta.yaml` + `proposal.md`
2. `iteration.json` 的 `status` 字段支持 `"planned"` 值
3. `guide-plan` Phase 2.5 fill 阶段可填充骨架 change
4. `deps` 对混合 planned+proposed change 输出正确
5. `guide-ship` archive 后输出 fill 建议
6. `status` Mode E 显示 planned 状态分组
7. ADR-0013 创建完成
8. 所有 unit + integration 测试通过