# spec 残留处置台账 — Phase 1 对齐 18 份（2026-11-20）

> 定位：change `align-spec-residue-prior-18`。`fix-spec-residue-guard` 的普查台账刻意不合并既有签批
> （合并键不可靠），本台账是这 18 份的**逐行处置记录**——`disposition` 即签批。
> 处置分型沿用 ADR-0036 修订；改指落点沿用 `docs/migration/v3-to-v4.md:28-31,41-45`。
> `line` 列是**改前**行号（插入标注后会下移）。
> ⚠️ 18 份里 **3 份已 0 命中**（batch 当时已标完）⇒ 实际改动面 **15 份 / 120 行**。

| 处置 | 行数 | 含义 |
|---|---|---|
| `ANNOTATE` | 93 | 行内标注 `<!-- v4-residue:allow=<code> -->`（合法历史引用） |
| `ENUM` | 3 | 枚举字面量，该值今天仍存在于 `_lib/schemas/sessions_schema.json` |
| `ADD_NOTE` | 8 | 已死块补注记 / 一处过度退役的澄清 |
| `REPOINT` | 16 | 活契约里的真残留 ⇒ 按权威映射表改指 |
| **合计** | **120** | |

## 逐行处置

| file | line | requirement_title | matched_token | disposition | code | evidence |
|---|---|---|---|---|---|---|
| openspec/specs/add-strict-human-approval/spec.md | 29 | STRICT_DESIGN_GATE blocks design-done for unapproved cross-r | guide-design | ADD_NOTE | RETIRED | **代码 0 命中**：`STRICT_DESIGN_GATE` / `rddf design-gate-check` 在 `_lib/` 与 `skills/` 均无实现（`_lib/gate.py` 只有 arch_done / plan_done / ship_done 三个 transition，无 design_done；`skills/guide-design/` 整目录不存在）⇒ 门 |
| openspec/specs/add-strict-human-approval/spec.md | 235 | design_content_review.sh upgrade for cross-repo category | guide-design | ANNOTATE | history | note@235 |
| openspec/specs/add-strict-human-approval/spec.md | 238 | design_content_review.sh upgrade for cross-repo category | guide-design | ANNOTATE | history | note@235 |
| openspec/specs/approved-proposal-parsing/spec.md | 35 | All three call sites use the helper | guide-design | ANNOTATE | rename-history | 行内「原 X」括号说明 |
| openspec/specs/approved-proposal-parsing/spec.md | 39 | All three call sites use the helper | guide-design | ADD_NOTE | RETIRED | `design_proposal_review.sh` **不存在**（同 Requirement 正文的「2026-11-20 部分退役」注记：审查逻辑并入 `propose_quality_check.py`）；本 Scenario 描述的是已消失的脚本入口 |
| openspec/specs/cross-container-event-bus/spec.md | 185 | rddf-session-goal-intent | guide-arch,guide-design,guide-plan,guide-ship | ENUM | enum | 枚举字面量，该值今天仍在 _lib/schemas/sessions_schema.json 的 goal.intent 里 |
| openspec/specs/cross-container-event-bus/spec.md | 189 | rddf-session-goal-intent | guide-arch,guide-design,guide-plan,guide-ship | ENUM | enum | 枚举字面量，该值今天仍在 _lib/schemas/sessions_schema.json 的 goal.intent 里 |
| openspec/specs/design-content-review/spec.md | 34 | approve 流调用 improvements 层内容审查 | guide-design | ANNOTATE | history | note@34 |
| openspec/specs/design-content-review/spec.md | 37 | approve 流调用 improvements 层内容审查 | guide-design | ANNOTATE | history | note@34 |
| openspec/specs/project-setup-check/spec.md | 79 | `guide-arch` Phase 1 hard-blocks on error issues | guide-arch | REPOINT | pure | 权威映射 guide-arch→rdd-arch（v3-to-v4.md:28-31） |
| openspec/specs/project-setup-check/spec.md | 80 | `guide-arch` Phase 1 hard-blocks on error issues | guide-arch | ANNOTATE | rename-history | 行内「原 X」括号说明 |
| openspec/specs/project-setup-check/spec.md | 82 | `guide-arch` Phase 1 hard-blocks on error issues | guide-arch | REPOINT | pure | 权威映射 guide-arch→rdd-arch（v3-to-v4.md:28-31） |
| openspec/specs/project-setup-check/spec.md | 86 | `guide-arch` Phase 1 hard-blocks on error issues | guide-arch | REPOINT | pure | 权威映射 guide-arch→rdd-arch（v3-to-v4.md:28-31） |
| openspec/specs/proposal-lifecycle-sync/spec.md | 14 | `approve_proposal.sh` MUST stage `improvement-approved.md` b | guide-design | ANNOTATE | history | note@14 |
| openspec/specs/proposal-lifecycle-sync/spec.md | 17 | `approve_proposal.sh` MUST stage `improvement-approved.md` b | guide-design | ANNOTATE | history | note@14 |
| openspec/specs/proposal-lifecycle-sync/spec.md | 113 | `plan-done` gate MUST warn on dirty `improvement-approved.md | guide-plan | ADD_NOTE | RETIRED | 两个落点都不存在：① `.plan-handoff.json` 已于 ADR-0044 Wave 3 RETIRE（`docs/schemas/README.md:51` 「legacy plan-done, per ADR-0044 RETIRE」）；② `skills/rdd-builder/` 对 `plan-done` **0 命中**（v4 的 plan-done 是 `_lib/gat |
| openspec/specs/rddf-session/spec.md | 10 | rddf-session 持久化 | guide-arch | REPOINT | pure | 权威映射 guide-arch→rdd-arch（v3-to-v4.md:28-31） |
| openspec/specs/rddf-session/spec.md | 22 | rddf-session kind 分类 | guide-arch | REPOINT | pure | 权威映射 guide-arch→rdd-arch（v3-to-v4.md:28-31） |
| openspec/specs/rddf-session/spec.md | 23 | rddf-session kind 分类 | guide-arch | ANNOTATE | rename-history | 行内「原 X」括号说明 |
| openspec/specs/rddf-session/spec.md | 27 | rddf-session kind 分类 | guide-plan | REPOINT | special | `rdd-builder` / `rdd-planner` 的 SKILL.md 对 `propose` 0 命中 |
| openspec/specs/rddf-session/spec.md | 39 | rddf-session 状态机 | guide-arch | REPOINT | pure | 权威映射 guide-arch→rdd-arch（v3-to-v4.md:28-31） |
| openspec/specs/rddf-session/spec.md | 45 | rddf-session 状态机 | guide-plan | ADD_NOTE | RETIRED | 触发条件在 v4 **无实现**：`ready-for-ship` 全仓 0 命中、`end_reason="plan-done-gate-rejected"` 0 命中、`_lib/gate.py:378` 的 `plan_done` 判据是 `artifacts_complete` / `changes_committed` 等。⚠️ 状态值 `failed` 本身仍合法（`_lib/.../ |
| openspec/specs/rddf-session/spec.md | 57 | 心跳机制 | guide-plan | REPOINT | special | `refresh_heartbeat` 活于 `rddf_session.py:112`（5 分钟刷新 / 30 分钟超时）。⚠️ 既有漂移（不在本项范围）：`rddf_session_hook_*` 在 v4 生产代码无调用方（仅 tests 调用，且测试注释仍写 guide-ship Phase 3） |
| openspec/specs/rddf-session/spec.md | 58 | 心跳机制 | guide-plan | REPOINT | special | `rdd-builder/SKILL.md:5-6` 的 phase 编号是 P0/P1/P1.5/P2/P2.5/P3，与 v3 的 Phase 2/2.5/3 不同。⚠️ 既有漂移（不在本项范围）：该 hook 无 v4 生产调用方 |
| openspec/specs/rddf-session/spec.md | 74 | opencode session 冲突软提示 | guide-plan | ANNOTATE | rename-history | 行内「原 X」括号说明 |
| openspec/specs/rddf-session/spec.md | 79 | opencode session 冲突软提示 | guide-plan | ANNOTATE | rename-history | 行内「原 X」括号说明 |
| openspec/specs/rddf-session/spec.md | 100 | rddf-session 父子关系 | guide-plan | REPOINT | pure | 权威映射 guide-plan→rdd-builder（v3-to-v4.md:28-31） |
| openspec/specs/rddf-session/spec.md | 114 | 关闭时序 | guide-plan | REPOINT | pure | 权威映射 guide-plan→rdd-builder（v3-to-v4.md:28-31） |
| openspec/specs/roadmap-feature-fragment/spec.md | 81 | guide-arch Phase 4 menu integration | guide-arch | ADD_NOTE | RETIRED | `skills/rdd-arch/SKILL.md` 的 Phase 4 是 `arch-done (Exit)`（`:549`），**没有** feature fragment 菜单；能力由 CLI `rddf roadmap add-feature` 承接 |
| openspec/specs/roadmap-feature-fragment/spec.md | 83 | guide-arch Phase 4 menu integration | guide-arch | ADD_NOTE | RETIRED | `skills/rdd-arch/SKILL.md` 的 Phase 4 是 `arch-done (Exit)`（`:549`），**没有** feature fragment 菜单；能力由 CLI `rddf roadmap add-feature` 承接 |
| openspec/specs/roadmap-feature-fragment/spec.md | 86 | guide-arch Phase 4 menu integration | guide-arch | ADD_NOTE | RETIRED | `skills/rdd-arch/SKILL.md` 的 Phase 4 是 `arch-done (Exit)`（`:549`），**没有** feature fragment 菜单；能力由 CLI `rddf roadmap add-feature` 承接 |
| openspec/specs/roadmap-feature-fragment/spec.md | 97 | ADR-0028 role boundary extension | guide-arch | ANNOTATE | rename-history | 行内「原 X」括号说明 |
| openspec/specs/ship-done-orphan-cleanup/spec.md | 41 | ship-done menu shows an orphan warning and option 5 when orp | guide-ship | ANNOTATE | history | note@41 |
| openspec/specs/ship-done-orphan-cleanup/spec.md | 43 | ship-done menu shows an orphan warning and option 5 when orp | guide-ship | ANNOTATE | history | note@41 |
| openspec/specs/ship-done-orphan-cleanup/spec.md | 93 | ship-done orphan cleanup is not automatic | guide-ship | ADD_NOTE | RETIRED | `skills/guide-ship/scripts/ship_done.sh` 不存在（ADR-0044 Wave 3 硬删除）⇒ 该菜单项约束不可验证；孤儿会话的**标记**由 `rddf sessions gc` 承接（30 分钟 heartbeat 超时 → orphaned），**清理/归档**由 `rddf sessions abandon` / `archive-history` 承 |
| openspec/specs/ship-done-orphan-cleanup/spec.md | 104 | line-count constraints are preserved | guide-ship | ANNOTATE | history | note@104 |
| openspec/specs/ship-done-orphan-cleanup/spec.md | 110 | line-count constraints are preserved | guide-ship | ANNOTATE | history | note@104 |
| openspec/specs/skill-role-model/spec.md | 15 | skill-frontmatter-role-field-optional | guide-arch | ANNOTATE | rename-history | 行内「原 X」括号说明 |
| openspec/specs/skill-role-model/spec.md | 22 | skill-frontmatter-role-field-optional | guide-arch | ANNOTATE | rename-history | 行内「原 X」括号说明 |
| openspec/specs/skill-role-model/spec.md | 133 | skill-role-boundaries-accurate | guide-arch | REPOINT | pure | 权威映射 guide-arch→rdd-arch（v3-to-v4.md:28-31） |
| openspec/specs/skill-role-model/spec.md | 135 | skill-role-boundaries-accurate | guide-arch | REPOINT | pure | 权威映射 guide-arch→rdd-arch（v3-to-v4.md:28-31） |
| openspec/specs/skill-role-model/spec.md | 143 | skill-role-human-involvement-level | guide-arch | REPOINT | pure | 权威映射 guide-arch→rdd-arch（v3-to-v4.md:28-31） |
| openspec/specs/skill-role-model/spec.md | 145 | skill-role-human-involvement-level | guide-arch | REPOINT | pure | 权威映射 guide-arch→rdd-arch（v3-to-v4.md:28-31） |
| openspec/specs/skill-role-model/spec.md | 157 | skill-role-metadata-consistent-across-phases | guide-arch,guide-design,guide-plan,guide-ship | REPOINT | special | v4 的四个 phase skill（`v3-to-v4.md:3`）；盲替换会让 `rdd-builder` 重复一次 |
| openspec/specs/three-phase-skills/spec.md | 8 | guide-arch-skill | guide-arch,guide-plan | ANNOTATE | history | note@8 |
| openspec/specs/three-phase-skills/spec.md | 10 | guide-arch-skill | guide-arch | ANNOTATE | history | note@8 |
| openspec/specs/three-phase-skills/spec.md | 26 | guide-plan-skill | guide-arch,guide-plan | ANNOTATE | history | note@26 |
| openspec/specs/three-phase-skills/spec.md | 28 | guide-plan-skill | guide-plan | ANNOTATE | history | note@26 |
| openspec/specs/three-phase-skills/spec.md | 30 | guide-plan-skill | guide-spec | ANNOTATE | history | note@26 |
| openspec/specs/three-phase-skills/spec.md | 52 | guide-plan-skill | guide-plan | ANNOTATE | history | note@26 |
| openspec/specs/three-phase-skills/spec.md | 59 | guide-spec-alias | guide-arch,guide-plan | ANNOTATE | history | note@59 |
| openspec/specs/three-phase-skills/spec.md | 61 | guide-spec-alias | guide-arch,guide-plan,guide-spec | ANNOTATE | history | note@59 |
| openspec/specs/three-phase-skills/spec.md | 63 | guide-spec-alias | guide-spec | ANNOTATE | history | note@59 |
| openspec/specs/three-phase-skills/spec.md | 64 | guide-spec-alias | guide-spec | ANNOTATE | history | note@59 |
| openspec/specs/three-phase-skills/spec.md | 65 | guide-spec-alias | guide-arch,guide-plan | ANNOTATE | history | note@59 |
| openspec/specs/three-phase-skills/spec.md | 70 | guide-recommender-three-phase | guide-arch,guide-plan | ANNOTATE | history | note@70 |
| openspec/specs/three-phase-skills/spec.md | 76 | guide-recommender-three-phase | guide-arch | ANNOTATE | history | note@70 |
| openspec/specs/three-phase-skills/spec.md | 80 | guide-recommender-three-phase | guide-plan | ANNOTATE | history | note@70 |
| openspec/specs/workflow-design-phase/spec.md | 8 | design Phase State Machine | guide-design,guide-plan | ANNOTATE | history | note@8 |
| openspec/specs/workflow-design-phase/spec.md | 11 | design Phase State Machine | guide-design | ANNOTATE | history | note@8 |
| openspec/specs/workflow-design-phase/spec.md | 16 | design Phase State Machine | guide-design | ANNOTATE | history | note@8 |
| openspec/specs/workflow-design-phase/spec.md | 18 | design Phase State Machine | guide-arch | ANNOTATE | history | note@8 |
| openspec/specs/workflow-design-phase/spec.md | 44 | design Phase State Machine | guide-design | ANNOTATE | history | note@8 |
| openspec/specs/workflow-design-phase/spec.md | 51 | design-handoff Contract | guide-design,guide-plan | ANNOTATE | history | note@51 |
| openspec/specs/workflow-design-phase/spec.md | 67 | design-handoff Contract | guide-design | ANNOTATE | history | note@51 |
| openspec/specs/workflow-design-phase/spec.md | 71 | arch Phase 5.5 Deprecation | guide-design,guide-plan | ANNOTATE | history | note@71 |
| openspec/specs/workflow-design-phase/spec.md | 74 | arch Phase 5.5 Deprecation | guide-arch,guide-design | ANNOTATE | history | note@71 |
| openspec/specs/workflow-design-phase/spec.md | 78 | arch Phase 5.5 Deprecation | guide-arch,guide-design | ANNOTATE | history | note@71 |
| openspec/specs/workflow-design-phase/spec.md | 79 | arch Phase 5.5 Deprecation | guide-arch | ANNOTATE | history | note@71 |
| openspec/specs/workflow-design-phase/spec.md | 83 | arch Phase 5.5 Deprecation | guide-arch | ANNOTATE | history | note@71 |
| openspec/specs/workflow-design-phase/spec.md | 95 | arch Phase 5.5 Deprecation | guide-arch | ANNOTATE | history | note@71 |
| openspec/specs/workflow-design-phase/spec.md | 99 | arch Phase 5.5 Deprecation | guide-design | ANNOTATE | history | note@71 |
| openspec/specs/workflow-design-phase/spec.md | 103 | plan Phase Design-done Gate (hard switch) | guide-design,guide-plan | ANNOTATE | history | note@103 |
| openspec/specs/workflow-design-phase/spec.md | 106 | plan Phase Design-done Gate (hard switch) | guide-plan | ANNOTATE | history | note@103 |
| openspec/specs/workflow-design-phase/spec.md | 111 | plan Phase Design-done Gate (hard switch) | guide-plan | ANNOTATE | history | note@103 |
| openspec/specs/workflow-design-phase/spec.md | 112 | plan Phase Design-done Gate (hard switch) | guide-design | ANNOTATE | history | note@103 |
| openspec/specs/workflow-design-phase/spec.md | 117 | plan Phase Design-done Gate (hard switch) | guide-plan | ANNOTATE | history | note@103 |
| openspec/specs/workflow-design-phase/spec.md | 130 | plan Phase Design-done Gate (hard switch) | guide-design | ANNOTATE | history | note@103 |
| openspec/specs/workflow-design-phase/spec.md | 134 | Dual-Scanner 4-State Recommender | guide-design,guide-plan | ANNOTATE | history | note@134 |
| openspec/specs/workflow-design-phase/spec.md | 141 | Dual-Scanner 4-State Recommender | guide-arch,guide-ship | ANNOTATE | history | note@134 |
| openspec/specs/workflow-design-phase/spec.md | 142 | Dual-Scanner 4-State Recommender | guide-design,guide-plan | ANNOTATE | history | note@134 |
| openspec/specs/workflow-design-phase/spec.md | 143 | Dual-Scanner 4-State Recommender | guide-design,guide-plan | ANNOTATE | history | note@134 |
| openspec/specs/workflow-design-phase/spec.md | 153 | Session Schema Additive Extension | guide-design,guide-plan | ANNOTATE | history | note@153 |
| openspec/specs/workflow-design-phase/spec.md | 160 | Session Schema Additive Extension | guide-design | ENUM | enum | 枚举字面量，该值今天仍在 _lib/schemas/sessions_schema.json 的 goal.intent 里 |
| openspec/specs/workflow-design-phase/spec.md | 171 | design-handoff v2 with changes_pre_created | guide-design,guide-plan | ANNOTATE | history | note@171 |
| openspec/specs/workflow-design-phase/spec.md | 174 | design-handoff v2 with changes_pre_created | guide-plan | ANNOTATE | history | note@171 |
| openspec/specs/workflow-design-phase/spec.md | 181 | design-handoff v2 with changes_pre_created | guide-plan | ANNOTATE | history | note@171 |
| openspec/specs/workflow-design-phase/spec.md | 186 | design-handoff v2 with changes_pre_created | guide-plan | ANNOTATE | history | note@171 |
| openspec/specs/iterative-plan-fill/spec.md | 6 | fill-phase-in-guide-plan | guide-plan | ANNOTATE | history | PARTIAL：Requirement 标题即 v3 子阶段名（f7)；退役部分是框架，标题随历史保留 |
| openspec/specs/iterative-plan-fill/spec.md | 11 | fill-phase-in-guide-plan | guide-plan | ANNOTATE | history | PARTIAL：退役的是「fill 子阶段建在 guide-plan、且位于 deps 之后」这个框架（v4 由 rdd-builder P1 承担，P1 在 P1.5 deps 之前）；保留的是「补 tasks.md」子句 |
| openspec/specs/iterative-plan-fill/spec.md | 21 | fill-phase-in-guide-plan | guide-plan | ANNOTATE | history | PARTIAL：PARTIAL 注记已明写退役「让用户选择 planned change」⇒ 该 Scenario 属退役部分 |
| openspec/specs/iterative-plan-fill/spec.md | 42 | fill-trigger-from-deps | guide-plan,guide-ship | ANNOTATE | history | note@42 |
| openspec/specs/iterative-plan-fill/spec.md | 59 | fill-trigger-from-deps | guide-plan,guide-ship | ANNOTATE | history | note@42 |
| openspec/specs/iterative-plan-fill/spec.md | 66 | mixed-plan-done-gate | guide-plan | ANNOTATE | history | note@63 |
| openspec/specs/iterative-plan-fill/spec.md | 69 | mixed-plan-done-gate | guide-ship | ANNOTATE | history | note@63 |
| openspec/specs/iterative-plan-fill/spec.md | 82 | mixed-plan-done-gate | guide-ship | ANNOTATE | history | note@63 |
| openspec/specs/iterative-plan-fill/spec.md | 89 | post-archive-fill-suggestion | guide-ship | ANNOTATE | history | note@86 |
| openspec/specs/iterative-plan-fill/spec.md | 92 | post-archive-fill-suggestion | guide-ship | ANNOTATE | history | note@86 |
| openspec/specs/iterative-plan-fill/spec.md | 93 | post-archive-fill-suggestion | guide-ship | ANNOTATE | history | note@86 |
| openspec/specs/iterative-plan-fill/spec.md | 94 | post-archive-fill-suggestion | guide-plan,guide-ship | ANNOTATE | history | note@86 |
| openspec/specs/iterative-plan-fill/spec.md | 97 | post-archive-fill-suggestion | guide-ship | ANNOTATE | history | note@86 |
| openspec/specs/iterative-plan-fill/spec.md | 99 | post-archive-fill-suggestion | guide-plan | ANNOTATE | history | note@86 |
| openspec/specs/iterative-plan-fill/spec.md | 103 | post-archive-fill-suggestion | guide-ship | ANNOTATE | history | note@86 |
| openspec/specs/iterative-plan-fill/spec.md | 113 | intake 消费 changes_pre_created | guide-plan | ANNOTATE | history | note@109 |
| openspec/specs/iterative-plan-fill/spec.md | 118 | intake 消费 changes_pre_created | guide-plan | ANNOTATE | history | note@109 |
| openspec/specs/plan-intake-bootstrap/spec.md | 16 | plan-intake-detects-missing-design-handoff | guide-design,guide-plan | ANNOTATE | history | note@8 |
| openspec/specs/plan-intake-bootstrap/spec.md | 18 | plan-intake-detects-missing-design-handoff | guide-design | ANNOTATE | history | note@8 |
| openspec/specs/plan-intake-bootstrap/spec.md | 47 | plan-intake-detects-stale-handoff | guide-design | ANNOTATE | history | note@38 |
| openspec/specs/plan-intake-bootstrap/spec.md | 62 | plan-intake-detects-empty-changes-pre-created | guide-design | ANNOTATE | history | note@52 |
| openspec/specs/plan-intake-bootstrap/spec.md | 104 | plan-intake-skip-propose-for-design-precreated | guide-plan | ANNOTATE | history | note@95 |
| openspec/specs/plan-intake-bootstrap/spec.md | 105 | plan-intake-skip-propose-for-design-precreated | guide-plan | ANNOTATE | history | note@95 |
| openspec/specs/plan-intake-bootstrap/spec.md | 106 | plan-intake-skip-propose-for-design-precreated | guide-plan | ANNOTATE | history | note@95 |
| openspec/specs/plan-intake-bootstrap/spec.md | 131 | plan-intake-stale-handoff-with-empty-changes-folder | guide-plan | ANNOTATE | history | note@121 |
| openspec/specs/verifier-v2-hardening/spec.md | 102 | read_verdict_cache SHALL fail closed on unknown schema_versi | ac-verifier | ANNOTATE | history | ac-verifier 时代的 schema_version 历史说明 |
| openspec/specs/verifier-v2-hardening/spec.md | 162 | planner SHALL expose scan_deprecated_skills helper | ac-verifier | ANNOTATE | history | batch2 已签批：`scan_deprecated_skills` 的输入夹具（helper 活于 `_lib/planner_deprecation.py:74`） |
| openspec/specs/verifier-v2-hardening/spec.md | 165 | planner SHALL expose scan_deprecated_skills helper | ac-verifier | ANNOTATE | history | 注记自身 |
| openspec/specs/verifier-v2-hardening/spec.md | 170 | planner SHALL expose scan_deprecated_skills helper | ac-verifier | ANNOTATE | history | 同上：夹具的 GIVEN 是**假设输入**，不是存在性断言 |
| openspec/specs/verifier-v2-hardening/spec.md | 172 | planner SHALL expose scan_deprecated_skills helper | ac-verifier | ANNOTATE | history | 同上：夹具的 THEN 断言扫描器输出形状 |
| openspec/specs/verifier-v2-hardening/spec.md | 190 | remove-ac-verifier-completely SHALL be scheduled with manual | ac-verifier | ANNOTATE | history | note@189 |
| openspec/specs/verifier-v2-hardening/spec.md | 194 | remove-ac-verifier-completely SHALL be scheduled with manual | ac-verifier | ANNOTATE | history | note@189 |

## 逐文件汇总

| spec | ANNOTATE | ENUM | ADD_NOTE | REPOINT | 合计 |
|---|---|---|---|---|---|
| `add-strict-human-approval` | 2 | 0 | 1 | 0 | 3 |
| `approved-proposal-parsing` | 1 | 0 | 1 | 0 | 2 |
| `cross-container-event-bus` | 0 | 2 | 0 | 0 | 2 |
| `design-content-review` | 2 | 0 | 0 | 0 | 2 |
| `project-setup-check` | 1 | 0 | 0 | 3 | 4 |
| `proposal-lifecycle-sync` | 2 | 0 | 1 | 0 | 3 |
| `rddf-session` | 3 | 0 | 1 | 8 | 12 |
| `roadmap-feature-fragment` | 1 | 0 | 3 | 0 | 4 |
| `ship-done-orphan-cleanup` | 4 | 0 | 1 | 0 | 5 |
| `skill-role-model` | 2 | 0 | 0 | 5 | 7 |
| `three-phase-skills` | 14 | 0 | 0 | 0 | 14 |
| `workflow-design-phase` | 29 | 1 | 0 | 0 | 30 |
| `iterative-plan-fill` | 17 | 0 | 0 | 0 | 17 |
| `plan-intake-bootstrap` | 8 | 0 | 0 | 0 | 8 |
| `verifier-v2-hardening` | 7 | 0 | 0 | 0 | 7 |

## 0 命中的 3 份（本项不改）

- `apply-adr-0051-skill-description-convention-bulk-rewrite`
- `post-archive-cleanup-hook`
- `rddf-session-auto-archive`

