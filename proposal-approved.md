# 已批准提案（Plan 阶段输入）

> plan 阶段输入。guide-plan propose 从此处读取，按链接打开对应 `improvements/xxx.md` 创建 change。

| 提案 | 优先级 | 批准时间 | 批准人 |
|------|--------|----------|--------|

| [add-config-validation](improvements/add-config-validation.md) | P0 | 2026-07-23 | guide-arch |

| [add-parent-feature-param](improvements/add-parent-feature-param.md) | P0 | 2026-07-23 | guide-arch |

| [add-workflow-synthesizer](improvements/add-workflow-synthesizer.md) | P0 | 2026-07-23 | guide-arch |

| [archive-iteration-sync](improvements/archive-iteration-sync.md) | P0 | 2026-07-23 | guide-arch |

| [auto-wave-scheduler](improvements/auto-wave-scheduler.md) | P0 | 2026-07-23 | guide-arch |





| [guide-plan-noninteractive](improvements/guide-plan-noninteractive.md) | P0 | 2026-07-23 | guide-arch |

| [propose-quality-autohook](improvements/propose-quality-autohook.md) | P0 | 2026-07-23 | guide-arch |

| [add-heartbeat-config](improvements/add-heartbeat-config.md) | P1 | 2026-07-23 | guide-arch |

| [add-propose-content-review](improvements/add-propose-content-review.md) | P1 | 2026-07-23 | guide-arch |

> **supersedes** (2026-07-28): 原始设计（propose Phase 4 自动末尾 + 写 `.rddf/state/propose-review.json`）已被后续 commits 修订：
> - `b4ad917` — relocate to arch Phase 5.5 human-in-loop 节点
> - `a99017b` — refine wording `修复` → `修订`（关联提案 add-change-content-review）
> - 当前最终设计：arch Phase 5.5 在 suggestions→approved 迁移界面 y/n/d/s 决策前，Oracle 终端展示 3 级报告（pass/warn/block），不持久化。已实现的孤儿 `skills/_lib/propose_content_review.py` 已删除（`311d497`）。

| [add-rddf-concurrency-tests](improvements/add-rddf-concurrency-tests.md) | P1 | 2026-07-23 | guide-arch |

| [add-session-progress-view](improvements/add-session-progress-view.md) | P1 | 2026-07-23 | guide-arch |

| [agent-completion-contract](improvements/agent-completion-contract.md) | P1 | 2026-07-23 | guide-arch |

| [archive-update-proposal-status](improvements/archive-update-proposal-status.md) | P1 | 2026-07-23 | guide-arch |

| [fix-attach-detach-symmetry](improvements/fix-attach-detach-symmetry.md) | P1 | 2026-07-23 | guide-arch |

| [guide-cross-validate](improvements/guide-cross-validate.md) | P1 | 2026-07-23 | guide-arch |

| [remove-ci-redundant-bats](improvements/remove-ci-redundant-bats.md) | P1 | 2026-07-23 | guide-arch |

| [split-iteration-module](improvements/split-iteration-module.md) | P1 | 2026-07-23 | guide-arch |

| [task-parallel-throttle](improvements/task-parallel-throttle.md) | P1 | 2026-07-23 | guide-arch |

| [unify-test-entry-points](improvements/unify-test-entry-points.md) | P1 | 2026-07-23 | guide-arch |

| [update-agents-module-map](improvements/update-agents-module-map.md) | P1 | 2026-07-23 | guide-arch |

| [add-file-size-quality-gate](improvements/add-file-size-quality-gate.md) | P2 | 2026-07-23 | guide-arch |

| [add-plugin-loader-tests](improvements/add-plugin-loader-tests.md) | P2 | 2026-07-23 | guide-arch |

| [add-progressive-linting](improvements/add-progressive-linting.md) | P2 | 2026-07-23 | guide-arch |

| [fix-scan-state-bats](improvements/fix-scan-state-bats.md) | P2 | 2026-07-23 | guide-arch |

| [preship-dirty-check](improvements/preship-dirty-check.md) | P2 | 2026-07-23 | guide-arch |

| [rddf-sessions-gc](improvements/rddf-sessions-gc.md) | P2 | 2026-07-23 | guide-arch |

| [relocate-loop-engine](improvements/relocate-loop-engine.md) | P2 | 2026-07-23 | guide-arch |

| [skill-name-auto-resolve](improvements/skill-name-auto-resolve.md) | P2 | 2026-07-23 | guide-arch |

