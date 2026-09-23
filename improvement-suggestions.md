# 提案池（待架构讨论）

> design 阶段输入。guide-design 逐个审查，批准后添加到 `improvement-approved.md`。
>
> **生命周期**: 提案从此文件创建 → design 审查 → 批准/拒绝/延迟 → 移至 `improvement-approved.md` 等待实施 → 实施后归档。
> **自动清理**: 提案被批准或实施后，`sync_suggestions()` 会自动从本表移除该行（不再停留）。
> **手动审计**: 发现过期条目时，运行 `skill_use("guide")` 的审计功能自动清理。
> **依赖记录**: `fix-orphan-hub-gates-wiring`（P1）阻塞于 `fix-adr-0031-safety-gate-substantiation`（P0）— audit log 须先非空，`check_cross_repo_approvals` 才能验证。

| 提案 | 优先级 | 来源 | 添加时间 | 状态 |
|------|--------|------|----------|------|
| [bypass-audit-mechanism](.rddf/improvements/bypass-audit-mechanism.md) | P2 | 2026-08-26 流程设计 review | 2026-08-26 | 延迟 (2026-08-28, 维持 v3.2 deferred 决策)  |
| [add-objective-evidence-v02-llm-synthesis](.rddf/improvements/add-objective-evidence-v02-llm-synthesis.md) | P2 | 2026-09-22 用户发起 — objective evidence v0.1 复盘 + 跨 repo 场景语义复杂度缺口补位 | 2026-09-22 | 待审查 |
| [add-stage-guide-e2e-cross-process-coverage](.rddf/improvements/add-stage-guide-e2e-cross-process-coverage.md) | P1 | 2026-09-23 review of feat-guide-orchestrator-session-event-bus — 核心架构承诺（跨 OpenCode 进程文件轮询）由 0 个 e2e test 验证；现有 test_guide_cross_container.bats 名为 cross 实为单进程模拟，存在 false confidence 风险 | 2026-09-23 | 待审查 |

