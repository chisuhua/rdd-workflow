## Context

当前 spec-workflow 的 change 生命周期是线性的：`propose（全量创建）→ deps（单次分析）→ plan-done（全部提交）→ guide-ship`。这种"瀑布式"批处理在以下场景中产生摩擦：

1. **多阶段 roadmap**：Phase 1 有 5 个 change，但只有前 3 个需要在当前 sprint 实现，后 2 个只需记录依赖关系
2. **跨阶段依赖**：Phase 2 的 change 依赖于 Phase 1 的输出，但 Phase 1 尚未完成时无法确定 Phase 2 的完整设计
3. **渐进规划**：团队希望先在白板上画出所有 change 的依赖关系图（骨架），再逐步填充每个骨架的细节

当前架构的硬约束（plan-done 双重门控、openspec 全量创建）使得以上场景只能通过创建完整 change 然后人为跳过来实现，失去了工具链的自动化支持。

## Goals / Non-Goals

**Goals:**
- 支持 `planned` 状态：change 可以仅包含骨架信息（name + phase + category + 最小 proposal.md），不强制 design.md/tasks.md
- 支持骨架批量创建：一次性为 roadmap 的所有阶段创建 change 骨架，建立依赖关系图
- 支持渐进填充：guide-plan 新增 `fill` 阶段，按 deps 推荐顺序逐步将骨架升级为完整 change
- 支持混合状态：guide-plan 允许 part-planned + part-proposed 的混合状态通过 plan-done 门控
- deps 支持骨架预分析：对仅含 proposal.md 的骨架 change，仍可基于 scope/ADR 引用进行三轴检测
- guide-ship 完成后触发下一轮填充：archive 后自动扫描 iteration.json，建议用户调用 guide-plan fill

**Non-Goals:**
- 不修改 `openspec` CLI 的核心行为（骨架模式完全在 propose.md 层面实现）
- 不改变 guide-ship 的执行逻辑（ship 端只处理 `proposed` 状态的完整 change）
- 不实现自动填充（始终需要用户确认，避免 AI 自动创建不准确的 design.md）
- 不改变 `proposal-suggestions.md` 作为持久化候选列表的角色

## Decisions

### Decision 1: `planned` 状态 vs 扩展 `proposed`

**选择**: 新增独立状态 `planned`

**备选**: 将 `proposed` 状态扩展为 `proposed(skeleton)` 和 `proposed(complete)`

**理由**:
- `planned` 语义清晰区分"已规划但未设计" vs "已设计待实现"
- iteration.json schema 已有 enum 约束，新增状态比拆分现有状态更安全（向后兼容）
- roadmap.md AUTO-SPRINT 段可以过滤 `planned` 状态的 change 单独展示

### Decision 2: 骨架 change 的最小 artifacts

**选择**: 骨架 = `.openspec.yaml` + `roadmap-meta.yaml` + 最小 `proposal.md`（只有 Why 和 What Changes 章节，无 Capabilities/Impact 章节）

**备选**: 骨架 = 仅有 `.openspec.yaml` + `roadmap-meta.yaml`（无 proposal.md）

**理由**:
- proposal.md 的 "Why" 和 "What Changes" 两章提供了依赖分析所需的最少信息（scope 文件路径、ADR 引用）
- `openspec new change` 已生成 `.openspec.yaml`，propose 只需额外写入最小 proposal.md
- 若完全没有 proposal.md，deps Step 1 无法提取 scope/ADR → 三轴分析退化为空

### Decision 3: `fill` 阶段的触发方式

**选择**: guide-plan 用户菜单新增选项「3. 填充骨架 change (fill)」，进入后展示所有 `planned` 状态 change，按 deps 推荐顺序排序

**备选**: 独立的 `guide-plan-fill` 子技能

**理由**:
- fill 属于 plan 阶段内部操作（填充 change artifacts），不应独立为一个阶段
- 与现有 guide-plan 的 scan → propose → deps 循环一致，用户心理模型不变
- 独立子技能会增加用户学习成本（记住更多技能名称）

### Decision 4: deps 对骨架 change 的容错策略

**选择**: 容错读取——design.md/tasks.md 不存在时跳过对应分析轴，仅基于 proposal.md 的 scope/ADR 进行文件冲突和 ADR 依赖检测

**备选**: 要求骨架 change 也必须有占位 design.md（`## TODO: 待填充`）

**理由**:
- 容错避免了额外的人工步骤（创建占位文件）
- 跳过接口依赖轴（接口信息从 design.md 提取）的精度损失可接受——骨架阶段的依赖分析本就是"预分析"，最终依赖关系在 fill 后重新计算
- deps 输出标注 `skeleton: true` 供下游消费者区分精度

### Decision 5: guide-ship archive 后的触发机制

**选择**: 归档完成后，调用 `iteration.py` 的 `get_unblocked_planned()` 函数扫描 iteration.json，若有结果则输出建议信息（不自动调用 guide-plan）

**备选**: 自动执行 `skill_use("guide-plan", "fill")`

**理由**:
- 用户始终需要确认填充内容和执行顺序
- 自动填充可能在用户未准备时创建不准确的 design.md
- 建议信息 + 手动确认符合 plan 阶段"中介入"的人机协作模型（ADR-0003）

### Decision 6: proposal-suggestions.md 的 `skeleton` 状态

**选择**: 新增 status 值 `skeleton`，与 `待创建`、`进行中`、`已完成` 并列

**理由**:
- 区分"尚未创建任何 artifacts"（待创建）和"骨架已创建，等待填充"（skeleton）
- 在 proposal-suggestions.md 中保留骨架条目，方便 guide-plan fill 阶段读取 `description` 字段的完整需求描述来填充 artifacts

## Risks / Trade-offs

- **[Risk] 混合状态增加 plan-done 门控复杂度** → Mitigation: 门控新增明确的分类统计（`planned=N, proposed=M, total=N+M`），清晰展示状态分布
- **[Risk] deps 对骨架的预分析精度低于完整分析** → Mitigation: fill 后强制重新运行 deps，以完整 artifacts 的分析结果为准
- **[Risk] 骨架 change 可能被遗忘** → Mitigation: status Mode E（当前迭代视图）始终展示所有 `planned` 状态 change；guide-ship 完成后主动提醒
- **[Trade-off] `planned` 状态的 change 在 proposal-suggestions.md 中保留** → 可能造成条目膨胀。但这是必要的——骨架的 `description` 字段是后续 fill 的唯一需求来源