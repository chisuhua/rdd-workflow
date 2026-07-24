# Design: auto-skip-archived-proposals

## Context

arch Phase 5.5 审批时，43 个提案中全部 43 个已归档（ALREADY_DONE），Oracle 审查了已无实际价值。应在审批前自动检测 `openspec/changes/archive/` 中已存在的 change，对已归档提案自动标记为"已完成"并跳过 Oracle。

## Goals / Non-Goals

### Goals

- 在 Phase 5.5 入口增加 archive 检测，自动检查 `openspec/changes/archive/<date>-<name>/` 是否存在
- 已归档提案自动追加到 proposal-approved.md 的 `## 已实施` 表格
- 输出汇总：`N 个已归档自动批准 | M 个待审查`
- 保留手动审查选项（用户可选择查看已归档提案的详情）
- 输出清晰区分"自动批准（已归档）"和"Oracle 审查通过"

### Non-Goals

- 不修改 Oracle 审查逻辑
- 不修改提案文件格式

## Decisions

在 `approve_proposal.sh` 中，在调用 Oracle 之前增加预过滤步骤：

1. 遍历待审查提案列表，对每个提案名检查 `openspec/changes/archive/` 下是否存在匹配 `20\d{2}-\d{2}-\d{2}-<name>` 的目录
2. 已归档的提案直接调用 `mark_approved_completed` 追加到 `## 已实施` 表格，跳过 Oracle
3. 未归档的提案进入正常 Oracle 审查流程
4. 最终汇总输出两类数量

检测 archive 目录命名模式使用 glob `openspec/changes/archive/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-<name>` 确保只匹配日期前缀。

## Implementation

**关键修改文件:**

- `skills/guide-arch/scripts/approve_proposal.sh` — 新增 `check_archived()` 函数 + 预过滤循环
- `skills/guide-arch/SKILL.md` — Phase 5.5 描述更新，增加"自动跳过已归档"说明
- `skills/_lib/state.sh` — 复用 `mark_approved_completed` 函数（无需修改）
