# sync-approved-to-suggestions

**优先级**: P1 | **来源**: 会话复盘 2026-07-23 — 双索引状态不一致
**阶段**: v2.1 | **分类**: core
**类型**: feature

## 架构依据

- `proposal-approved.md` 有 42 个批准条目，但 `proposal-suggestions.md` 中对应条目未更新状态
- `append_approved` 只写 approved.md，不更新 suggestions.md
- 双索引缺乏自动同步机制，人工维护成本高

## 范围

- **In Scope**:
  - `append_approved` 函数中增加：同步更新 `proposal-suggestions.md` 中对应条目，添加"已审批"标记或移到 `## 已批准` 表格
  - `mark_approved_completed` 中增加：同步更新 suggestions.md
  - 或：新增 `sync_suggestions_index` 函数，按 approved.md 状态批量更新 suggestions.md
- **Out Scope**:
  - 不修改 proposal-suggestions.md 的表格格式

## 关键场景

- GIVEN append_approved 被调用, WHEN 写入 approved.md, THEN 同步更新 suggestions.md 中对应条目
- GIVEN 批量批准, WHEN 全部完成, THEN suggestions.md 反映最新状态

## 技术约束

- MUST 通过 Python 脚本或 sed 操作 Markdown 表格
- MUST 容错：suggestions.md 中找不到对应条目时静默跳过
- SHOULD 与 `fix-stale-suggestions-warning` 的实现不冲突

## 验收标准

- approved.md 和 suggestions.md 条目状态一致
- 批量批准后无需手动同步