# spec 残留普查台账（机器生成）

> 生成器：`skills/rdd-doctor/scripts/gen_spec_residue_census.py` — **不要手编辑本文件**。
> 台账 = **清理待办清单**（`disposition=unset` 的行归零 = Phase 1 的完成判据）+ 可复算基线 + 证据。
> 签批记录的权威落点**不是这里** —— 见下方「既有签批」段。

## 口径（冻结常量）

扫描根 `openspec/specs/*/spec.md`（恰为一层，非递归；**不扫** `openspec/changes/**`）。
normative 段 = `### Requirement:` 标题+正文 / `#### Scenario:` 标题+正文 / 正文内 fenced code block；
**不含** `## Purpose` 等散文段。命中按**块**归类。

词边界：`(?<![\w-])(guide-arch|guide-design|guide-plan|guide-ship|guide-spec|ac-verifier)(?![\w-])`
（token 后不得再跟 `-`，否则 `guide-plan-quick-finish` 这类**提案名**会被前缀命中）。

| `code_block_in` × `title_in` | 命中处数 | 命中块数 | 命中 spec 份数 |
|---|---|---|---|
| `True` × `True` ← 选定（冻结） | 333 | 181 | 46 |
| `True` × `False` | 310 | 180 | 46 |
| `False` × `True` | 331 | 180 | 45 |
| `False` × `False` | 308 | 179 | 45 |

## 基线（选定口径）

- 扫描 spec 文件：**165** 份
- 命中实例：**333** 处（其中未被豁免 **191** 处）
- 命中块：**181** 块
- 命中 spec：**46** 份
- `stale allow`（过期豁免）：**0** 处

## 既有签批（不由本台账合并）

| 批次 | 台账 | 覆盖 spec |
|---|---|---|
| 第一批（13 份 / 34 处） | `.rddf/reviews/spec-residue-census-2026-11-20.md` | 见该文件 |
| 第二批（5 份 / 37 处） | `.rddf/reviews/spec-residue-census-2026-11-20-batch2.md` | 见该文件 |

这 18 份已**全部处置完毕**（0 个命中行）—— 逐行判定与标注见
`.rddf/reviews/spec-residue-align-18-2026-11-20.md`（change `align-spec-residue-prior-18`）。

## 残留清单

