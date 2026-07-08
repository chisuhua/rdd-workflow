# ADR-0013: Incremental Skeleton Planning

**Status**: 待定 → 已采纳（待 archive 后切换）
**日期**: 2026-07-08
**作者**: sisyphus (via dispatching-parallel-agents)
**evolved-from**: 部分灵感源自 ADR-0011（阶段步骤化执行模型）

## Context

当前 spec-workflow 的 change 生命周期是线性的：`propose（全量创建）→ deps（单次分析）→ plan-done（全部提交）→ guide-ship`。这种"瀑布式"批处理在多阶段 roadmap 场景中产生摩擦：

1. **多阶段 roadmap**: Phase 1 有 5 个 change，但只有前 3 个需要在当前 sprint 实现
2. **跨阶段依赖**: Phase 2 的 change 依赖于 Phase 1 的输出，但 Phase 1 尚未完成时无法确定 Phase 2 的完整设计
3. **渐进规划**: 团队希望先画出所有 change 的依赖关系图（骨架），再逐步填充每个骨架的细节

当前架构的硬约束（plan-done 双重门控、openspec 全量创建）使得以上场景只能通过创建完整 change 然后人为跳过来实现，失去了工具链的自动化支持。

## Decision

引入"骨架 change"概念：在 change 生命周期中新增 `planned` 状态，允许仅创建最小 artifacts（`.openspec.yaml` + `roadmap-meta.yaml` + 最小 `proposal.md`）即注册 change，后续按依赖关系渐进填充为完整 change。

具体实现包含 6 个关键决策：

### Decision 1: 新增独立 `planned` 状态
- 生命周期：`planned → proposed → in_worktree → review → completed → archived`
- `planned` 状态的 change 不进入 guide-ship 执行候选
- iteration.json schema enum 扩展为 `["planned", "proposed", "in_worktree", "review", "completed", "archived"]`，version 字段从 2 → 3

### Decision 2: 骨架 change 的最小 artifacts
- 骨架 = `.openspec.yaml` + `roadmap-meta.yaml` + 最小 `proposal.md`（只有 Why + What Changes）
- deps 可基于最小 proposal.md 的 scope/ADR 引用进行三轴分析
- 若完全没有 proposal.md，deps 三轴分析退化为空

### Decision 3: guide-plan fill 阶段
- guide-plan Phase 2 菜单新增「3. 填充骨架 change (fill)」
- 按 deps 推荐顺序（blocker 已清除者优先）填充 design.md + tasks.md
- 填充后状态 `planned → proposed`

### Decision 4: plan-done 门控放宽
- 允许 part-planned + part-proposed 混合状态通过
- 新增 Gate 0：至少 1 个 `proposed` 状态 change
- 仅 `planned` 无 `proposed` 仍失败

### Decision 5: deps 骨架容错
- 读取 change artifacts 时容错（缺失 design.md 不报错）
- 跳过接口依赖轴（Axis 3，需要 design.md）
- Mermaid 图中骨架 change 用 `[[name]]` 双括号标记
- Change 状态表新增 `备注` 列标识 skeleton

### Decision 6: guide-ship archive 后触发
- 归档完成后扫描 iteration.json 中 blocker 已解除的 planned change
- 输出建议信息（不自动调用 guide-plan fill）
- 用户始终需要显式确认填充

## Consequences

### 正面
- 支持多阶段 roadmap 的渐进规划
- 可在 sprint 开始前画出完整依赖图
- Phase 1 完成后自动提示填充 Phase 2 的骨架

### 负面
- 混合状态（planned + proposed）增加 plan-done 门控复杂度
- deps 对骨架的预分析精度低于完整分析（fill 后强制重跑）
- 骨架 change 可能被遗忘（status Mode E 持续展示 + archive 后主动提醒）

## Alternatives Considered

### Alternative A: 拆分 `proposed` 状态
- 不新增状态，将 `proposed` 分为 `proposed(skeleton)` 和 `proposed(complete)`
- **拒绝理由**: 现有 schema enum 强约束，扩展语义会导致下游解析复杂化

### Alternative B: 独立的 `guide-plan-fill` 子技能
- 把 fill 作为独立技能
- **拒绝理由**: fill 属于 plan 阶段内部操作，不应独立为阶段；增加用户学习成本

### Alternative C: 自动填充
- archive 后自动调用 guide-plan fill
- **拒绝理由**: 用户始终需要确认内容；自动填充可能在未准备时创建不准确 design.md

## Implementation Status

| Group | Description | Status |
|-------|-------------|--------|
| 1 | Schema 与状态基础设施 (iteration.py + iteration_schema.json) | ✅ 已采纳 |
| 2 | propose --skeleton 模式 (propose.md) | ✅ 已采纳 |
| 3 | guide-plan fill 阶段 (guide-plan.md) | ✅ 已采纳 |
| 4 | deps 骨架容错 (deps.md) | ✅ 已采纳 |
| 5 | guide-ship archive-fill 触发 (guide-ship.md) | ✅ 已采纳 |
| 6 | status Mode A/E planned 显示 (status.md) | ✅ 已采纳 |
| 7 | ADR-0013 文档 | ✅ 已采纳 |

## Related

- **ADR-0003**: 三阶段架构 (arch → plan → ship) — 本决策的架构依据
- **ADR-0007**: 门控机制 — plan-done 双重门控的设计依据
- **ADR-0011**: 阶段步骤化执行模型 — plan 阶段的子阶段设计
- **v3-scheduled-triggers**: 配套 change，LoopEngine 的触发器集成
