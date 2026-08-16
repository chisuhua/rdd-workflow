# 已批准提案（Plan 阶段输入）

> plan 阶段输入。guide-design 批准后直接落盘 `openspec/changes/<name>/proposal.md`，并写入本索引。guide-plan intake 按链接打开对应 `.rddf/improvements/<name>.md`，并通过 `.rddf/state/.design-handoff.json` v2 的 `changes_pre_created` 数组跳过已落盘的 change（Path A）。

> **supersedes** (2026-07-28): 原始设计（propose Phase 4 自动末尾 + 写 `.rddf/state/propose-review.json`）已被后续 commits 修订：
> - `b4ad917` — relocate to arch Phase 5.5 human-in-loop 节点（**历史**：v2.1+ 已迁移至 guide-design Phase 3，详见 ADR-0025）
> - `a99017b` — refine wording `修复` → `修订`（关联提案 add-change-content-review）
> - 当前最终设计（**已更新** v2.1+，ADR-0025）：`guide-design` Phase 3 拥有 suggestions→approved 迁移的 y/n/d/s 决策；批准动作直接落盘 `openspec/changes/<name>/proposal.md`（Path A，详见 move-proposal-creation-to-design 提案）。Oracle 终端展示 3 级报告（pass/warn/block），不持久化。已实现的孤儿 `skills/_lib/propose_content_review.py` 已删除（`311d497`）。

## 已批准提案

| 提案 | 优先级 | 批准时间 | 批准者 |
|------|--------|----------|--------|

> **依赖声明 (2026-08-05 design-done)**: 本批 7 项提案 (本次批准) 形成强依赖链, 计划按下列顺序实施:
> 1. **`fix-archive-iteration-sync`** (P0) — first: 定义 `sync_iteration_after_archive` helper, 装到 `archive.sh::archive_change()` + `archive_on_main.sh` + `rddf status --archive` 3 个入口
> 2. **`fix-archive-on-main-flow`** (P0) — after #1: 给 `archive_on_main.sh` 加 `--confirm-main` 必填 + 失败回滚 (在 #1 的 helper 之上加固)
> 3. **`add-archive-post-commit-hook-and-force-flag`** (P0) — after #1: 凭 #1 的 helper 拦截裸 `git mv` 路径 + `--force` 消除绕过动机 (AC-16 硬约束)
> 4. **`fix-rddf-status-corrupt-message`** (P1) + **`rddf-iteration-strict-schema`** (P1) — 并行: 共修 `status_cmd.py` + `state_reader.py`, 建议合 PR 避免 collision (前者修 read-side 消息折叠, 后者加 `rddf iteration lint` + `allowed-fields` 写前预检)
> 5. **`fix-tasks-md-archive-residue`** (P1) — independent, 推荐与 #1 同 PR (共享 `archive_change()` 末尾 hook 触发点)
> 6. **`collect-l2-violation-count-on-archive`** (P2) — last: 依赖 #4 的 schema 演进策略 (自身需 schema bump, 等 #4 明确 schema 治理流程后实施)
>
> **重叠修正 (2026-08-05 design-done)**:
> - `fix-archive-iteration-sync` 与 `fix-archive-on-main-flow` 在 `archive_on_main.sh` 路径上重叠. 实施时 **#1 先** (helper + 3 个入口), **#2 后** (在该文件加 `--confirm-main` 必填 + 失败回滚 — 不重写 #1 的 sync 调用)
> - `fix-rddf-status-corrupt-message` 与 `rddf-iteration-strict-schema` 在 `status_cmd.py` 上重叠. 前者修 read-side 错误消息折叠, 后者加 write-side `lint` / `allowed-fields` 子命令. 两者都改 `status_cmd.py`, 建议 **同 PR 合并**避免 file conflict
> - `fix-archive-iteration-sync` 与 `fix-tasks-md-archive-residue` 在 `archive_change()` 末尾 hook 上重叠. 推荐 **同 PR 合并实施** (sidecar 生成 + tasks_done 派生都在同一 hook 点)
>
> **bump 合并声明 (2026-08-05 design-done)**: `fix-rddf-status-corrupt-message` (本次批准) 与 `rddf-iteration-strict-schema` (本次批准) **合并为单一 CLI 消息治理 PR** (`unify-status-cmd-iteration-messages`), 一次同时支持 read-side 缺失/损坏区分 + write-side 预检工具. **禁止拆为两次独立 PR**. Plan 阶段必须先实施 #1 (`fix-archive-iteration-sync`) 再启动本 PR.

