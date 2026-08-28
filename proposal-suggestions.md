# 提案池（待架构讨论）

> design 阶段输入。guide-design 逐个审查，批准后添加到 `proposal-approved.md`。
>
> **生命周期**: 提案从此文件创建 → design 审查 → 批准/拒绝/延迟 → 移至 `proposal-approved.md` 等待实施 → 实施后归档。
> **自动清理**: 提案被批准或实施后，`sync_suggestions()` 会自动从本表移除该行（不再停留）。
> **手动审计**: 发现过期条目时，运行 `skill_use("guide")` 的审计功能自动清理。
> **依赖记录**: `fix-orphan-hub-gates-wiring`（P1）阻塞于 `fix-adr-0031-safety-gate-substantiation`（P0）— audit log 须先非空，`check_cross_repo_approvals` 才能验证。

| 提案 | 优先级 | 来源 | 添加时间 | 状态 |
|------|--------|------|----------|------|
| [improve-from-roadmap-naming-flexibility](.rddf/improvements/improve-from-roadmap-naming-flexibility.md) | P2 | 2026-08-27 Hybrid path reflection (from_roadmap.sh 命名约束 `from-roadmap-<phase>-<category>` 不支持多 proposal batch 创建) | 2026-08-27 | 待 design 审查 |
| [improve-roadmap-feature-discovery](.rddf/improvements/improve-roadmap-feature-discovery.md) | P2 | 2026-08-27 Hybrid path reflection (feat-fix-audit-findings 未在 AGENTS.md 引用, 未来 agent 不知此 feature 存在) | 2026-08-27 | 待 design 审查 |
| [adr-index-auto-sync](.rddf/improvements/adr-index-auto-sync.md) | P2 | 2026-08-26 文档与代码一致性审计 | 2026-08-26 | ⏳ 已延迟 (2026-08-27) |
| [bypass-audit-mechanism](.rddf/improvements/bypass-audit-mechanism.md) | P2 | 2026-08-26 流程设计 review | 2026-08-26 | ⏳ 已延迟 (2026-08-27) |
| [changelog-usage-sync](.rddf/improvements/changelog-usage-sync.md) | P2 | 2026-08-26 文档与代码一致性审计 | 2026-08-26 | ⏳ 已延迟 (2026-08-27) |
| [verifier-archive-gate-clarification](.rddf/improvements/verifier-archive-gate-clarification.md) | P2 | 2026-08-26 流程设计 review | 2026-08-26 | ⏳ 已延迟 (2026-08-27) |