| file | line | requirement_title | matched_token | category | disposition | owner | signoff | date |
|---|---|---|---|---|---|---|---|---|
| openspec/specs/archive-auto-commit/spec.md | 93 | `rdd-builder` P3 lightweight mode MUST also call helper | guide-ship | unclassified | unset |  |  |  |
| openspec/specs/archive-gate-verification/spec.md | 10 | Archive SHALL remain owned by the builder stage | guide-ship | unclassified | unset |  |  |  |
| openspec/specs/archive-gate-verification/spec.md | 70 | Gate precedence SHALL be deterministic across skip, strict, bypass, and feature options | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/archive-gate-verification/spec.md | 99 | Gate precedence SHALL be deterministic across skip, strict, bypass, and feature options | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/archive-gate-verification/spec.md | 101 | Gate precedence SHALL be deterministic across skip, strict, bypass, and feature options | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/archive-gate-verification/spec.md | 109 | Direct archive fallback SHALL write structured verdict to the canonical cache | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/archive-gate-verification/spec.md | 109 | Direct archive fallback SHALL write structured verdict to the canonical cache | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/archive-gate-verification/spec.md | 114 | Direct archive fallback SHALL write structured verdict to the canonical cache | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/archive-gate-verification/spec.md | 115 | Direct archive fallback SHALL write structured verdict to the canonical cache | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/archive-gate-verification/spec.md | 126 | Direct archive fallback SHALL write structured verdict to the canonical cache | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/archive-gate-verification/spec.md | 127 | Direct archive fallback SHALL write structured verdict to the canonical cache | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/complete-project-yaml-config-gaps/spec.md | 70 | verifier-explicit-runner-override | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/complete-project-yaml-config-gaps/spec.md | 179 | verifier-hook-provider-routing | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/complete-project-yaml-config-gaps/spec.md | 203 | guide-ship-phase-1-detect-lightweight | guide-ship | unclassified | unset |  |  |  |
| openspec/specs/complete-project-yaml-config-gaps/spec.md | 297 | zero-regression-backward-compat | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/cross-repo-deps/spec.md | 126 | Hub dependency issue creation | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/cross-repo-federation/spec.md | 119 | Design Gate Integration | guide-design | unclassified | unset |  |  |  |
| openspec/specs/dashboard-verification-status/spec.md | 50 | Verification status schema SHALL be explicit and versioned | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/dashboard-verification-status/spec.md | 50 | Verification status schema SHALL be explicit and versioned | guide-ship | unclassified | unset |  |  |  |
| openspec/specs/doc-architecture-v4-sync/spec.md | 8 | user-facing-docs-reflect-v4-four-stage | guide-arch | unclassified | unset |  |  |  |
| openspec/specs/doc-architecture-v4-sync/spec.md | 8 | user-facing-docs-reflect-v4-four-stage | guide-design | unclassified | unset |  |  |  |
| openspec/specs/doc-architecture-v4-sync/spec.md | 8 | user-facing-docs-reflect-v4-four-stage | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/doc-architecture-v4-sync/spec.md | 8 | user-facing-docs-reflect-v4-four-stage | guide-ship | unclassified | unset |  |  |  |
| openspec/specs/doc-architecture-v4-sync/spec.md | 8 | user-facing-docs-reflect-v4-four-stage | guide-spec | unclassified | unset |  |  |  |
| openspec/specs/doc-architecture-v4-sync/spec.md | 37 | user-facing-docs-reflect-v4-four-stage | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/doc-architecture-v4-sync/spec.md | 37 | user-facing-docs-reflect-v4-four-stage | guide-ship | unclassified | unset |  |  |  |
| openspec/specs/doc-architecture-v4-sync/spec.md | 41 | architectural-docs-no-deprecated-guide-star-skill-names | guide-arch | unclassified | unset |  |  |  |
| openspec/specs/doc-architecture-v4-sync/spec.md | 41 | architectural-docs-no-deprecated-guide-star-skill-names | guide-design | unclassified | unset |  |  |  |
| openspec/specs/doc-architecture-v4-sync/spec.md | 41 | architectural-docs-no-deprecated-guide-star-skill-names | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/doc-architecture-v4-sync/spec.md | 41 | architectural-docs-no-deprecated-guide-star-skill-names | guide-ship | unclassified | unset |  |  |  |
| openspec/specs/doc-architecture-v4-sync/spec.md | 41 | architectural-docs-no-deprecated-guide-star-skill-names | guide-spec | unclassified | unset |  |  |  |
| openspec/specs/doc-architecture-v4-sync/spec.md | 47 | architectural-docs-no-deprecated-guide-star-skill-names | guide-arch | unclassified | unset |  |  |  |
| openspec/specs/doc-architecture-v4-sync/spec.md | 47 | architectural-docs-no-deprecated-guide-star-skill-names | guide-design | unclassified | unset |  |  |  |
| openspec/specs/doc-architecture-v4-sync/spec.md | 47 | architectural-docs-no-deprecated-guide-star-skill-names | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/doc-architecture-v4-sync/spec.md | 47 | architectural-docs-no-deprecated-guide-star-skill-names | guide-ship | unclassified | unset |  |  |  |
| openspec/specs/doc-architecture-v4-sync/spec.md | 61 | architectural-docs-no-deprecated-guide-star-skill-names | guide-design | unclassified | unset |  |  |  |
| openspec/specs/doc-architecture-v4-sync/spec.md | 62 | architectural-docs-no-deprecated-guide-star-skill-names | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/doc-architecture-v4-sync/spec.md | 62 | architectural-docs-no-deprecated-guide-star-skill-names | guide-ship | unclassified | unset |  |  |  |
| openspec/specs/doc-architecture-v4-sync/spec.md | 71 | architectural-docs-no-deprecated-guide-star-skill-names | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/doc-architecture-v4-sync/spec.md | 75 | architectural-docs-no-deprecated-guide-star-skill-names | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/doc-architecture-v4-sync/spec.md | 89 | rdd-arch-skill-md-rename-history-bug-fixed | guide-arch | unclassified | unset |  |  |  |
| openspec/specs/doc-architecture-v4-sync/spec.md | 91 | rdd-arch-skill-md-rename-history-bug-fixed | guide-arch | unclassified | unset |  |  |  |
| openspec/specs/doc-architecture-v4-sync/spec.md | 94 | rdd-arch-skill-md-rename-history-bug-fixed | guide-arch | unclassified | unset |  |  |  |
| openspec/specs/doc-architecture-v4-sync/spec.md | 112 | rdd-arch-skill-md-describes-v4-four-stage | guide-design | unclassified | unset |  |  |  |
| openspec/specs/doc-architecture-v4-sync/spec.md | 112 | rdd-arch-skill-md-describes-v4-four-stage | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/doc-architecture-v4-sync/spec.md | 112 | rdd-arch-skill-md-describes-v4-four-stage | guide-ship | unclassified | unset |  |  |  |
| openspec/specs/doc-architecture-v4-sync/spec.md | 129 | skills-directory-has-5-rdd-stage-skills-and-0-guide-star-skill-subdirs | guide-arch | unclassified | unset |  |  |  |
| openspec/specs/doc-architecture-v4-sync/spec.md | 129 | skills-directory-has-5-rdd-stage-skills-and-0-guide-star-skill-subdirs | guide-design | unclassified | unset |  |  |  |
| openspec/specs/doc-architecture-v4-sync/spec.md | 129 | skills-directory-has-5-rdd-stage-skills-and-0-guide-star-skill-subdirs | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/doc-architecture-v4-sync/spec.md | 129 | skills-directory-has-5-rdd-stage-skills-and-0-guide-star-skill-subdirs | guide-ship | unclassified | unset |  |  |  |
| openspec/specs/doc-architecture-v4-sync/spec.md | 129 | skills-directory-has-5-rdd-stage-skills-and-0-guide-star-skill-subdirs | guide-spec | unclassified | unset |  |  |  |
| openspec/specs/doc-truth-sync/spec.md | 85 | install-usage-readme-metadata-sync | guide-arch | unclassified | unset |  |  |  |
| openspec/specs/doc-truth-sync/spec.md | 85 | install-usage-readme-metadata-sync | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/doc-truth-sync/spec.md | 133 | doc-contract-tests-required | guide-spec | unclassified | unset |  |  |  |
| openspec/specs/doc-truth-sync/spec.md | 133 | doc-contract-tests-required | guide-spec | unclassified | unset |  |  |  |
| openspec/specs/doc-truth-sync/spec.md | 134 | doc-contract-tests-required | guide-arch | unclassified | unset |  |  |  |
| openspec/specs/doc-truth-sync/spec.md | 134 | doc-contract-tests-required | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/doc-truth-sync/spec.md | 205 | doc-contract-tests-required | guide-spec | unclassified | unset |  |  |  |
| openspec/specs/doc-truth-sync/spec.md | 208 | doc-contract-tests-required | guide-spec | unclassified | unset |  |  |  |
| openspec/specs/doc-truth-sync/spec.md | 243 | doc-surfaces-share-truth-source | guide-ship | unclassified | unset |  |  |  |
| openspec/specs/doc-truth-sync/spec.md | 246 | doc-surfaces-share-truth-source | guide-ship | unclassified | unset |  |  |  |
| openspec/specs/doc-truth-sync/spec.md | 247 | doc-surfaces-share-truth-source | guide-ship | unclassified | unset |  |  |  |
| openspec/specs/docs-v4-sync-scope-followup/spec.md | 14 | docs-ONBOARDING-md-reflects-v4 | guide-arch | unclassified | unset |  |  |  |
| openspec/specs/docs-v4-sync-scope-followup/spec.md | 14 | docs-ONBOARDING-md-reflects-v4 | guide-design | unclassified | unset |  |  |  |
| openspec/specs/docs-v4-sync-scope-followup/spec.md | 14 | docs-ONBOARDING-md-reflects-v4 | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/docs-v4-sync-scope-followup/spec.md | 14 | docs-ONBOARDING-md-reflects-v4 | guide-ship | unclassified | unset |  |  |  |
| openspec/specs/docs-v4-sync-scope-followup/spec.md | 14 | docs-ONBOARDING-md-reflects-v4 | guide-spec | unclassified | unset |  |  |  |
| openspec/specs/docs-v4-sync-scope-followup/spec.md | 20 | docs-ONBOARDING-md-reflects-v4 | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/docs-v4-sync-scope-followup/spec.md | 22 | docs-ONBOARDING-md-reflects-v4 | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/docs-v4-sync-scope-followup/spec.md | 24 | docs-ONBOARDING-md-reflects-v4 | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/docs-v4-sync-scope-followup/spec.md | 25 | docs-ONBOARDING-md-reflects-v4 | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/docs-v4-sync-scope-followup/spec.md | 42 | docs-architecture-improvement-check-mechanisms-no-dead-links | guide-ship | unclassified | unset |  |  |  |
| openspec/specs/docs-v4-sync-scope-followup/spec.md | 46 | docs-architecture-improvement-check-mechanisms-no-dead-links | guide-ship | unclassified | unset |  |  |  |
| openspec/specs/docs-v4-sync-scope-followup/spec.md | 52 | skills-INSTALL-md-no-guide-star-skill-references | guide-design | unclassified | unset |  |  |  |
| openspec/specs/docs-v4-sync-scope-followup/spec.md | 52 | skills-INSTALL-md-no-guide-star-skill-references | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/docs-v4-sync-scope-followup/spec.md | 52 | skills-INSTALL-md-no-guide-star-skill-references | guide-ship | unclassified | unset |  |  |  |
| openspec/specs/docs-v4-sync-scope-followup/spec.md | 56 | skills-INSTALL-md-no-guide-star-skill-references | guide-design | unclassified | unset |  |  |  |
| openspec/specs/docs-v4-sync-scope-followup/spec.md | 56 | skills-INSTALL-md-no-guide-star-skill-references | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/docs-v4-sync-scope-followup/spec.md | 56 | skills-INSTALL-md-no-guide-star-skill-references | guide-ship | unclassified | unset |  |  |  |
| openspec/specs/docs-v4-sync-scope-followup/spec.md | 67 | docs-architecture-skills-and-handoff-no-deleted-path-examples | guide-arch | unclassified | unset |  |  |  |
| openspec/specs/docs-v4-sync-scope-followup/spec.md | 73 | docs-architecture-skills-and-handoff-no-deleted-path-examples | guide-arch | unclassified | unset |  |  |  |
| openspec/specs/docs-v4-sync-scope-followup/spec.md | 85 | doc-contract-test-extended-to-all-architecture-docs | guide-arch | unclassified | unset |  |  |  |
| openspec/specs/docs-v4-sync-scope-followup/spec.md | 91 | doc-contract-test-extended-to-all-architecture-docs | guide-arch | unclassified | unset |  |  |  |
| openspec/specs/docs-v4-sync-scope-followup/spec.md | 91 | doc-contract-test-extended-to-all-architecture-docs | guide-design | unclassified | unset |  |  |  |
| openspec/specs/docs-v4-sync-scope-followup/spec.md | 91 | doc-contract-test-extended-to-all-architecture-docs | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/docs-v4-sync-scope-followup/spec.md | 91 | doc-contract-test-extended-to-all-architecture-docs | guide-ship | unclassified | unset |  |  |  |
| openspec/specs/docs-v4-sync-scope-followup/spec.md | 91 | doc-contract-test-extended-to-all-architecture-docs | guide-spec | unclassified | unset |  |  |  |
| openspec/specs/docs-v4-sync-scope-followup/spec.md | 97 | doc-contract-test-extended-to-all-architecture-docs | guide-design | unclassified | unset |  |  |  |
| openspec/specs/docs-v4-sync-scope-followup/spec.md | 97 | doc-contract-test-extended-to-all-architecture-docs | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/docs-v4-sync-scope-followup/spec.md | 97 | doc-contract-test-extended-to-all-architecture-docs | guide-ship | unclassified | unset |  |  |  |
| openspec/specs/general/spec.md | 127 | general-docs-match-code | guide-arch | unclassified | unset |  |  |  |
| openspec/specs/general/spec.md | 145 | general-docs-match-code | guide-arch | unclassified | unset |  |  |  |
| openspec/specs/general/spec.md | 146 | general-docs-match-code | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/general/spec.md | 147 | general-docs-match-code | guide-spec | unclassified | unset |  |  |  |
| openspec/specs/inline-ac-verifier-into-rdd-verifier/spec.md | 10 | rdd-verifier SHALL self-contain its LLM verification protocol | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/inline-ac-verifier-into-rdd-verifier/spec.md | 19 | rdd-verifier SHALL self-contain its LLM verification protocol | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/inline-ac-verifier-into-rdd-verifier/spec.md | 56 | rdd-verifier verdict reasoning SHALL embed heuristic classifier keywords | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/inline-ac-verifier-into-rdd-verifier/spec.md | 63 | rdd-verifier verdict reasoning SHALL embed heuristic classifier keywords | guide-ship | unclassified | unset |  |  |  |
| openspec/specs/inline-ac-verifier-into-rdd-verifier/spec.md | 98 | archive_gate_check SHALL NOT shell out to ac-verifier | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/inline-ac-verifier-into-rdd-verifier/spec.md | 100 | archive_gate_check SHALL NOT shell out to ac-verifier | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/inline-ac-verifier-into-rdd-verifier/spec.md | 146 | ac-verifier SHALL be marked deprecated | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/inline-ac-verifier-into-rdd-verifier/spec.md | 148 | ac-verifier SHALL be marked deprecated | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/inline-ac-verifier-into-rdd-verifier/spec.md | 148 | ac-verifier SHALL be marked deprecated | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/inline-ac-verifier-into-rdd-verifier/spec.md | 150 | ac-verifier SHALL be marked deprecated | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/inline-ac-verifier-into-rdd-verifier/spec.md | 152 | ac-verifier SHALL be marked deprecated | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/inline-ac-verifier-into-rdd-verifier/spec.md | 166 | deprecation period SHALL be at least one release cycle | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/inline-ac-verifier-into-rdd-verifier/spec.md | 170 | deprecation period SHALL be at least one release cycle | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/inline-ac-verifier-into-rdd-verifier/spec.md | 177 | deprecation period SHALL be at least one release cycle | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/inline-ac-verifier-into-rdd-verifier/spec.md | 179 | deprecation period SHALL be at least one release cycle | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/migration-docs/spec.md | 9 | migration-guide-content | guide-spec | unclassified | unset |  |  |  |
| openspec/specs/migration-docs/spec.md | 33 | usage-doc-update | guide-arch | unclassified | unset |  |  |  |
| openspec/specs/migration-docs/spec.md | 33 | usage-doc-update | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/migration-docs/spec.md | 33 | usage-doc-update | guide-ship | unclassified | unset |  |  |  |
| openspec/specs/openspec-version-degradation/spec.md | 8 | CLI 版本检测与降级 | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/openspec-version-degradation/spec.md | 13 | CLI 版本检测与降级 | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/openspec-version-degradation/spec.md | 19 | CLI 版本检测与降级 | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/plan-done-quality-gate/spec.md | 8 | run_plan_checks 在 plan_done_gate 正常执行路径中被调用 | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/plan-done-quality-gate/spec.md | 12 | run_plan_checks 在 plan_done_gate 正常执行路径中被调用 | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/post-flow-analysis/spec.md | 10 | fix-adr-0027-cli-optin-gate | guide-ship | unclassified | unset |  |  |  |
| openspec/specs/propose-changes/spec.md | 37 | parent-feature-name-validation | guide-design | unclassified | unset |  |  |  |
| openspec/specs/rddf-layout-manifest/spec.md | 118 | acceptance-13 | guide-design | unclassified | unset |  |  |  |
| openspec/specs/rddf-layout-manifest/spec.md | 118 | acceptance-13 | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/rddf-layout-manifest/spec.md | 118 | acceptance-13 | guide-ship | unclassified | unset |  |  |  |
| openspec/specs/rddf-layout-manifest/spec.md | 123 | acceptance-13 | guide-design | unclassified | unset |  |  |  |
| openspec/specs/rddf-layout-manifest/spec.md | 123 | acceptance-13 | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/rddf-layout-manifest/spec.md | 123 | acceptance-13 | guide-ship | unclassified | unset |  |  |  |
| openspec/specs/release-management/spec.md | 9 | beta-version-published | guide-arch | unclassified | unset |  |  |  |
| openspec/specs/release-management/spec.md | 9 | beta-version-published | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/release-management/spec.md | 9 | beta-version-published | guide-ship | unclassified | unset |  |  |  |
| openspec/specs/remove-ac-verifier-completely/spec.md | 6 | ac-verifier skill deletion | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/remove-ac-verifier-completely/spec.md | 7 | ac-verifier skill deletion | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/remove-ac-verifier-completely/spec.md | 7 | ac-verifier skill deletion | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/remove-ac-verifier-completely/spec.md | 11 | ac-verifier skill deletion | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/remove-ac-verifier-completely/spec.md | 12 | ac-verifier skill deletion | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/remove-ac-verifier-completely/spec.md | 51 | ac-verifier test file removal | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/remove-ac-verifier-completely/spec.md | 69 | ac-verifier test file removal | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/remove-ac-verifier-completely/spec.md | 72 | top-level docs cleanup | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/remove-ac-verifier-completely/spec.md | 74 | top-level docs cleanup | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/remove-ac-verifier-completely/spec.md | 76 | top-level docs cleanup | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/remove-ac-verifier-completely/spec.md | 78 | top-level docs cleanup | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/remove-ac-verifier-completely/spec.md | 80 | top-level docs cleanup | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/remove-ac-verifier-completely/spec.md | 83 | top-level docs cleanup | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/remove-ac-verifier-completely/spec.md | 85 | top-level docs cleanup | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/remove-ac-verifier-completely/spec.md | 97 | ADR historical reference | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/remove-ac-verifier-completely/spec.md | 101 | ADR historical reference | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/rfc-rddf-project-yaml-config-i10/spec.md | 26 | acceptance-3 | guide-ship | unclassified | unset |  |  |  |
| openspec/specs/rfc-rddf-project-yaml-config-i10/spec.md | 28 | acceptance-3 | guide-ship | unclassified | unset |  |  |  |
| openspec/specs/rfc-rddf-project-yaml-config-i10/spec.md | 31 | acceptance-3 | guide-ship | unclassified | unset |  |  |  |
| openspec/specs/roadmap-hierarchy/spec.md | 149 | plan-done gate 集成 fragment 校验 | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/roadmap-incremental/spec.md | 8 | arch-done-roadmap-sync | guide-arch | unclassified | unset |  |  |  |
| openspec/specs/roadmap-incremental/spec.md | 11 | arch-done-roadmap-sync | guide-arch | unclassified | unset |  |  |  |
| openspec/specs/roadmap-incremental/spec.md | 132 | thin-wrapper-standalone-skill | guide-arch | unclassified | unset |  |  |  |
| openspec/specs/roadmap-incremental/spec.md | 137 | thin-wrapper-standalone-skill | guide-arch | unclassified | unset |  |  |  |
| openspec/specs/roadmap-proposal-guidance/spec.md | 69 | guide-design preflight 显示 roadmap 主题覆盖率 | guide-design | unclassified | unset |  |  |  |
| openspec/specs/roadmap-proposal-guidance/spec.md | 71 | guide-design preflight 显示 roadmap 主题覆盖率 | guide-design | unclassified | unset |  |  |  |
| openspec/specs/roadmap-proposal-guidance/spec.md | 103 | guide-design Phase 2 菜单新增按主题创建选项 | guide-design | unclassified | unset |  |  |  |
| openspec/specs/roadmap-proposal-guidance/spec.md | 105 | guide-design Phase 2 菜单新增按主题创建选项 | guide-design | unclassified | unset |  |  |  |
| openspec/specs/roadmap-proposal-guidance/spec.md | 142 | rdd-doctor 不感知主题覆盖率字段 | guide-design | unclassified | unset |  |  |  |
| openspec/specs/skeleton-planning/spec.md | 11 | planned-status-lifecycle | guide-ship | unclassified | unset |  |  |  |
| openspec/specs/skeleton-planning/spec.md | 22 | planned-status-lifecycle | guide-ship | unclassified | unset |  |  |  |
| openspec/specs/skeleton-planning/spec.md | 23 | planned-status-lifecycle | guide-ship | unclassified | unset |  |  |  |
| openspec/specs/skeleton-planning/spec.md | 43 | skeleton-minimal-artifacts | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/skeleton-planning/spec.md | 47 | skeleton-minimal-artifacts | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/skeleton-planning/spec.md | 83 | proposal-suggestions-skeleton-status | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/spec-validation-gates/spec.md | 149 | guide-plan.md plan-done gate MUST validate all active changes | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/spec-validation-gates/spec.md | 151 | guide-plan.md plan-done gate MUST validate all active changes | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/spec-validation-gates/spec.md | 158 | guide-plan.md plan-done gate MUST validate all active changes | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/spec-validation-gates/spec.md | 167 | guide-plan.md plan-done gate MUST validate all active changes | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/spec-validation-gates/spec.md | 183 | rdd-builder P3 archive pre-flight MUST call validate_delta_targets.py | guide-ship | unclassified | unset |  |  |  |
| openspec/specs/state-management/spec.md | 65 | iteration-json-planned-status | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/state-management/spec.md | 73 | iteration-json-planned-status | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/third-party-feedback-loop/spec.md | 33 | Phase traces are replayable from any project subdirectory | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/third-party-feedback-loop/spec.md | 39 | Phase traces are replayable from any project subdirectory | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/v4-planner-scope-correction/spec.md | 136 | sh-broken-removed-or-repointed | guide-design | unclassified | unset |  |  |  |
| openspec/specs/v4-residue-contract/spec.md | 41 | route-schema-enums-preserve-legacy-values | guide-ship | unclassified | unset |  |  |  |
| openspec/specs/v4-residue-contract/spec.md | 83 | user-facing-text-references-existing-skills | guide-arch | unclassified | unset |  |  |  |
| openspec/specs/v4-residue-contract/spec.md | 88 | user-facing-text-references-existing-skills | guide-arch | unclassified | unset |  |  |  |
| openspec/specs/v4-residue-contract/spec.md | 88 | user-facing-text-references-existing-skills | guide-design | unclassified | unset |  |  |  |
| openspec/specs/v4-residue-contract/spec.md | 88 | user-facing-text-references-existing-skills | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/v4-residue-contract/spec.md | 88 | user-facing-text-references-existing-skills | guide-ship | unclassified | unset |  |  |  |
| openspec/specs/v4-residue-contract/spec.md | 93 | user-facing-text-references-existing-skills | guide-ship | unclassified | unset |  |  |  |
| openspec/specs/v4-residue-contract/spec.md | 113 | v4-residue-doctor-category | guide-ship | unclassified | unset |  |  |  |
| openspec/specs/v4-residue-contract/spec.md | 119 | v4-residue-doctor-category | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/v4-residue-contract/spec.md | 133 | v4-residue-scan-exclusions | guide-design | unclassified | unset |  |  |  |
| openspec/specs/v4-residue-contract/spec.md | 139 | v4-residue-scan-exclusions | guide-design | unclassified | unset |  |  |  |
| openspec/specs/v4-residue-contract/spec.md | 145 | v4-residue-scan-exclusions | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/v4-residue-contract/spec.md | 151 | v4-residue-scan-exclusions | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/verifier-archive-gate/spec.md | 10 | ADR-0035 documents verifier/archive dual-track boundary | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/verifier-archive-gate/spec.md | 31 | STRICT_AC_GATE escalation token | ac-verifier | unclassified | unset |  |  |  |
| openspec/specs/verifier-lifecycle/spec.md | 166 | Verification failures SHALL route back to plan or ship | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/verifier-lifecycle/spec.md | 166 | Verification failures SHALL route back to plan or ship | guide-ship | unclassified | unset |  |  |  |

## 合计

- `disposition=unset`：**191** 条命中记录（Phase 1 的待办量）
- 已登记豁免（标注）：**142** 处
- 命中 token 分布：
  - `guide-arch`: 24
  - `guide-design`: 24
  - `guide-plan`: 45
  - `guide-ship`: 39
  - `guide-spec`: 11
  - `ac-verifier`: 48
