# 已批准提案（Plan 阶段输入）

> plan 阶段输入。guide-plan propose 从此处读取，按链接打开对应 `improvements/xxx.md` 创建 change。

> **supersedes** (2026-07-28): 原始设计（propose Phase 4 自动末尾 + 写 `.rddf/state/propose-review.json`）已被后续 commits 修订：
> - `b4ad917` — relocate to arch Phase 5.5 human-in-loop 节点
> - `a99017b` — refine wording `修复` → `修订`（关联提案 add-change-content-review）
> - 当前最终设计：arch Phase 5.5 在 suggestions→approved 迁移界面 y/n/d/s 决策前，Oracle 终端展示 3 级报告（pass/warn/block），不持久化。已实现的孤儿 `skills/_lib/propose_content_review.py` 已删除（`311d497`）。

## 已批准提案

| 提案 | 优先级 | 批准时间 | 批准者 |
|------|--------|----------|----------|

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


















| [add-env-cache-arch-discovery](improvements/add-env-cache-arch-discovery.md) | P2 | 2026-08-07 | guide-arch |

## 已实施
| [post-archive-cleanup-hook](improvements/post-archive-cleanup-hook.md) | P0 | 2026-08-06 |
| [fix-rddf-init-broken-layout](improvements/fix-rddf-init-broken-layout.md) | P1 | 2026-08-06 |
| [collect-l2-violation-count-on-archive](improvements/collect-l2-violation-count-on-archive.md) | P2 | 2026-08-06 |
| [fix-tasks-md-archive-residue](improvements/fix-tasks-md-archive-residue.md) | P1 | 2026-08-06 |
| [rddf-iteration-strict-schema](improvements/rddf-iteration-strict-schema.md) | P1 | 2026-08-06 |
| [fix-rddf-status-corrupt-message](improvements/fix-rddf-status-corrupt-message.md) | P1 | 2026-08-06 |
| [add-archive-post-commit-hook-and-force-flag](improvements/add-archive-post-commit-hook-and-force-flag.md) | P0 | 2026-08-06 |
| [fix-archive-on-main-flow](improvements/fix-archive-on-main-flow.md) | P0 | 2026-08-06 |
| [fix-archive-iteration-sync](improvements/fix-archive-iteration-sync.md) | P0 | 2026-08-06 |
| [guide-ship-default-serial-execution](improvements/guide-ship-default-serial-execution.md) | P1 | 2026-08-05 |
| [plan-quality-and-validation](improvements/plan-quality-and-validation.md) | P0 | 2026-08-05 |
| [developer-experience-observability](improvements/developer-experience-observability.md) | P2 | 2026-08-05 |
| [subagent-orchestrator-execution-strategy](improvements/subagent-orchestrator-execution-strategy.md) | P0 | 2026-08-05 |
| [worktree-archive-workflow](improvements/worktree-archive-workflow.md) | P0 | 2026-08-05 |
| [plan-execute-commit-policy-consistency](improvements/plan-execute-commit-policy-consistency.md) | P1 | 2026-08-04 |
| [python-failures-baseline](improvements/python-failures-baseline.md) | P3 | 2026-08-04 |
| [test-isolation-from-repo-state](improvements/test-isolation-from-repo-state.md) | P2 | 2026-08-04 |
| [execute-gate-unified-regression](improvements/execute-gate-unified-regression.md) | P2 | 2026-08-04 |
| [archive-history-keep-semantics](improvements/archive-history-keep-semantics.md) | P2 | 2026-08-04 |
| [extract-rdd-env-check-from-guide-arch](improvements/extract-rdd-env-check-from-guide-arch.md) | P1 | 2026-08-03 |
| [adr-create-interactive-drafting](improvements/adr-create-interactive-drafting.md) | P1 | 2026-08-03 |
| [add-rddf-session-workflow-group](improvements/add-rddf-session-workflow-group.md) | P2 | 2026-08-03 |
| [add-rddf-session-sub-phase-heartbeat](improvements/add-rddf-session-sub-phase-heartbeat.md) | P1 | 2026-08-03 |
| [add-rddf-session-status-cmd](improvements/add-rddf-session-status-cmd.md) | P2 | 2026-08-03 |
| [add-rddf-session-auto-archive-on-entry](improvements/add-rddf-session-auto-archive-on-entry.md) | P1 | 2026-08-03 |
| [refine-plan-openspec-integration](improvements/refine-plan-openspec-integration.md) | P1 | 2026-08-02 |
| [move-proposal-creation-to-design](improvements/move-proposal-creation-to-design.md) | P1 | 2026-08-02 |
| [fix-wt-scanner-strip-bug-and-untracked-coverage](improvements/fix-wt-scanner-strip-bug-and-untracked-coverage.md) | P1 | 2026-08-01 |
| [improve-ship-done-cleanup-orphan-sessions](improvements/improve-ship-done-cleanup-orphan-sessions.md) | P2 | 2026-08-01 |
| [fix-scanner-fallback-and-orphan-archival](improvements/fix-scanner-fallback-and-orphan-archival.md) | P1 | 2026-08-01 |
| [check-project-setup](improvements/check-project-setup.md) | P1 | 2026-08-01 |
| [fix-mark-approved-completed-date-drift](improvements/fix-mark-approved-completed-date-drift.md) | P2 | 2026-08-01 |
| [fix-ship-plan-skill-use-fallback](improvements/fix-ship-plan-skill-use-fallback.md) | P1 | 2026-08-01 |
| [fix-deps-render-report-multi-candidate](improvements/fix-deps-render-report-multi-candidate.md) | P1 | 2026-08-01 |
| [fix-update-proposal-status-data-loss](improvements/fix-update-proposal-status-data-loss.md) | P0 | 2026-08-01 |

| 提案 | 优先级 | 完成时间 |
|------|--------|----------|
| [add-known-failures-baseline](improvements/add-known-failures-baseline.md) | P3 | 2026-08-04 |
| [add-skill-registration-checklist](improvements/add-skill-registration-checklist.md) | P2 | 2026-08-04 |
| [fix-execute-change-name-persistence](improvements/fix-execute-change-name-persistence.md) | P1 | 2026-08-04 |
| [fix-rddf-session-owner-stability](improvements/fix-rddf-session-owner-stability.md) | P0 | 2026-08-03 |
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
