# 已批准提案（Plan 阶段输入）

> plan 阶段输入。guide-plan propose 从此处读取，按链接打开对应 `improvements/xxx.md` 创建 change。

> **supersedes** (2026-07-28): 原始设计（propose Phase 4 自动末尾 + 写 `.rddf/state/propose-review.json`）已被后续 commits 修订：
> - `b4ad917` — relocate to arch Phase 5.5 human-in-loop 节点
> - `a99017b` — refine wording `修复` → `修订`（关联提案 add-change-content-review）
> - 当前最终设计：arch Phase 5.5 在 suggestions→approved 迁移界面 y/n/d/s 决策前，Oracle 终端展示 3 级报告（pass/warn/block），不持久化。已实现的孤儿 `skills/_lib/propose_content_review.py` 已删除（`311d497`）。

## 已批准提案

| 提案 | 优先级 | 批准时间 | 批准者 |
|------|--------|----------|--------|





| [check-project-setup](improvements/check-project-setup.md) | P1 | 2026-08-01 | guide-arch |

| [fix-scanner-fallback-and-orphan-archival](improvements/fix-scanner-fallback-and-orphan-archival.md) | P1 | 2026-08-01 | guide-arch |

| [fix-wt-scanner-strip-bug-and-untracked-coverage](improvements/fix-wt-scanner-strip-bug-and-untracked-coverage.md) | P1 | 2026-08-01 | guide-arch |

| [improve-ship-done-cleanup-orphan-sessions](improvements/improve-ship-done-cleanup-orphan-sessions.md) | P2 | 2026-08-01 | guide-arch |

## 已实施
| [fix-mark-approved-completed-date-drift](improvements/fix-mark-approved-completed-date-drift.md) | P2 | 2026-08-01 |
| [fix-ship-plan-skill-use-fallback](improvements/fix-ship-plan-skill-use-fallback.md) | P1 | 2026-08-01 |
| [fix-deps-render-report-multi-candidate](improvements/fix-deps-render-report-multi-candidate.md) | P1 | 2026-08-01 |
| [fix-update-proposal-status-data-loss](improvements/fix-update-proposal-status-data-loss.md) | P0 | 2026-08-01 |

