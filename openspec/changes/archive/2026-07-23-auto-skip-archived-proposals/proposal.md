# Proposal: auto-skip-archived-proposals

## Why

arch Phase 5.5 审批时，43 个提案中全部 43 个已归档（ALREADY_DONE），Oracle 审查了已无实际价值。应在审批前自动检测 `openspec/changes/archive/` 中已存在的 change，对已归档提案自动标记为"已完成"并跳过 Oracle，仅对真正未实施的提案发起审查。

来源: 会话复盘 2026-07-23

## What Changes

- 在 `guide-arch/scripts/approve_proposal.sh` 或 Phase 5.5 入口增加 archive 检测逻辑
- 自动检查 `openspec/changes/archive/<date>-<name>/` 是否存在已归档的 change
- 已归档的提案自动追加到 proposal-approved.md 的 `## 已实施` 表格
- 输出汇总：`N 个已归档自动批准 | M 个待审查`
- 不修改 Oracle 审查逻辑本身
- 不修改提案文件格式

## Capabilities

### New Capabilities: auto-skip-archived-proposals

在 arch 阶段 Phase 5.5 审批流程中，自动检测 `openspec/changes/archive/` 目录中已归档的 change，对已归档提案标记为"已完成"并跳过 Oracle 审查，仅对真正未实施的提案发起审查。检测 archive 目录命名模式 `20\d{2}-\d{2}-\d{2}-<name>`。

## Impact

**受影响文件:**
- `skills/guide-arch/scripts/approve_proposal.sh` — 新增 archive 检测逻辑
- `skills/guide-arch/SKILL.md` — Phase 5.5 流程更新
- `proposal-approved.md` — 自动追加已实施条目

**不受影响:**
- Oracle 审查逻辑
- 提案文件格式
