# spec 残留普查台账 — 2026-11-20

> 口径：本批 = `.rddf/improvements/fix-spec-residue-guard.md` 的 **Phase 1（逐 spec 清理）** 第一轮。
> 基线：18 份 / 51 处含已退役引用 → 本批处置 **13 份 / 34 处** → 剩余 5 份（守卫型 2 + 已退役 2 + 已标 NOTE 1）不动。
> `line` 列是 **T0 快照（改前）行号**；插入 RETIRED 注后实际行号会下移。
> `category` ∈ `{retired-object, history, rename-history, guard, enum}`；`disposition` ∈ `{REPOINT, RETIRED, PARTIAL, KEEP}`。

| file | line | requirement_title | matched_token | category | disposition | owner | signoff | date |
|---|---|---|---|---|---|---|---|---|
| openspec/specs/three-phase-skills/spec.md | 55 | guide-spec-alias | skill_use("guide-spec" | history | RETIRED | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/three-phase-skills/spec.md | 64 | guide-recommender-three-phase | skill_use("guide-arch" | history | RETIRED | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/three-phase-skills/spec.md | 68 | guide-recommender-three-phase | skill_use("guide-plan" | history | RETIRED | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/workflow-design-phase/spec.md | 13 | design Phase State Machine | skill_use("guide-design" | history | RETIRED | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/workflow-design-phase/spec.md | 15 | design Phase State Machine | skill_use("guide-arch" | history | RETIRED | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/workflow-design-phase/spec.md | 41 | design Phase State Machine | skill_use("guide-design" | history | RETIRED | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/workflow-design-phase/spec.md | 61 | design-handoff Contract | skill_use("guide-design" | history | RETIRED | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/workflow-design-phase/spec.md | 69 | arch Phase 5.5 Deprecation | skill_use("guide-design" | history | RETIRED | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/workflow-design-phase/spec.md | 74 | arch Phase 5.5 Deprecation | skills/guide-arch/scripts/arch_proposal_review.sh | history | RETIRED | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/workflow-design-phase/spec.md | 90 | arch Phase 5.5 Deprecation | skill_use("guide-design" | history | RETIRED | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/workflow-design-phase/spec.md | 99 | plan Phase Design-done Gate (hard switch) | skill_use("guide-plan" | history | RETIRED | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/workflow-design-phase/spec.md | 100 | plan Phase Design-done Gate (hard switch) | skill_use("guide-design" | history | RETIRED | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/workflow-design-phase/spec.md | 105 | plan Phase Design-done Gate (hard switch) | skill_use("guide-plan" | history | RETIRED | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/workflow-design-phase/spec.md | 122 | Dual-Scanner 4-State Recommender | skills/guide/scripts/scan-state.sh | history | RETIRED | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/project-setup-check/spec.md | 80 | `guide-arch` Phase 1 hard-blocks on error issues | skills/guide-arch/scripts/arch_env_check.sh | rename-history | REPOINT | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/project-setup-check/spec.md | 91 | `guide` recommender soft-presents all issues | skills/guide/scripts/scan-state.sh | retired-object | RETIRED | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/project-setup-check/spec.md | 93 | `guide` recommender soft-presents all issues | skill_use("guide" | retired-object | RETIRED | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/skill-role-model/spec.md | 15 | skill-frontmatter-role-field-optional | skill_use("guide-arch" | rename-history | REPOINT | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/skill-role-model/spec.md | 22 | skill-frontmatter-role-field-optional | skill_use("guide-arch" | rename-history | REPOINT | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/roadmap-feature-fragment/spec.md | 97 | ADR-0028 role boundary extension | skills/guide-arch/SKILL.md | rename-history | REPOINT | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/roadmap-feature-fragment/spec.md | 100 | ADR-0028 role boundary extension | skills/guide-arch/SKILL.md | rename-history | REPOINT | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/rddf-session/spec.md | 23 | rddf-session kind 分类 | skill_use("guide-arch" | rename-history | REPOINT | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/rddf-session/spec.md | 32 | rddf-session kind 分类 | skill_use("status" | rename-history | REPOINT | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/rddf-session/spec.md | 74 | opencode session 冲突软提示 | skill_use("guide-plan" | rename-history | REPOINT | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/rddf-session/spec.md | 79 | opencode session 冲突软提示 | skill_use("guide-plan" | rename-history | REPOINT | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/cross-container-event-bus/spec.md | 12 | stage-guide-kind | skill_use("guide" | retired-object | RETIRED | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/cross-container-event-bus/spec.md | 153 | backward-compatibility | skill_use("guide" | rename-history | REPOINT | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/ship-done-orphan-cleanup/spec.md | 40 | ship-done menu shows an orphan warning and option 5 when orp | skills/guide-ship/scripts/ship_done.sh | retired-object | RETIRED | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/ship-done-orphan-cleanup/spec.md | 104 | line-count constraints are preserved | skills/guide-ship/scripts/ship_done.sh | retired-object | RETIRED | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/design-content-review/spec.md | 34 | approve 流调用 improvements 层内容审查 | skills/guide-design/scripts/design_content_review.sh | retired-object | RETIRED | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/proposal-lifecycle-sync/spec.md | 14 | `approve_proposal.sh` MUST stage `improvement-approved.md` b | skills/guide-design/scripts/approve_proposal.sh | retired-object | RETIRED | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/add-strict-human-approval/spec.md | 235 | design_content_review.sh upgrade for cross-repo category | skills/guide-design/scripts/design_content_review.sh | retired-object | RETIRED | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/approved-proposal-parsing/spec.md | 35 | All three call sites use the helper | skills/guide-design/scripts/design_proposal_review.sh | retired-object | PARTIAL | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/apply-adr-0051-skill-description-convention-bulk-rewrite/spec.md | 20 | skill-description-convention | skills/guide/SKILL.md | rename-history | REPOINT | builder | critic APPROVE (2nd round) | 2026-11-20 |

**合计**：34 处（REPOINT 11 / RETIRED 22 / PARTIAL 1）。
