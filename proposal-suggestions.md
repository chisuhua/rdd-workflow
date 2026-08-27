# 提案池（待架构讨论）

> design 阶段输入。guide-design 逐个审查，批准后添加到 `proposal-approved.md`。
>
> **生命周期**: 提案从此文件创建 → design 审查 → 批准/拒绝/延迟 → 移至 `proposal-approved.md` 等待实施 → 实施后归档。
> **自动清理**: 提案被批准或实施后，`sync_suggestions()` 会自动从本表移除该行（不再停留）。
> **手动审计**: 发现过期条目时，运行 `skill_use("guide")` 的审计功能自动清理。
> **依赖记录**: `fix-orphan-hub-gates-wiring`（P1）阻塞于 `fix-adr-0031-safety-gate-substantiation`（P0）— audit log 须先非空，`check_cross_repo_approvals` 才能验证。

| 提案 | 优先级 | 来源 | 添加时间 | 状态 |
|------|--------|------|----------|------|
| [reconcile-iteration-after-archive](.rddf/improvements/reconcile-iteration-after-archive.md) | P0 | 2026-08-27 ship audit (3 P1 changes 已 archive 但 iteration 仍 proposed, rdd-verifier 扫描空队列) | 2026-08-27 | 待 design 审查 |
| [fix-iteration-archive-sync](.rddf/improvements/fix-iteration-archive-sync.md) | P0 | 2026-08-27 ship audit (archive hook 未同步 iteration.json, root cause) | 2026-08-27 | 待 design 审查 |
| [fix-proposal-ac-section-mapping](.rddf/improvements/fix-proposal-ac-section-mapping.md) | P1 | 2026-08-27 ship audit (generate_full_proposal.py 的 `_extract_section` 不匹配 `## 验收`,导致 Acceptance 是 TBD) | 2026-08-27 | 待 design 审查 |
| [fix-ship-plan-untracked-gate](.rddf/improvements/fix-ship-plan-untracked-gate.md) | P1 | 2026-08-27 ship audit (check_artifacts_committed 把 untracked specs/ 当作污染拒绝) | 2026-08-27 | 待 design 审查 |
| [fix-disk-count-semantic-conflict](.rddf/improvements/fix-disk-count-semantic-conflict.md) | P1 | 2026-08-27 ship audit (test_doc_contracts.py 与 bats 的 disk count 语义不一致) | 2026-08-27 | 待 design 审查 |
| [fix-design-preflight-roadmap-format](.rddf/improvements/fix-design-preflight-roadmap-format.md) | P1 | 2026-08-27 ship audit + Hybrid 路径验证 (design_preflight.py `_PHASE_HEADER_RE` 不匹配 `.rddf/roadmap.md` 表格格式) | 2026-08-27 | 待 design 审查 |
| [improve-execution-mode-per-change](.rddf/improvements/improve-execution-mode-per-change.md) | P2 | 2026-08-27 ship audit (detect_execution_mode 仅按 total_changes > 1 决策) | 2026-08-27 | 待 design 审查 |
| [improve-change-splitting-strategy](.rddf/improvements/improve-change-splitting-strategy.md) | P2 | 2026-08-27 ship audit (sync-package-skills-to-disk + sync-agents-md-five-stage 共享 AGENTS.md 导致 ship 污染) | 2026-08-27 | 待 design 审查 |
| [improve-commit-scope-discipline](.rddf/improvements/improve-commit-scope-discipline.md) | P2 | 2026-08-27 ship audit (`git add -A` 混入 pre-existing dirty + 空文件) | 2026-08-27 | 待 design 审查 |
| [adr-index-auto-sync](.rddf/improvements/adr-index-auto-sync.md) | P2 | 2026-08-26 文档与代码一致性审计 | 2026-08-26 | ⏳ 已延迟 (2026-08-27) |
| [bypass-audit-mechanism](.rddf/improvements/bypass-audit-mechanism.md) | P2 | 2026-08-26 流程设计 review | 2026-08-26 | ⏳ 已延迟 (2026-08-27) |
| [changelog-usage-sync](.rddf/improvements/changelog-usage-sync.md) | P2 | 2026-08-26 文档与代码一致性审计 | 2026-08-26 | ⏳ 已延迟 (2026-08-27) |
| [verifier-archive-gate-clarification](.rddf/improvements/verifier-archive-gate-clarification.md) | P2 | 2026-08-26 流程设计 review | 2026-08-26 | ⏳ 已延迟 (2026-08-27) |
