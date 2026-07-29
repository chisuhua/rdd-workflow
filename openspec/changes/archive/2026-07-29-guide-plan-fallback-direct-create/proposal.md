## Why

PTX-EMU 项目已完成 35+ changes 全部归档，`proposal-approved.md` 不存在。用户意图是直接创建新 change（跳过大中小审批流程），但 guide-plan Phase 2 要求 `proposal-approved.md` 存在才能进入 propose 阶段，导致卡死。

## What Changes

- guide-plan Phase 1 环境检测后增加分支检测：`proposal-approved.md` 不存在 → 提供"直接创建新 change"后备选项
- 后备路径调用 `propose` 技能但不关联 `proposal-approved.md`（独立模式）
- 完成后正常进入 deps 阶段
- 后备模式创建的 change 在 `proposal.md` 中标注 `approved_by: "direct-create"`

## Capabilities

### New Capabilities
- `direct-create-fallback`: 无 proposal-approved.md 时的直接创建后备路径

### Modified Capabilities
- `plan-intake-flow`: 在 Phase 1 环境检测后增加分支检测

## Impact

- 修改文件：skills/guide-plan/SKILL.md, skills/guide-plan/scripts/plan_intake.sh
- 影响流程：guide-plan Phase 1 → Phase 2 入口
- 兼容：保留全量 approve 流程
