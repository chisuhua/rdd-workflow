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
| `True` × `True` ← 选定（冻结） | 319 | 170 | 44 |
| `True` × `False` | 296 | 169 | 44 |
| `False` × `True` | 317 | 169 | 43 |
| `False` × `False` | 294 | 168 | 43 |

## 基线（选定口径）

- 扫描 spec 文件：**165** 份
- 命中实例：**319** 处（其中未被豁免 **36** 处）
- 命中块：**170** 块
- 命中 spec：**44** 份
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
| openspec/specs/cross-repo-deps/spec.md | 126 | Hub dependency issue creation | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/cross-repo-federation/spec.md | 119 | Design Gate Integration | guide-design | unclassified | unset |  |  |  |
| openspec/specs/general/spec.md | 127 | general-docs-match-code | guide-arch | unclassified | unset |  |  |  |
| openspec/specs/general/spec.md | 145 | general-docs-match-code | guide-arch | unclassified | unset |  |  |  |
| openspec/specs/general/spec.md | 146 | general-docs-match-code | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/general/spec.md | 147 | general-docs-match-code | guide-spec | unclassified | unset |  |  |  |
| openspec/specs/openspec-version-degradation/spec.md | 8 | CLI 版本检测与降级 | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/openspec-version-degradation/spec.md | 13 | CLI 版本检测与降级 | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/openspec-version-degradation/spec.md | 19 | CLI 版本检测与降级 | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/plan-done-quality-gate/spec.md | 8 | run_plan_checks 在 plan_done_gate 正常执行路径中被调用 | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/plan-done-quality-gate/spec.md | 12 | run_plan_checks 在 plan_done_gate 正常执行路径中被调用 | guide-plan | unclassified | unset |  |  |  |
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
| openspec/specs/state-management/spec.md | 65 | iteration-json-planned-status | guide-plan | unclassified | unset |  |  |  |
| openspec/specs/state-management/spec.md | 73 | iteration-json-planned-status | guide-plan | unclassified | unset |  |  |  |

## 围栏式豁免清单

> 紧跟围栏**结束行**的 `allow` 标注会豁免该围栏内**全部**行 —— 它与被豁免的文本
> 物理分离（中间隔着围栏），且本台账不列已豁免行 ⇒ 若不留这份清单，
> 它就只存在于一个没人读的注释里。`tokens` 列供人工核对「code 声明是否成立」。

| file | 围栏行范围 | code | tokens |
|---|---|---|---|
| `openspec/specs/dashboard-verification-status/spec.md` | 45–57 | `enum` | guide-plan, guide-ship |

## 合计

- `disposition=unset`：**36** 条命中记录（Phase 1 的待办量）
- 已登记豁免（标注）：**283** 处
- 命中 token 分布：
  - `guide-arch`: 6
  - `guide-design`: 6
  - `guide-plan`: 17
  - `guide-ship`: 6
  - `guide-spec`: 1
