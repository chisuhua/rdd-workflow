## Why

当前 guide-plan 采用"全量创建 → 单次 deps → plan-done → 全部交接 guide-ship"的瀑布式批处理模式。在实际多阶段 roadmap 场景中，团队经常需要在 **Phase 1 先定义所有 change 骨架和依赖关系**，但**只对前几个高优先级 change 填充完整内容**并执行，等它们完成后（guide-ship archive），再根据依赖图选择下一批骨架进行填充。当前架构的 plan-done 双重门控（所有 change 的全部 artifacts 必须已提交）和 `openspec new change` 的全量创建模式阻断了这一渐进规划工作流。

## What Changes

- **新增 change 生命周期状态 `planned`**：表示骨架已创建（只有目录 + roadmap-meta.yaml + 最小 proposal.md），尚未填充 design.md/tasks.md
- **propose 新增 `--skeleton` 模式**：支持仅创建 change 骨架（`openspec new change` + roadmap-meta.yaml + 最小 proposal.md），跳过 design.md/tasks.md 的生成
- **guide-plan 新增 Phase 2.5 `fill`**：对已存在的 `planned` 状态 change，按 deps 推荐的执行顺序，调用 openspec 命令序列填充 design.md + tasks.md，将其升级为 `proposed` 状态
- **guide-plan Phase 4 plan-done 门控放宽**：允许部分 change 处于 `planned` 状态（已提交骨架 artifacts），部分处于 `proposed` 状态（已提交完整 artifacts）
- **deps 支持骨架 change 的预分析**：对仅含 proposal.md 的 `planned` change，仍可在 deps 中基于 proposal.md 的 scope/ADR 引用进行三轴依赖检测
- **guide-ship archive 后触发 `planned→proposed` 转换建议**：change 归档完成后，自动扫描 iteration.json，找出所有 blocker 已解除的 `planned` change，建议用户调用 `guide-plan fill` 填充下一个
- **`proposal-suggestions.md` 支持中间态**：条目 status 增加 `skeleton` 值，与 `待创建`/`进行中`/`已完成` 区分

## Capabilities

### New Capabilities
- `skeleton-planning`: change 骨架生命周期管理（`planned` 状态、骨架创建、渐进填充、骨架 deps 预分析）
- `iterative-plan-fill`: guide-plan 新增 fill 阶段，支持基于 deps 依赖图的渐进式 change 内容填充

### Modified Capabilities
- `three-phase-skills`: guide-plan 阶段状态机扩展（新增 fill 子阶段），plan-done 门控放宽为允许 part-planned + part-proposed 混合状态
- `state-management`: iteration.json schema 新增 `planned` status，proposal-suggestions.md schema 新增 `skeleton` status
- `roadmap-planning`: roadmap-meta.yaml 的 category_validation logic 适配骨架 change（骨架不需要完整设计文档即可通过分类验证）

## Impact

| 模块 | 影响 |
|------|------|
| `skills/propose.md` | Phase 4 新增 `--skeleton` 分支；Phase 5 提交逻辑适配骨架 artifacts |
| `skills/guide-plan.md` | Phase 2 后新增 Phase 2.5 fill；Phase 4 plan-done 门控新增部分骨架允许路径 |
| `skills/deps.md` | Step 1 骨架 change artifacts 读取容错（允许 design.md/tasks.md 不存在）；Step 5 输出标注骨架 change |
| `skills/guide-ship.md` | Phase 3 archive 完成后新增 planned→proposed 转换触发逻辑 |
| `skills/status.md` | Mode A/E 支持 `planned` 状态展示 |
| `skills/_lib/iteration.py` | `create_empty` / `add_or_update_change` 支持 `planned` status |
| `skills/_lib/schemas/iteration_schema.json` | status enum 添加 `"planned"` |
| `skills/_lib/schemas/deps_analysis_schema.json` | 新增 `skeleton` 标记字段 |
| `docs/adr/` | 新增 ADR-0013 记录增量骨架规划的设计决策 |