| 提案 | 优先级 | 完成时间 |
|------|--------|----------|
| [fix-add-improve-initial-prompt-ux](improvements/fix-add-improve-initial-prompt-ux.md) | P1 | 2026-07-31 |
| [fix-plan-deps-candidates-import-guard](improvements/fix-plan-deps-candidates-import-guard.md) | P0 | 2026-07-31 |
| [fix-rddf-session-lifecycle-binding](improvements/fix-rddf-session-lifecycle-binding.md) | P1 | 2026-07-31 |
| [fix-test-infrastructure-and-skill-registration](improvements/fix-test-infrastructure-and-skill-registration.md) | P2 | 2026-07-31 |
| [deps-driven-execution-mode](improvements/deps-driven-execution-mode.md) | P2 | 2026-07-30 |
| [guide-ship-quick-finish](improvements/guide-ship-quick-finish.md) | P2 | 2026-07-29 |
| [fix-plan-done-gate-zero-stale-count](improvements/fix-plan-done-gate-zero-stale-count.md) | P2 | 2026-07-29 |
| [fix-guide-ship-archive-bats](improvements/fix-guide-ship-archive-bats.md) | P2 | 2026-07-29 |
| [fix-doc-truth-sync](improvements/fix-doc-truth-sync.md) | P2 | 2026-07-29 |
| [archive-cleanup-plan-files](improvements/archive-cleanup-plan-files.md) | P2 | 2026-07-29 |
| [add-proposal-defer-support](improvements/add-proposal-defer-support.md) | P2 | 2026-07-29 |
| [prompt-worktree-cleanup-before-stage](improvements/prompt-worktree-cleanup-before-stage.md) | P3 | 2026-07-29 |
| [detect-suggestions-approved-inconsistency](improvements/detect-suggestions-approved-inconsistency.md) | P3 | 2026-07-29 |
| [filter-guide-ship-when-no-changes](improvements/filter-guide-ship-when-no-changes.md) | P2 | 2026-07-29 |
| [fix-scan-state-integer-comparison](improvements/fix-scan-state-integer-comparison.md) | P2 | 2026-07-29 |
| [pre-checkout-warning](improvements/pre-checkout-warning.md) | P2 | 2026-07-29 |
| [archive-cleanup-plan-handoff](improvements/archive-cleanup-plan-handoff.md) | P1 | 2026-07-29 |
| [add-proposal-deps-and-features](improvements/add-proposal-deps-and-features.md) | P1 | 2026-07-29 |
| [add-change-content-review](improvements/add-change-content-review.md) | P1 | 2026-07-29 |
| [guide-plan-fallback-direct-create](improvements/guide-plan-fallback-direct-create.md) | P1 | 2026-07-29 |
| [fix-arch-handoff-stale-detection](improvements/fix-arch-handoff-stale-detection.md) | P1 | 2026-07-29 |
| [adr-creation-architecture-gate](improvements/adr-creation-architecture-gate.md) | P1 | 2026-07-29 |
| [sync-approved-to-suggestions](improvements/sync-approved-to-suggestions.md) | P1 | 2026-07-29 |
| [fix-skill-tool-cache](improvements/fix-skill-tool-cache.md) | P1 | 2026-07-29 |
| [archive-gate-incomplete-tasks](improvements/archive-gate-incomplete-tasks.md) | P1 | 2026-07-29 |
| [ship-incomplete-archive-change-fallback](improvements/ship-incomplete-archive-change-fallback.md) | P1 | 2026-07-29 |
| [ship-delete-branch-safety](improvements/ship-delete-branch-safety.md) | P1 | 2026-07-29 |
| [fix-rddf-session-owner-cross-call](improvements/fix-rddf-session-owner-cross-call.md) | P1 | 2026-07-29 |
| [RDDF-0001-fix-rddf-session-import-path](improvements/RDDF-0001-fix-rddf-session-import-path.md) | P1 | 2026-07-29 |
| [add-config-validation](improvements/add-config-validation.md) | P0 | 2026-07-28 |
| [add-file-size-quality-gate](improvements/add-file-size-quality-gate.md) | P2 | 2026-07-28 |
| [add-full-regression-gate](improvements/add-full-regression-gate.md) | P0 | 2026-07-28 |
| [add-heartbeat-config](improvements/add-heartbeat-config.md) | P1 | 2026-07-28 |
| [add-openspec-gate](improvements/add-openspec-gate.md) | P0 | 2026-07-28 |
| [add-parent-feature-param](improvements/add-parent-feature-param.md) | P0 | 2026-07-28 |
| [add-plugin-loader-tests](improvements/add-plugin-loader-tests.md) | P2 | 2026-07-28 |
| [add-progressive-linting](improvements/add-progressive-linting.md) | P2 | 2026-07-28 |
| [add-propose-content-review](improvements/add-propose-content-review.md) | P1 | 2026-07-28 |
| [add-rddf-concurrency-tests](improvements/add-rddf-concurrency-tests.md) | P1 | 2026-07-28 |
| [add-session-progress-view](improvements/add-session-progress-view.md) | P1 | 2026-07-28 |
| [add-workflow-reflect-engine](improvements/add-workflow-reflect-engine.md) | P1 | 2026-07-28 |
| [add-workflow-synthesizer](improvements/add-workflow-synthesizer.md) | P0 | 2026-07-28 |
| [agent-completion-contract](improvements/agent-completion-contract.md) | P1 | 2026-07-28 |
| [archive-cleanup-working-tree](improvements/archive-cleanup-working-tree.md) | P1 | 2026-07-28 |
| [archive-iteration-sync](improvements/archive-iteration-sync.md) | P0 | 2026-07-28 |
| [archive-update-proposal-status](improvements/archive-update-proposal-status.md) | P1 | 2026-07-28 |
| [audit-attach-detach-calls](improvements/audit-attach-detach-calls.md) | P0 | 2026-07-28 |
| [auto-skip-archived-proposals](improvements/auto-skip-archived-proposals.md) | P0 | 2026-07-28 |
| [auto-sync-adr-index](improvements/auto-sync-adr-index.md) | P2 | 2026-07-28 |
| [auto-wave-scheduler](improvements/auto-wave-scheduler.md) | P0 | 2026-07-28 |
| [enforce-hook-symmetry](improvements/enforce-hook-symmetry.md) | P2 | 2026-07-28 |
| [fix-append-approved-output](improvements/fix-append-approved-output.md) | P2 | 2026-07-28 |
| [fix-arch-env-check-adr-count-bug](improvements/fix-arch-env-check-adr-count-bug.md) | P2 | 2026-07-28 |
| [fix-attach-detach-symmetry](improvements/fix-attach-detach-symmetry.md) | P1 | 2026-07-28 |
| [fix-deps-render-empty-candidates](improvements/fix-deps-render-empty-candidates.md) | P2 | 2026-07-28 |
| [fix-lsp-dash-bridge](improvements/fix-lsp-dash-bridge.md) | P0 | 2026-07-28 |
| [fix-mark-approved-completed](improvements/fix-mark-approved-completed.md) | P1 | 2026-07-28 |
| [fix-rddf-schema-validation](improvements/fix-rddf-schema-validation.md) | P0 | 2026-07-28 |
| [fix-scan-state-binding](improvements/fix-scan-state-binding.md) | P0 | 2026-07-28 |
| [fix-ship-lightweight-wt-path-pollution](improvements/fix-ship-lightweight-wt-path-pollution.md) | P2 | 2026-07-28 |
| [fix-silent-exception](improvements/fix-silent-exception.md) | P0 | 2026-07-28 |
| [fix-stale-suggestions-warning](improvements/fix-stale-suggestions-warning.md) | P2 | 2026-07-28 |
| [guide-cross-validate](improvements/guide-cross-validate.md) | P1 | 2026-07-28 |
| [guide-plan-noninteractive](improvements/guide-plan-noninteractive.md) | P0 | 2026-07-28 |
| [improve-openspec-test-change-support](improvements/improve-openspec-test-change-support.md) | P0 | 2026-07-28 |
| [parallel-oracle-review](improvements/parallel-oracle-review.md) | P1 | 2026-07-28 |
| [parallel-wave-execution](improvements/parallel-wave-execution.md) | P1 | 2026-07-28 |
| [preship-dirty-check](improvements/preship-dirty-check.md) | P2 | 2026-07-28 |
| [proposal-approval-pipeline](improvements/proposal-approval-pipeline.md) | P0 | 2026-07-28 |
| [propose-quality-autohook](improvements/propose-quality-autohook.md) | P0 | 2026-07-28 |
| [rddf-sessions-gc](improvements/rddf-sessions-gc.md) | P2 | 2026-07-28 |
| [relocate-loop-engine](improvements/relocate-loop-engine.md) | P2 | 2026-07-28 |
| [remove-ci-redundant-bats](improvements/remove-ci-redundant-bats.md) | P1 | 2026-07-28 |
| [skill-name-auto-resolve](improvements/skill-name-auto-resolve.md) | P2 | 2026-07-28 |
| [split-iteration-module](improvements/split-iteration-module.md) | P1 | 2026-07-28 |
| [split-rddf-god-class](improvements/split-rddf-god-class.md) | P2 | 2026-07-28 |
| [task-parallel-throttle](improvements/task-parallel-throttle.md) | P1 | 2026-07-28 |
| [unify-session-kind-naming](improvements/unify-session-kind-naming.md) | P0 | 2026-07-28 |
| [unify-test-entry-points](improvements/unify-test-entry-points.md) | P1 | 2026-07-28 |
| [update-adr-index](improvements/update-adr-index.md) | P2 | 2026-07-28 |
| [update-agents-module-map](improvements/update-agents-module-map.md) | P1 | 2026-07-28 |
| [update-guide-plan-format](improvements/update-guide-plan-format.md) | P1 | 2026-07-28 |
| [fix-scan-state-bats](improvements/fix-scan-state-bats.md) | P2 | 2026-07-23 |