| [split-rddf-god-class](improvements/split-rddf-god-class.md) | P2 | 2026-07-23 | guide-arch |

| [update-adr-index](improvements/update-adr-index.md) | P2 | 2026-07-23 | guide-arch |

| [auto-skip-archived-proposals](improvements/auto-skip-archived-proposals.md) | P0 | 2026-07-23 | guide-arch |

| [archive-cleanup-working-tree](improvements/archive-cleanup-working-tree.md) | P1 | 2026-07-23 | guide-arch |

| [fix-mark-approved-completed](improvements/fix-mark-approved-completed.md) | P1 | 2026-07-23 | guide-arch |

| [parallel-oracle-review](improvements/parallel-oracle-review.md) | P1 | 2026-07-23 | guide-arch |

| [update-guide-plan-format](improvements/update-guide-plan-format.md) | P1 | 2026-07-23 | guide-arch |

| [fix-stale-suggestions-warning](improvements/fix-stale-suggestions-warning.md) | P2 | 2026-07-23 | guide-arch |

| [fix-append-approved-output](improvements/fix-append-approved-output.md) | P2 | 2026-07-23 | guide-arch |

| [ship-incomplete-archive-change-fallback](improvements/ship-incomplete-archive-change-fallback.md) | P1 | 2026-07-26 | guide-arch |

| [archive-gate-incomplete-tasks](improvements/archive-gate-incomplete-tasks.md) | P1 | 2026-07-26 | guide-arch |

| [fix-skill-tool-cache](improvements/fix-skill-tool-cache.md) | P1 | 2026-07-26 | guide-arch |

| [ship-delete-branch-safety](improvements/ship-delete-branch-safety.md) | P1 | 2026-07-26 | guide-arch |

| [sync-approved-to-suggestions](improvements/sync-approved-to-suggestions.md) | P1 | 2026-07-26 | guide-arch |

| [pre-checkout-warning](improvements/pre-checkout-warning.md) | P2 | 2026-07-26 | guide-arch |

| [adr-creation-architecture-gate](improvements/adr-creation-architecture-gate.md) | P1 | 2026-07-26 | guide-arch |

| [fix-scan-state-integer-comparison](improvements/fix-scan-state-integer-comparison.md) | P2 | 2026-07-26 | guide-arch |

| [fix-arch-handoff-stale-detection](improvements/fix-arch-handoff-stale-detection.md) | P1 | 2026-07-26 | guide-arch |

| [filter-guide-ship-when-no-changes](improvements/filter-guide-ship-when-no-changes.md) | P2 | 2026-07-26 | guide-arch |

| [guide-plan-fallback-direct-create](improvements/guide-plan-fallback-direct-create.md) | P1 | 2026-07-26 | guide-arch |

| [fix-rddf-session-owner-cross-call](improvements/fix-rddf-session-owner-cross-call.md) | P1 | 2026-07-26 | guide-arch |

| [detect-suggestions-approved-inconsistency](improvements/detect-suggestions-approved-inconsistency.md) | P3 | 2026-07-26 | guide-arch |

| [prompt-worktree-cleanup-before-stage](improvements/prompt-worktree-cleanup-before-stage.md) | P3 | 2026-07-26 | guide-arch |

| [add-workflow-reflect-engine](improvements/add-workflow-reflect-engine.md) | P1 | 2026-07-26 | guide-arch |

| [fix-arch-env-check-adr-count-bug](improvements/fix-arch-env-check-adr-count-bug.md) | P2 | 2026-07-27 | guide-arch |

| [fix-deps-render-empty-candidates](improvements/fix-deps-render-empty-candidates.md) | P2 | 2026-07-27 | guide-arch |

| [fix-ship-lightweight-wt-path-pollution](improvements/fix-ship-lightweight-wt-path-pollution.md) | P2 | 2026-07-27 | guide-arch |

## 已实施
| 提案 | 状态 | 实施时间 |
|------|------|----------|
| [fix-silent-exception](improvements/fix-silent-exception.md) | proposed | 2026-07-26 |
| [fix-rddf-schema-validation](improvements/fix-rddf-schema-validation.md) | ? | 2026-07-26 |
| [audit-attach-detach-calls](improvements/audit-attach-detach-calls.md) | ? | 2026-07-26 |
| [fix-scan-state-binding](improvements/fix-scan-state-binding.md) | ? | 2026-07-26 |
| [add-workflow-synthesizer](improvements/add-workflow-synthesizer.md) | proposed | 2026-07-26 |