> **supersedes** (2026-08-02 design-done): `add-rddf-session-status-cmd` (本次批准) **supersedes** 已批准 `add-session-progress-view` (P1, 2026-07-28) — 后者范围是前者的子集 (本提案更广: 表格 + BINDING_LINES + guide 推荐器整合)。Plan 阶段实施时跳过 `add-session-progress-view`, 仅实施 `add-rddf-session-status-cmd`。
>
> **bump 合并声明** (2026-08-02 design-done): `add-rddf-session-sub-phase-heartbeat` (本次批准) 与 `add-rddf-session-workflow-group` (本次批准) **合并为单一 schema v1→v2 bump PR** (`bump-sessions-schema-v2`), 一次同时支持 `sub_phase: str | null` + `workflow_group: str | null` 两个 optional 字段。**禁止拆为两次独立 bump**。Plan 阶段必须先实施 P0 (`fix-rddf-session-owner-stability`) 再启动本 PR。







































| [add-cross-repo-state-schemas](.rddf/improvements/add-cross-repo-state-schemas.md) | P1 | 2026-08-15 | guide-arch |

| [add-contract-lint-ci-gate](.rddf/improvements/add-contract-lint-ci-gate.md) | P1 | 2026-08-15 | guide-arch |

| [add-cross-repo-deps-orchestration](.rddf/improvements/add-cross-repo-deps-orchestration.md) | P1 | 2026-08-15 | guide-arch |

