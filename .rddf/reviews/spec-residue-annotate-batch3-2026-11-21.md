# spec 残留处置台账 — Phase 1 第三批（2026-11-21）

> 定位：change `annotate-spec-residue-guard-batch3`。
> 本批**零文本改动** —— 只在命中行**下一行**插入 `<!-- v4-residue:allow=<code> -->`（HTML 注释，渲染不可见）。
> `line` 列是**改前**行号。

| code | 行数 | 含义 |
|---|---|---|
| `guard` | 49 | 反漂移判据 / 夹具 / 扫描输入：该行**断言旧名不存在**，删掉它守卫本身就不存在 |
| `rename-history` | 3 | 重命名说明（`from guide-arch to rdd-arch`） |
| **合计** | **52** | **89 处** |

## 逐行处置

| file | line | requirement_title | matched_token | code | evidence |
|---|---|---|---|---|---|
| openspec/specs/doc-architecture-v4-sync/spec.md | 8 | user-facing-docs-reflect-v4-four-stage | guide-arch,guide-design,guide-plan,guide-ship,guide-spec | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/doc-architecture-v4-sync/spec.md | 38 | user-facing-docs-reflect-v4-four-stage | guide-plan,guide-ship | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/doc-architecture-v4-sync/spec.md | 43 | architectural-docs-no-deprecated-guide-star-skill-names | guide-arch,guide-design,guide-plan,guide-ship,guide-spec | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/doc-architecture-v4-sync/spec.md | 50 | architectural-docs-no-deprecated-guide-star-skill-names | guide-arch,guide-design,guide-plan,guide-ship | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/doc-architecture-v4-sync/spec.md | 65 | architectural-docs-no-deprecated-guide-star-skill-names | guide-design | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/doc-architecture-v4-sync/spec.md | 67 | architectural-docs-no-deprecated-guide-star-skill-names | guide-plan,guide-ship | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/doc-architecture-v4-sync/spec.md | 77 | architectural-docs-no-deprecated-guide-star-skill-names | ac-verifier | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/doc-architecture-v4-sync/spec.md | 82 | architectural-docs-no-deprecated-guide-star-skill-names | ac-verifier | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/doc-architecture-v4-sync/spec.md | 97 | rdd-arch-skill-md-rename-history-bug-fixed | guide-arch | rename-history | 重命名说明（`from guide-arch to rdd-arch`）—— 类别 ⑤ |
| openspec/specs/doc-architecture-v4-sync/spec.md | 100 | rdd-arch-skill-md-rename-history-bug-fixed | guide-arch | rename-history | 重命名说明（`from guide-arch to rdd-arch`）—— 类别 ⑤ |
| openspec/specs/doc-architecture-v4-sync/spec.md | 104 | rdd-arch-skill-md-rename-history-bug-fixed | guide-arch | rename-history | 重命名说明（`from guide-arch to rdd-arch`）—— 类别 ⑤ |
| openspec/specs/doc-architecture-v4-sync/spec.md | 123 | rdd-arch-skill-md-describes-v4-four-stage | guide-design,guide-plan,guide-ship | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/doc-architecture-v4-sync/spec.md | 141 | skills-directory-has-5-rdd-stage-skills-and-0-guide-star | guide-arch,guide-design,guide-plan,guide-ship,guide-spec | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/docs-v4-sync-scope-followup/spec.md | 14 | docs-ONBOARDING-md-reflects-v4 | guide-arch,guide-design,guide-plan,guide-ship,guide-spec | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/docs-v4-sync-scope-followup/spec.md | 21 | docs-ONBOARDING-md-reflects-v4 | guide-plan | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/docs-v4-sync-scope-followup/spec.md | 24 | docs-ONBOARDING-md-reflects-v4 | ac-verifier | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/docs-v4-sync-scope-followup/spec.md | 27 | docs-ONBOARDING-md-reflects-v4 | ac-verifier | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/docs-v4-sync-scope-followup/spec.md | 29 | docs-ONBOARDING-md-reflects-v4 | ac-verifier | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/docs-v4-sync-scope-followup/spec.md | 47 | docs-architecture-improvement-check-mechanisms-no-dead-l | guide-ship | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/docs-v4-sync-scope-followup/spec.md | 52 | docs-architecture-improvement-check-mechanisms-no-dead-l | guide-ship | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/docs-v4-sync-scope-followup/spec.md | 59 | skills-INSTALL-md-no-guide-star-skill-references | guide-design,guide-plan,guide-ship | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/docs-v4-sync-scope-followup/spec.md | 64 | skills-INSTALL-md-no-guide-star-skill-references | guide-design,guide-plan,guide-ship | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/docs-v4-sync-scope-followup/spec.md | 76 | docs-architecture-skills-and-handoff-no-deleted-path-exa | guide-arch | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/docs-v4-sync-scope-followup/spec.md | 83 | docs-architecture-skills-and-handoff-no-deleted-path-exa | guide-arch | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/docs-v4-sync-scope-followup/spec.md | 96 | doc-contract-test-extended-to-all-architecture-docs | guide-arch | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/docs-v4-sync-scope-followup/spec.md | 103 | doc-contract-test-extended-to-all-architecture-docs | guide-arch,guide-design,guide-plan,guide-ship,guide-spec | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/docs-v4-sync-scope-followup/spec.md | 110 | doc-contract-test-extended-to-all-architecture-docs | guide-design,guide-plan,guide-ship | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/remove-ac-verifier-completely/spec.md | 6 | ac-verifier skill deletion | ac-verifier | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/remove-ac-verifier-completely/spec.md | 8 | ac-verifier skill deletion | ac-verifier | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/remove-ac-verifier-completely/spec.md | 13 | ac-verifier skill deletion | ac-verifier | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/remove-ac-verifier-completely/spec.md | 15 | ac-verifier skill deletion | ac-verifier | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/remove-ac-verifier-completely/spec.md | 55 | ac-verifier test file removal | ac-verifier | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/remove-ac-verifier-completely/spec.md | 74 | ac-verifier test file removal | ac-verifier | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/remove-ac-verifier-completely/spec.md | 78 | top-level docs cleanup | ac-verifier | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/remove-ac-verifier-completely/spec.md | 81 | top-level docs cleanup | ac-verifier | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/remove-ac-verifier-completely/spec.md | 84 | top-level docs cleanup | ac-verifier | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/remove-ac-verifier-completely/spec.md | 87 | top-level docs cleanup | ac-verifier | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/remove-ac-verifier-completely/spec.md | 90 | top-level docs cleanup | ac-verifier | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/remove-ac-verifier-completely/spec.md | 94 | top-level docs cleanup | ac-verifier | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/remove-ac-verifier-completely/spec.md | 97 | top-level docs cleanup | ac-verifier | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/remove-ac-verifier-completely/spec.md | 110 | ADR historical reference | ac-verifier | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/remove-ac-verifier-completely/spec.md | 115 | ADR historical reference | ac-verifier | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/v4-residue-contract/spec.md | 41 | route-schema-enums-preserve-legacy-values | guide-ship | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/v4-residue-contract/spec.md | 84 | user-facing-text-references-existing-skills | guide-arch | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/v4-residue-contract/spec.md | 90 | user-facing-text-references-existing-skills | guide-arch,guide-design,guide-plan,guide-ship | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/v4-residue-contract/spec.md | 96 | user-facing-text-references-existing-skills | guide-ship | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/v4-residue-contract/spec.md | 117 | v4-residue-doctor-category | guide-ship | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/v4-residue-contract/spec.md | 124 | v4-residue-doctor-category | guide-plan | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/v4-residue-contract/spec.md | 139 | v4-residue-scan-exclusions | guide-design | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/v4-residue-contract/spec.md | 146 | v4-residue-scan-exclusions | guide-design | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/v4-residue-contract/spec.md | 153 | v4-residue-scan-exclusions | guide-plan | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |
| openspec/specs/v4-residue-contract/spec.md | 160 | v4-residue-scan-exclusions | guide-plan | guard | 反漂移判据 / 夹具 / 扫描输入 —— 该行**断言旧名不存在**或用作示例数据，删掉它守卫本身就不存在了 |

## 逐文件汇总

| spec | guard | rename-history | 合计 | 处数 |
|---|---|---|---|---|
| `doc-architecture-v4-sync` | 10 | 3 | 13 | 32 |
| `docs-v4-sync-scope-followup` | 14 | 0 | 14 | 28 |
| `remove-ac-verifier-completely` | 15 | 0 | 15 | 16 |
| `v4-residue-contract` | 10 | 0 | 10 | 13 |

## 记 tail（范围外，本批只标不改）

`docs-v4-sync-scope-followup:85` 的 token（`skill_use("guide-arch")`）是**测试行为描述的示例** ⇒
标 `guard` 正确。但该行引用的过滤词表 `'shim\|DEPRECATED\|compat'` 已被 `c49ea379` **放宽**
（现网为 `grep -vE 'shim|DEPRECATED|deprecated|compat|已移除|已废弃|retired|hard removal|removed'`，
`tests/integration/test_v4_doc_drift_contracts.bats:273`；并新增了 spec 未覆盖的 Test 14b `:288`）。

这是 **spec-vs-impl 漂移**（不是退役 stage 残留，属五类 code 之外）⇒ **不在本批改**，
留给后续「spec-vs-impl 一致性」批次。**静默标注过去等于把它从普查视野里洗白。**

