# 提案池（待架构讨论）

> design 阶段输入。guide-design 逐个审查，批准后添加到 `proposal-approved.md`。
>
> **生命周期**: 提案从此文件创建 → design 审查 → 批准/拒绝/延迟 → 移至 `proposal-approved.md` 等待实施 → 实施后归档。
> **自动清理**: 提案被批准或实施后，`sync_suggestions()` 会自动从本表移除该行（不再停留）。
> **手动审计**: 发现过期条目时，运行 `skill_use("guide")` 的审计功能自动清理。

| 提案 | 优先级 | 来源 | 添加时间 | 状态 |
|------|--------|------|----------|------|
| [guide-ship-default-serial-execution](improvements/guide-ship-default-serial-execution.md) | P1 | Session 复盘限流/配额问题 + 用户决策 | 2026-08-04 | 新增 |
| [subagent-orchestrator-execution-strategy](improvements/subagent-orchestrator-execution-strategy.md) | P0 | Session 复盘:5 changes ship 时子代理配额耗尽,4 个降级到 orchestrator 直接执行 | 2026-08-04 | 新增 |
| [plan-quality-and-validation](improvements/plan-quality-and-validation.md) | P0 | Session 复盘:2 个 plan 的 expected 数字与实际不符(脚本需 guard、cross-stage conflict 未考虑) | 2026-08-04 | 新增 |
| [worktree-archive-workflow](improvements/worktree-archive-workflow.md) | P0 | Session 复盘:execute 不 commit 与 archive 需 commits 矛盾隐含,需显式文档 + 批量归档优化 | 2026-08-04 | 新增 |
| [developer-experience-observability](improvements/developer-experience-observability.md) | P2 | Session 复盘:hook 在必要注释误报 + 缺工作流改进数据基础 | 2026-08-04 | 新增 |


