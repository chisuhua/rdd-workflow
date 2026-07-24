# guide-ship-quick-finish

**优先级**: P2 | **来源**: PTX-EMU add-cudart-unit-tests guide-ship 复盘 2026-07-24
**阶段**: v2.2 | **分类**: core
**类型**: feature

## 架构依据
- 复盘发现：`add-cudart-unit-tests` 仅剩 1 个 trivial 任务（更新 proposal-suggestions.md 状态），但 guide-ship Phase 1 仍假设 worktree 创建 → plan 生成 → execute 三步走
- AI 不得不绕过整个 Phase 1 手动处理，暴露了"near-complete change"的快捷路径缺失
- 类似的"大部分已完成、仅剩文档/状态更新"模式在项目后期会频繁出现

## 范围
- **In Scope**:
  - `ship_plan.sh` 中增加快速完成检测逻辑：Phase 1 扫描时判断是否满足 quick-finish 条件
  - quick-finish 条件：剩余任务 ≤ 2 且均为文档/状态更新类型（`[ ] update proposal-suggestions.md` 等），且所有代码变更已提交
  - quick-finish 流程：跳过 worktree 创建、plan 生成、execute 三件套，直接进入 review → archive
  - 用户交互：展示 quick-finish 与标准模式两个选项，附带剩余任务详情
- **Out Scope**:
  - 不修改已有 worktree 模式路径
  - 不自动判断"trivial"的类型定义（由 AI 在 prompt 中展示判断依据给用户确认）

## 关键场景
- GIVEN change 仅剩 1 个"更新 proposal-suggestions.md 状态"任务, WHEN 进入 guide-ship, THEN 展示 Quick Finish 选项
- GIVEN change 剩余 3 个功能实现任务, WHEN 进入 guide-ship, THEN 不触发 quick-finish 检测
- GIVEN quick-finish 选中, WHEN 执行, THEN 跳过 worktree/plan/execute, 直接进入 review → archive

## 技术约束
- MUST 通过检测 tasks.md 中 `[ ]` 条目类型和数量判断是否触发 quick-finish
- MUST AI 在 prompt 中展示剩余任务详情让用户确认，不自动推定
- MUST 不创建 worktree 和不生成 plan 文件（quick-finish 不产生 .rddf/plans/ 文件）
- SHOULD quick-finish 归档完成后自动清理 .plan-handoff.json

## 验收标准
- guide-ship Phase 1 检测到 quick-finish 条件时展示对应选项
- quick-finish 路径跳过 worktree 创建和 plan 生成
- archive 后 iteration.json 正确更新
- 2 个 bats 测试：触发 quick-finish + 不触发场景