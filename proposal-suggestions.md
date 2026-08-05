# 提案池（待架构讨论）

> design 阶段输入。guide-design 逐个审查，批准后添加到 `proposal-approved.md`。
>
> **生命周期**: 提案从此文件创建 → design 审查 → 批准/拒绝/延迟 → 移至 `proposal-approved.md` 等待实施 → 实施后归档。
> **自动清理**: 提案被批准或实施后，`sync_suggestions()` 会自动从本表移除该行（不再停留）。
> **手动审计**: 发现过期条目时，运行 `skill_use("guide")` 的审计功能自动清理。

| 提案 | 优先级 | 来源 | 添加时间 | 状态 |
|------|--------|------|----------|------|
| [fix-rddf-status-corrupt-message](improvements/fix-rddf-status-corrupt-message.md) | P1 | session 2026-08-05 — `rddf status` 对 schema-invalid iteration.json 误报 "not found" 并建议 `propose` (触发数据丢失式修复) | 2026-08-05T15:59:41Z | 已批准 |
| [fix-archive-iteration-sync](improvements/fix-archive-iteration-sync.md) | P0 | session 2026-08-05 UsrLinuxEmu — 5 个 stage4-l2-foundation-removal-* change 的 archive commit 全部没 patch iteration.json | 2026-08-05T16:05:00Z | 已批准 |
| [fix-archive-on-main-flow](improvements/fix-archive-on-main-flow.md) | P0 | session 2026-08-05 UsrLinuxEmu — archive_on_main.sh 旁路流程缺少 iteration sync hook 与 --confirm-main 门控 | 2026-08-05T16:05:00Z | 已批准 |
| [rddf-iteration-strict-schema](improvements/rddf-iteration-strict-schema.md) | P1 | session 2026-08-05 UsrLinuxEmu — AI 写 iteration.json 含未知字段触发静默 backup + 清空,缺乏可见性 | 2026-08-05T16:05:00Z | 已批准 |
| [fix-tasks-md-archive-residue](improvements/fix-tasks-md-archive-residue.md) | P1 | session 2026-08-05 UsrLinuxEmu — archive 后 tasks.md 静态残留导致 "archived 0/total" 自相矛盾状态 | 2026-08-05T16:05:00Z | 已批准 |
| [collect-l2-violation-count-on-archive](improvements/collect-l2-violation-count-on-archive.md) | P2 | session 2026-08-05 UsrLinuxEmu — 5 个 removal commit message 各自声明 L2 减少量,全局绝对计数无任何文件记录 | 2026-08-05T16:05:00Z | 已批准 |
| [add-archive-post-commit-hook-and-force-flag](improvements/add-archive-post-commit-hook-and-force-flag.md) | P0 | HydraForge 2026-08-05 dashboard divergence 调查 + UsrLinuxEmu 2026-08-05 on-main archive 复盘 — 裸 `git mv` + `git commit` 手工 archive path 完全未被任何现有提案兜底; `--force` flag 消除 archive_gate_check 绕过动机 | 2026-08-05T16:36:37Z | 已批准 |


