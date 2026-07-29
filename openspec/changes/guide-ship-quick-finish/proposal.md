# Guide-ship quick finish path for near-complete changes

**优先级**: P2
**阶段**: v2.2
**分类**: core

## 概要

当 change 仅剩 ≤2 个 trivial 任务（文档/状态更新）时，`guide-ship` Phase 1 应提供 quick-finish 快捷路径，跳过 worktree 创建、plan 生成、execute 三件套，直接进入 review → archive。

## 背景

- PTX-EMU add-cudart-unit-tests guide-ship 复盘 2026-07-24 发现：change 仅剩 1 个 `update proposal-suggestions.md` 任务，但 guide-ship 仍假设全流程
- AI 不得不手动绕过整个 Phase 1，暴露了"near-complete change"的快捷路径缺失
- 类似的"大部分已完成、仅剩文档/状态更新"模式在项目后期频繁出现
- 用户期望：剩余 1-2 个 trivial 任务时，guide-ship 能识别并主动提示快捷路径

## 范围

### In Scope

- `ship_plan.sh` 中增加 `detect_quick_finish()` 函数：Phase 1 扫描时判断是否满足 quick-finish 条件
- quick-finish 条件：剩余任务 ≤ 2 且均为文档/状态更新类型（如 `[ ] update proposal-suggestions.md`），且所有代码变更已提交
- quick-finish 流程：跳过 worktree 创建、plan 生成、execute，直接进入 review → archive
- 用户交互：展示 quick-finish 与标准模式两个选项，附带剩余任务详情
- 归档后自动清理 .plan-handoff.json

### Out Scope

- 不修改已有 worktree 模式路径
- 不自动判断"trivial"的类型定义（由 AI 在 prompt 中展示判断依据给用户确认）
- 不影响 guide-ship Phase 2/3 的其他逻辑

## 关键场景

- GIVEN change 仅剩 1 个"更新 proposal-suggestions.md 状态"任务, WHEN 进入 guide-ship, THEN 展示 Quick Finish 选项
- GIVEN change 剩余 3 个功能实现任务, WHEN 进入 guide-ship, THEN 不触发 quick-finish 检测
- GIVEN quick-finish 选中, WHEN 执行, THEN 跳过 worktree/plan/execute, 直接进入 review → archive

## 验收标准

- guide-ship Phase 1 检测到 quick-finish 条件时展示对应选项
- quick-finish 路径跳过 worktree 创建和 plan 生成
- archive 后 iteration.json 正确更新
- 2 个 bats 测试：触发 quick-finish + 不触发场景