## 已实施
| [add-strict-human-approval-for-cross-repo-changes](.rddf/improvements/add-strict-human-approval-for-cross-repo-changes.md) | P1 | 2026-08-16 |
| [add-spoke-system-prompt-injection](.rddf/improvements/add-spoke-system-prompt-injection.md) | P1 | 2026-08-16 |
| [add-mcp-cross-repo-protocol](.rddf/improvements/add-mcp-cross-repo-protocol.md) | P1 | 2026-08-16 |
| [add-rdd-hub-cross-repo-federation](.rddf/improvements/add-rdd-hub-cross-repo-federation.md) | P1 | 2026-08-16 |
| [add-rdd-hub-bootstrap](.rddf/improvements/add-rdd-hub-bootstrap.md) | P0 | 2026-08-16 |
| [issue-driven-proposal-creation](.rddf/improvements/issue-driven-proposal-creation.md) | P1 | 2026-08-15 |
| [add-phase-role-model](.rddf/improvements/add-phase-role-model.md) | P1 | 2026-08-14 |
| [preserve-orchestrator-command-stdout](.rddf/improvements/preserve-orchestrator-command-stdout.md) | P1 | 2026-08-14 |
| [harden-plan-intake-bootstrap-and-design-gate-tests](.rddf/improvements/harden-plan-intake-bootstrap-and-design-gate-tests.md) | P1 | 2026-08-13 |
| [validate-feature-name](.rddf/improvements/validate-feature-name.md) | P1 | 2026-08-12 |
| [fix-feature-decision-design-phase](.rddf/improvements/fix-feature-decision-design-phase.md) | P1 | 2026-08-10 |
| [fix-proposal-approved-missing-after-archive](.rddf/improvements/fix-proposal-approved-missing-after-archive.md) | P1 | 2026-08-09 |
| [add-rdd-doctor-skill](.rddf/improvements/add-rdd-doctor-skill.md) | P1 | 2026-08-09 |
| [archive-cleanup-plan-files-extension](.rddf/improvements/archive-cleanup-plan-files-extension.md) | P2 | 2026-08-08 |
| [fix-design-proposal-review-approved-parsing](.rddf/improvements/fix-design-proposal-review-approved-parsing.md) | P0 | 2026-08-07 |
| [post-archive-cleanup-hook](.rddf/improvements/post-archive-cleanup-hook.md) | P0 | 2026-08-06 |
| [fix-rddf-init-broken-layout](.rddf/improvements/fix-rddf-init-broken-layout.md) | P1 | 2026-08-06 |
| [collect-l2-violation-count-on-archive](.rddf/improvements/collect-l2-violation-count-on-archive.md) | P2 | 2026-08-06 |
| [fix-tasks-md-archive-residue](.rddf/improvements/fix-tasks-md-archive-residue.md) | P1 | 2026-08-06 |
| [rddf-iteration-strict-schema](.rddf/improvements/rddf-iteration-strict-schema.md) | P1 | 2026-08-06 |
| [fix-rddf-status-corrupt-message](.rddf/improvements/fix-rddf-status-corrupt-message.md) | P1 | 2026-08-06 |
| [add-archive-post-commit-hook-and-force-flag](.rddf/improvements/add-archive-post-commit-hook-and-force-flag.md) | P0 | 2026-08-06 |
| [fix-archive-on-main-flow](.rddf/improvements/fix-archive-on-main-flow.md) | P0 | 2026-08-06 |
| [fix-archive-iteration-sync](.rddf/improvements/fix-archive-iteration-sync.md) | P0 | 2026-08-06 |
| [guide-ship-default-serial-execution](.rddf/improvements/guide-ship-default-serial-execution.md) | P1 | 2026-08-05 |
| [plan-quality-and-validation](.rddf/improvements/plan-quality-and-validation.md) | P0 | 2026-08-05 |
| [developer-experience-observability](.rddf/improvements/developer-experience-observability.md) | P2 | 2026-08-05 |
| [subagent-orchestrator-execution-strategy](.rddf/improvements/subagent-orchestrator-execution-strategy.md) | P0 | 2026-08-05 |
| [worktree-archive-workflow](.rddf/improvements/worktree-archive-workflow.md) | P0 | 2026-08-05 |
| [plan-execute-commit-policy-consistency](.rddf/improvements/plan-execute-commit-policy-consistency.md) | P1 | 2026-08-04 |
| [python-failures-baseline](.rddf/improvements/python-failures-baseline.md) | P3 | 2026-08-04 |
| [test-isolation-from-repo-state](.rddf/improvements/test-isolation-from-repo-state.md) | P2 | 2026-08-04 |
| [execute-gate-unified-regression](.rddf/improvements/execute-gate-unified-regression.md) | P2 | 2026-08-04 |
| [archive-history-keep-semantics](.rddf/improvements/archive-history-keep-semantics.md) | P2 | 2026-08-04 |
| [extract-rdd-env-check-from-guide-arch](.rddf/improvements/extract-rdd-env-check-from-guide-arch.md) | P1 | 2026-08-03 |
| [adr-create-interactive-drafting](.rddf/improvements/adr-create-interactive-drafting.md) | P1 | 2026-08-03 |
| [add-rddf-session-workflow-group](.rddf/improvements/add-rddf-session-workflow-group.md) | P2 | 2026-08-03 |
| [add-rddf-session-sub-phase-heartbeat](.rddf/improvements/add-rddf-session-sub-phase-heartbeat.md) | P1 | 2026-08-03 |
| [add-rddf-session-status-cmd](.rddf/improvements/add-rddf-session-status-cmd.md) | P2 | 2026-08-03 |
| [add-rddf-session-auto-archive-on-entry](.rddf/improvements/add-rddf-session-auto-archive-on-entry.md) | P1 | 2026-08-03 |
| [refine-plan-openspec-integration](.rddf/improvements/refine-plan-openspec-integration.md) | P1 | 2026-08-02 |
| [move-proposal-creation-to-design](.rddf/improvements/move-proposal-creation-to-design.md) | P1 | 2026-08-02 |
| [fix-wt-scanner-strip-bug-and-untracked-coverage](.rddf/improvements/fix-wt-scanner-strip-bug-and-untracked-coverage.md) | P1 | 2026-08-01 |
| [improve-ship-done-cleanup-orphan-sessions](.rddf/improvements/improve-ship-done-cleanup-orphan-sessions.md) | P2 | 2026-08-01 |
| [fix-scanner-fallback-and-orphan-archival](.rddf/improvements/fix-scanner-fallback-and-orphan-archival.md) | P1 | 2026-08-01 |
| [check-project-setup](.rddf/improvements/check-project-setup.md) | P1 | 2026-08-01 |
| [fix-mark-approved-completed-date-drift](.rddf/improvements/fix-mark-approved-completed-date-drift.md) | P2 | 2026-08-01 |
| [fix-ship-plan-skill-use-fallback](.rddf/improvements/fix-ship-plan-skill-use-fallback.md) | P1 | 2026-08-01 |
| [fix-deps-render-report-multi-candidate](.rddf/improvements/fix-deps-render-report-multi-candidate.md) | P1 | 2026-08-01 |
| [fix-update-proposal-status-data-loss](.rddf/improvements/fix-update-proposal-status-data-loss.md) | P0 | 2026-08-01 |

