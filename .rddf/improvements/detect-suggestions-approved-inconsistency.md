# detect-suggestions-approved-inconsistency

**优先级**: P3 | **来源**: Session 复盘 2026-07-26 — 审计追溯缺失
**阶段**: v2.1 | **分类**: planning
**类型**: improvement

## 架构依据
- Session 复盘：`proposal-suggestions.md` 有 10 项全部标记为 `status: "已完成"` 或 `"已评估，不需要"` 或 `"暂缓"`，但 `proposal-approved.md` 从未被创建。中间缺失了"批准"步骤的审计追溯。
- 根因：项目历史中 changes 被直接创建并归档，绕过了 proposal → approved → change 的标准流程。workflow 无检测此不一致的机制。
- 影响：审计者无法区分"已完成"的 suggestion 是通过 approved 流程还是 bypass 完成。丧失了 workflow 的治理能力。

## 范围
- **In Scope**:
  - `guide` 入口扫描新增一致性检测：当 `proposal-suggestions.md` 有 `status: "已完成"` 的条目但 `proposal-approved.md` 不存在或对应条目缺失时，输出提示
  - 可选：自动创建缺失的 `proposal-approved.md` 条目（从 suggestion 内容派生），标记来源为 `"auto-recovered"`
  - 在 `guide` 入口输出："⚠️ N 个 suggestions 标记已完成但无 approved 记录 — 建议审计或自动恢复"
- **Out Scope**:
  - 不修改 `guide-arch` Phase 5.5 的审批流程
  - 不自动修改 `proposal-suggestions.md` 的状态
  - 不影响正常的 approve → propose 流程

## 关键场景
- GIVEN `proposal-suggestions.md` 有 5 个 `status: "已完成"` 且 `proposal-approved.md` 不存在 WHEN `guide_entry` 执行 THEN 输出警告 + 建议自动恢复
- GIVEN `proposal-approved.md` 与 `proposal-suggestions.md` 一致 WHEN `guide_entry` 执行 THEN 无警告
- GIVEN `proposal-suggestions.md` 不存在 WHEN `guide_entry` 执行 THEN 无警告

## 技术约束
- MUST 只读——不修改任何文件
- MUST 在 `proposal-approved.md` 和 `proposal-suggestions.md` 都存在时验证条目一致性

## 验收标准
- `guide_entry` 检测到不一致时输出 `⚠️` 警告
- 正常项目无 false positive
- 新增 bats 测试覆盖一致性检测