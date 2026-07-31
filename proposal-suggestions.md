# 提案池（待架构讨论）

> design 阶段输入。guide-design 逐个审查，批准后添加到 `proposal-approved.md`。
>
> **生命周期**: 提案从此文件创建 → design 审查 → 批准/拒绝/延迟 → 移至 `proposal-approved.md` 等待实施 → 实施后归档。
> **自动清理**: 提案被批准或实施后，`sync_suggestions()` 会自动从本表移除该行（不再停留）。
> **手动审计**: 发现过期条目时，运行 `skill_use("guide")` 的审计功能自动清理。

| 提案 | 优先级 | 来源 | 添加时间 | 状态 |
|------|--------|------|----------|------|
| [fix-update-proposal-status-data-loss](improvements/fix-update-proposal-status-data-loss.md) | P0 | 会话复盘 2026-07-31 — 归档后 proposal-approved.md 已实施表从 83 条坍缩到 1 条（历史审计数据丢失） | 2026-07-31 | 待创建 |
| [fix-deps-render-report-multi-candidate](improvements/fix-deps-render-report-multi-candidate.md) | P1 | 会话复盘 2026-07-31 — 3 个候选 change 渲染成单个拼接字符串 | 2026-07-31 | 待创建 |
| [fix-ship-plan-skill-use-fallback](improvements/fix-ship-plan-skill-use-fallback.md) | P1 | 会话复盘 2026-07-31 — bash 子进程调用 skill_use 恒失败，3 次计划生成失败 | 2026-07-31 | 待创建 |
| [fix-mark-approved-completed-date-drift](improvements/fix-mark-approved-completed-date-drift.md) | P2 | 会话复盘 2026-07-31 — 幂等调用覆盖原完成日期 | 2026-07-31 | 待创建 |