| 提案 | 优先级 | 完成时间 |
|------|--------|----------|
| [fix-generator-scope-extraction](.rddf/improvements/fix-generator-scope-extraction.md) | P1 | 2026-08-15 |
| [complete-third-party-replay-and-upstream-reporting](.rddf/improvements/complete-third-party-replay-and-upstream-reporting.md) | P0 | 2026-08-13 |
| [sync-changelog-unreleased](.rddf/improvements/sync-changelog-unreleased.md) | P1 | 2026-08-13 |
| [add-roadmap-proposal-guidance](.rddf/improvements/add-roadmap-proposal-guidance.md) | P1 | 2026-08-13 |
| [migrate-improvements-to-rddf-namespace](.rddf/improvements/migrate-improvements-to-rddf-namespace.md) | P0 | 2026-08-12 |
| [add-proposal-how-leakage-warning](.rddf/improvements/add-proposal-how-leakage-warning.md) | P1 | 2026-08-12 |
| [wire-design-content-review-gate](.rddf/improvements/wire-design-content-review-gate.md) | P1 | 2026-08-12 |
| [wire-plan-done-quality-gates](.rddf/improvements/wire-plan-done-quality-gates.md) | P0 | 2026-08-12 |
| [fix-ship-archive-resolve-lib-path](.rddf/improvements/fix-ship-archive-resolve-lib-path.md) | P1 | 2026-08-07 |
| [fix-bootstrap-fallback-paths](.rddf/improvements/fix-bootstrap-fallback-paths.md) | P1 | 2026-08-07 |
| [add-env-cache-arch-discovery](.rddf/improvements/add-env-cache-arch-discovery.md) | P2 | 2026-08-07 |
| [add-known-failures-baseline](.rddf/improvements/add-known-failures-baseline.md) | P3 | 2026-08-04 |
| [add-skill-registration-checklist](.rddf/improvements/add-skill-registration-checklist.md) | P2 | 2026-08-04 |
| [fix-execute-change-name-persistence](.rddf/improvements/fix-execute-change-name-persistence.md) | P1 | 2026-08-04 |
| [fix-rddf-session-owner-stability](.rddf/improvements/fix-rddf-session-owner-stability.md) | P0 | 2026-08-03 |
| [fix-add-improve-initial-prompt-ux](.rddf/improvements/fix-add-improve-initial-prompt-ux.md) | P1 | 2026-07-31 |
| [fix-plan-deps-candidates-import-guard](.rddf/improvements/fix-plan-deps-candidates-import-guard.md) | P0 | 2026-07-31 |
| [fix-rddf-session-lifecycle-binding](.rddf/improvements/fix-rddf-session-lifecycle-binding.md) | P1 | 2026-07-31 |
| [fix-test-infrastructure-and-skill-registration](.rddf/improvements/fix-test-infrastructure-and-skill-registration.md) | P2 | 2026-07-31 |
| [deps-driven-execution-mode](.rddf/improvements/deps-driven-execution-mode.md) | P2 | 2026-07-30 |
| [guide-ship-quick-finish](.rddf/improvements/guide-ship-quick-finish.md) | P2 | 2026-07-29 |
| [fix-plan-done-gate-zero-stale-count](.rddf/improvements/fix-plan-done-gate-zero-stale-count.md) | P2 | 2026-07-29 |
| [fix-guide-ship-archive-bats](.rddf/improvements/fix-guide-ship-archive-bats.md) | P2 | 2026-07-29 |
| [fix-doc-truth-sync](.rddf/improvements/fix-doc-truth-sync.md) | P2 | 2026-07-29 |
| [archive-cleanup-plan-files](.rddf/improvements/archive-cleanup-plan-files.md) | P2 | 2026-07-29 |
| [add-proposal-defer-support](.rddf/improvements/add-proposal-defer-support.md) | P2 | 2026-07-29 |
| [prompt-worktree-cleanup-before-stage](.rddf/improvements/prompt-worktree-cleanup-before-stage.md) | P3 | 2026-07-29 |
| [detect-suggestions-approved-inconsistency](.rddf/improvements/detect-suggestions-approved-inconsistency.md) | P3 | 2026-07-29 |
| [filter-guide-ship-when-no-changes](.rddf/improvements/filter-guide-ship-when-no-changes.md) | P2 | 2026-07-29 |
| [fix-scan-state-integer-comparison](.rddf/improvements/fix-scan-state-integer-comparison.md) | P2 | 2026-07-29 |
| [pre-checkout-warning](.rddf/improvements/pre-checkout-warning.md) | P2 | 2026-07-29 |
| [archive-cleanup-plan-handoff](.rddf/improvements/archive-cleanup-plan-handoff.md) | P1 | 2026-07-29 |
| [add-proposal-deps-and-features](.rddf/improvements/add-proposal-deps-and-features.md) | P1 | 2026-07-29 |
| [add-change-content-review](.rddf/improvements/add-change-content-review.md) | P1 | 2026-07-29 |
| [guide-plan-fallback-direct-create](.rddf/improvements/guide-plan-fallback-direct-create.md) | P1 | 2026-07-29 |
| [fix-arch-handoff-stale-detection](.rddf/improvements/fix-arch-handoff-stale-detection.md) | P1 | 2026-07-29 |
| [adr-creation-architecture-gate](.rddf/improvements/adr-creation-architecture-gate.md) | P1 | 2026-07-29 |
| [sync-approved-to-suggestions](.rddf/improvements/sync-approved-to-suggestions.md) | P1 | 2026-07-29 |
| [fix-skill-tool-cache](.rddf/improvements/fix-skill-tool-cache.md) | P1 | 2026-07-29 |
| [archive-gate-incomplete-tasks](.rddf/improvements/archive-gate-incomplete-tasks.md) | P1 | 2026-07-29 |
| [ship-incomplete-archive-change-fallback](.rddf/improvements/ship-incomplete-archive-change-fallback.md) | P1 | 2026-07-29 |
| [ship-delete-branch-safety](.rddf/improvements/ship-delete-branch-safety.md) | P1 | 2026-07-29 |
| [fix-rddf-session-owner-cross-call](.rddf/improvements/fix-rddf-session-owner-cross-call.md) | P1 | 2026-07-29 |
| [RDDF-0001-fix-rddf-session-import-path](.rddf/improvements/RDDF-0001-fix-rddf-session-import-path.md) | P1 | 2026-07-29 |
| [add-config-validation](.rddf/improvements/add-config-validation.md) | P0 | 2026-07-28 |
| [add-file-size-quality-gate](.rddf/improvements/add-file-size-quality-gate.md) | P2 | 2026-07-28 |
| [add-full-regression-gate](.rddf/improvements/add-full-regression-gate.md) | P0 | 2026-07-28 |
| [add-heartbeat-config](.rddf/improvements/add-heartbeat-config.md) | P1 | 2026-07-28 |
| [add-openspec-gate](.rddf/improvements/add-openspec-gate.md) | P0 | 2026-07-28 |
| [add-parent-feature-param](.rddf/improvements/add-parent-feature-param.md) | P0 | 2026-07-28 |
| [add-plugin-loader-tests](.rddf/improvements/add-plugin-loader-tests.md) | P2 | 2026-07-28 |
| [add-progressive-linting](.rddf/improvements/add-progressive-linting.md) | P2 | 2026-07-28 |
| [add-propose-content-review](.rddf/improvements/add-propose-content-review.md) | P1 | 2026-07-28 |
| [add-rddf-concurrency-tests](.rddf/improvements/add-rddf-concurrency-tests.md) | P1 | 2026-07-28 |
| [add-session-progress-view](.rddf/improvements/add-session-progress-view.md) | P1 | 2026-07-28 |
| [add-workflow-reflect-engine](.rddf/improvements/add-workflow-reflect-engine.md) | P1 | 2026-07-28 |
| [add-workflow-synthesizer](.rddf/improvements/add-workflow-synthesizer.md) | P0 | 2026-07-28 |
| [agent-completion-contract](.rddf/improvements/agent-completion-contract.md) | P1 | 2026-07-28 |
| [archive-cleanup-working-tree](.rddf/improvements/archive-cleanup-working-tree.md) | P1 | 2026-07-28 |
| [archive-iteration-sync](.rddf/improvements/archive-iteration-sync.md) | P0 | 2026-07-28 |
| [archive-update-proposal-status](.rddf/improvements/archive-update-proposal-status.md) | P1 | 2026-07-28 |
| [audit-attach-detach-calls](.rddf/improvements/audit-attach-detach-calls.md) | P0 | 2026-07-28 |
| [auto-skip-archived-proposals](.rddf/improvements/auto-skip-archived-proposals.md) | P0 | 2026-07-28 |
| [auto-sync-adr-index](.rddf/improvements/auto-sync-adr-index.md) | P2 | 2026-07-28 |
| [auto-wave-scheduler](.rddf/improvements/auto-wave-scheduler.md) | P0 | 2026-07-28 |
| [enforce-hook-symmetry](.rddf/improvements/enforce-hook-symmetry.md) | P2 | 2026-07-28 |
| [fix-append-approved-output](.rddf/improvements/fix-append-approved-output.md) | P2 | 2026-07-28 |
| [fix-arch-env-check-adr-count-bug](.rddf/improvements/fix-arch-env-check-adr-count-bug.md) | P2 | 2026-07-28 |
| [fix-attach-detach-symmetry](.rddf/improvements/fix-attach-detach-symmetry.md) | P1 | 2026-07-28 |
| [fix-deps-render-empty-candidates](.rddf/improvements/fix-deps-render-empty-candidates.md) | P2 | 2026-07-28 |
| [fix-lsp-dash-bridge](.rddf/improvements/fix-lsp-dash-bridge.md) | P0 | 2026-07-28 |
| [fix-mark-approved-completed](.rddf/improvements/fix-mark-approved-completed.md) | P1 | 2026-07-28 |
| [fix-rddf-schema-validation](.rddf/improvements/fix-rddf-schema-validation.md) | P0 | 2026-07-28 |
| [fix-scan-state-binding](.rddf/improvements/fix-scan-state-binding.md) | P0 | 2026-07-28 |
| [fix-ship-lightweight-wt-path-pollution](.rddf/improvements/fix-ship-lightweight-wt-path-pollution.md) | P2 | 2026-07-28 |
| [fix-silent-exception](.rddf/improvements/fix-silent-exception.md) | P0 | 2026-07-28 |
| [fix-stale-suggestions-warning](.rddf/improvements/fix-stale-suggestions-warning.md) | P2 | 2026-07-28 |
| [guide-cross-validate](.rddf/improvements/guide-cross-validate.md) | P1 | 2026-07-28 |
| [guide-plan-noninteractive](.rddf/improvements/guide-plan-noninteractive.md) | P0 | 2026-07-28 |
| [improve-openspec-test-change-support](.rddf/improvements/improve-openspec-test-change-support.md) | P0 | 2026-07-28 |
| [parallel-oracle-review](.rddf/improvements/parallel-oracle-review.md) | P1 | 2026-07-28 |
| [parallel-wave-execution](.rddf/improvements/parallel-wave-execution.md) | P1 | 2026-07-28 |
| [preship-dirty-check](.rddf/improvements/preship-dirty-check.md) | P2 | 2026-07-28 |
| [proposal-approval-pipeline](.rddf/improvements/proposal-approval-pipeline.md) | P0 | 2026-07-28 |
| [propose-quality-autohook](.rddf/improvements/propose-quality-autohook.md) | P0 | 2026-07-28 |
| [rddf-sessions-gc](.rddf/improvements/rddf-sessions-gc.md) | P2 | 2026-07-28 |
| [relocate-loop-engine](.rddf/improvements/relocate-loop-engine.md) | P2 | 2026-07-28 |
| [remove-ci-redundant-bats](.rddf/improvements/remove-ci-redundant-bats.md) | P1 | 2026-07-28 |
| [skill-name-auto-resolve](.rddf/improvements/skill-name-auto-resolve.md) | P2 | 2026-07-28 |
| [split-iteration-module](.rddf/improvements/split-iteration-module.md) | P1 | 2026-07-28 |
| [split-rddf-god-class](.rddf/improvements/split-rddf-god-class.md) | P2 | 2026-07-28 |
| [task-parallel-throttle](.rddf/improvements/task-parallel-throttle.md) | P1 | 2026-07-28 |
| [unify-session-kind-naming](.rddf/improvements/unify-session-kind-naming.md) | P0 | 2026-07-28 |
| [unify-test-entry-points](.rddf/improvements/unify-test-entry-points.md) | P1 | 2026-07-28 |
| [update-adr-index](.rddf/improvements/update-adr-index.md) | P2 | 2026-07-28 |
| [update-agents-module-map](.rddf/improvements/update-agents-module-map.md) | P1 | 2026-07-28 |
| [update-guide-plan-format](.rddf/improvements/update-guide-plan-format.md) | P1 | 2026-07-28 |
| [fix-scan-state-bats](.rddf/improvements/fix-scan-state-bats.md) | P2 | 2026-07-23 |
| [complete-third-party-replay-and-upstream-reporting](.rddf/improvements/complete-third-party-replay-and-upstream-reporting.md) | P0 | 2026-08-13 |
