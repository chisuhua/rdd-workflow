# guide-plan-fallback-direct-create

**优先级**: P1 | **来源**: Session 复盘 2026-07-26 — 成熟项目 dead-end
**阶段**: v2.1 | **分类**: planning
**类型**: feature

## 架构依据
- Session 复盘：PTX-EMU 项目已完成 35+ changes 全部归档，`proposal-approved.md` 不存在。用户意图是直接创建新 change（跳过大中小审批流程），但 guide-plan Phase 2 要求 `proposal-approved.md` 存在才能进入 propose 阶段。
- 根因：guide-plan 工作流假设所有 change 都从已批准提案开始。对于已成熟的项目，这个假设不成立。
- 影响：用户在 `guide` 选择 `guide-plan` → 检测到无 `proposal-approved.md` → 卡死 → 被迫退出。

## 范围
- **In Scope**:
  - guide-plan Phase 1 环境检测后增加分支检测：`proposal-approved.md` 不存在 → 提供"直接创建新 change"后备选项
  - 后备路径调用 `propose` 技能但不关联 `proposal-approved.md`（独立模式）
  - 完成后正常进入 deps 阶段
  - 输出提示："跳过提案审批流程，直接进入变更创建。后续可手动追加 proposal-approved.md 作为审计追溯。"
- **Out Scope**:
  - 不修改 guide-plan 的 approve 模式（保留完整流程）
  - 不修改 propose 技能本身（只新增调用入口）
  - 不影响 guide-arch / guide-ship

## 关键场景
- GIVEN `proposal-approved.md` 不存在且 `openspec/changes/archive/` 有历史归档, WHEN `guide-plan` 入口, THEN 自动提示后备选项, 用户可直接创建 change
- GIVEN `proposal-approved.md` 存在且有已批准提案, WHEN `guide-plan` 入口, THEN 行为不变（进入正常 propose 菜单）
- GIVEN 全新项目 `proposal-approved.md` 不存在且无归档, WHEN `guide-plan` 入口, THEN 提示"请先运行 guide-arch 完成架构定义"

## 技术约束
- MUST 保留全量 approve 流程（兼容已有项目）
- MUST 识别新项目 vs 成熟项目（通过归档数量或 project 年龄）
- 后备模式创建的 change 应在 `proposal.md` 中标注 `approved_by: "direct-create"`

## 验收标准
- `guide-plan` 在 `proposal-approved.md` 不存在且项目有归档时进入后备模式
- 后备模式下可正常调用 `propose` 创建 change
- 创建的 change artifacts 包含 `approved_by: "direct-create"` 标记
- 已有 bats 测试通过