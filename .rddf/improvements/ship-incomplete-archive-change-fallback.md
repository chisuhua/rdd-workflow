# ship-incomplete-archive-change-fallback

**优先级**: P1 | **来源**: UsrLinuxEmu hal-iommu-full 执行复盘: 归档时自动将未完成任务转为 change 候选
**阶段**: v2.1 | **分类**: core
**类型**: feature

## 架构依据
- 复盘发现：hal-iommu-full ship 完成后有 2 个任务因依赖未解除而延后（iommu_invalidate 不在 gpu_hal_ops 中）
- 当前 guide-ship archive 阶段：如果 tasks.md 中有未完成的 [ ] 条目，直接归档会导致这些任务丢失
- 改进需求：archive 前检查 tasks.md 未完成任务，判断是否需要创建新 change，并自动追加到 proposal-suggestions.md

## 范围
- **In Scope**:
  - guide-ship Phase 3 (archive) 增加 pre-archive check：扫描 tasks.md 中未完成的 [ ] 条目
  - 对每个未完成任务：判断是「依赖未解除」还是「主动跳过」
  - 若是依赖未解除：自动生成 change 候选描述，追加到 proposal-suggestions.md
  - 若是主动跳过：标记为 skipped，不生成新 change
  - 用户交互确认（展示即将创建的候选 change 列表）
- **Out Scope**:
  - 不自动创建 change（仅追加到 proposal-suggestions.md）
  - 不修改 tasks.md 格式

## 关键场景
- GIVEN tasks.md 有未完成的 [ ] 条目标为延后, WHEN 执行 archive, THEN 自动追加对应条目到 proposal-suggestions.md
- GIVEN 所有任务已完成, WHEN archive, THEN 行为不变（不追加）

## 技术约束
- MUST 复用 propose.md Phase 2 的 proposal-suggestions.md 写入逻辑
- SHOULD 从 tasks.md 提取任务描述自动生成 change 名称和描述
- MUST 用户确认后才追加（非静默）

## 验收标准
- archive 时检测到未完成任务，打印候选 change 列表
- 用户确认后 proposal-suggestions.md 新增对应条目
- 不改变已完成 change 的归档流程
- 2 个 bats 测试：有未完成任务 + 无未完成任务场景
