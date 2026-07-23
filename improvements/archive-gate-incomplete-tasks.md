# archive-gate-incomplete-tasks

**优先级**: P1 | **来源**: 会话复盘 2026-07-23 — 4 个 change 未实现即归档
**阶段**: v2.1 | **分类**: core
**类型**: feature

## 架构依据

- guide-ship Phase 3 归档时，`openspec archive --yes` 对 tasks.md 中全部 `[ ]` 的 change 仅 warning 不阻断
- 本次会话中 `parallel-oracle-review`、`update-guide-plan-format`、`fix-stale-suggestions-warning`、`fix-append-approved-output` 4 个 change 在 tasks 全未完成时被归档
- 缺少"实现完成"验证门控

## 范围

- **In Scope**:
  - guide-ship Phase 3 归档前增加门控检查：`grep -c '\[x\]' tasks.md` ≥ 1 才能归档
  - 0 个完成任务的 change 提示"未实现，确认归档？"并要求二次确认
  - 可在 `archive.sh::archive_change` 或 guide-ship SKILL.md Phase 3 中实现
- **Out Scope**:
  - 不修改 openspec CLI 的行为
  - 不强制 100% 完成才可归档（部分完成允许）

## 关键场景

- GIVEN tasks.md 全部 `[ ]`, WHEN 尝试归档, THEN 阻止并要求二次确认
- GIVEN tasks.md 至少 1 个 `[x]`, WHEN 归档, THEN 正常进行

## 技术约束

- MUST 使用 `grep -c '\[x\]' tasks.md` 检测完成数
- MUST 支持 `FORCE_ARCHIVE_INCOMPLETE=yes` 跳过检查
- SHOULD 在 guide-ship SKILL.md 文档中记录此门控

## 验收标准

- 未实现的 change 归档时被阻止
- FORCE_ARCHIVE_INCOMPLETE=yes 可跳过
- 已完成 change 归档不受影响
