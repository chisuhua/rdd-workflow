# 提案池（待架构讨论）

> design 阶段输入。guide-design 逐个审查，批准后添加到 `proposal-approved.md`。
>
> **生命周期**: 提案从此文件创建 → design 审查 → 批准/拒绝/延迟 → 移至 `proposal-approved.md` 等待实施 → 实施后归档。
> **自动清理**: 提案被批准或实施后，`sync_suggestions()` 会自动从本表移除该行（不再停留）。
> **手动审计**: 发现过期条目时，运行 `skill_use("guide")` 的审计功能自动清理。

| 提案 | 优先级 | 来源 | 添加时间 | 状态 |
|------|--------|------|----------|------|
| [check-project-setup](improvements/check-project-setup.md) | P1 | 用户反馈 — 启动无 gitignore 知识门槛 + 硬/软门控不对称 | 2026-07-31 | 待讨论 |
| [fix-scanner-fallback-and-orphan-archival](improvements/fix-scanner-fallback-and-orphan-archival.md) | P1 | HydraForge 案例 2026-07-31 — 消费方项目 scanner 静默失败 + rddf-session 孤儿归档残留 | 2026-08-01 | 待讨论 |


