# 提案池（待架构讨论）

> design 阶段输入。guide-design 逐个审查，批准后添加到 `proposal-approved.md`。
>
> **生命周期**: 提案从此文件创建 → design 审查 → 批准/拒绝/延迟 → 移至 `proposal-approved.md` 等待实施 → 实施后归档。
> **自动清理**: 提案被批准或实施后，`sync_suggestions()` 会自动从本表移除该行（不再停留）。
> **手动审计**: 发现过期条目时，运行 `skill_use("guide")` 的审计功能自动清理。

| 提案 | 优先级 | 来源 | 添加时间 | 状态 |
|------|--------|------|----------|------|
| [fix-plan-deps-candidates-import-guard](improvements/fix-plan-deps-candidates-import-guard.md) | P0 | 会话复盘 2026-07-31 — plan_deps_candidates_env.py 无 None guard + execution_mode_decisions 数据残留 | 2026-07-31 | |
| [fix-rddf-session-lifecycle-binding](improvements/fix-rddf-session-lifecycle-binding.md) | P1 | 会话复盘 2026-07-31 — 4 阶段工作流执行中缺少 session 生命周期管理 | 2026-07-31 | |
| [fix-test-infrastructure-and-skill-registration](improvements/fix-test-infrastructure-and-skill-registration.md) | P2 | 会话复盘 2026-07-31 — bats 基础设施损坏 + 9 个 Python 测试持续失败 | 2026-07-31 | |


