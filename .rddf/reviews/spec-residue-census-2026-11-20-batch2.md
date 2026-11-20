# spec 残留普查台账 — 2026-11-20 batch2

> 口径：`.rddf/improvements/fix-spec-residue-guard.md` 的 **Phase 1（逐 spec 清理）第二批**。
> 基线：51 份含已退役引用 → 第一批处置 13 份 / 34 处 → **本批 5 份 / 37 处** → 剩余 28 份留给守卫驱动。
> `line` 列是 **T0 快照（改前）行号**；插入注记后实际行号会下移。
> `category` ∈ `{retired-object, history, rename-history, guard, enum}`；`disposition` ∈ `{REPOINT, RETIRED, PARTIAL, KEEP}`。
> 本批选择标准：承载机制**整体或大部分**已不存在（不是「某个落点改名」）。

| file | line | requirement_title | matched_token | category | disposition | owner | signoff | date |
|---|---|---|---|---|---|---|---|---|
| openspec/specs/plan-intake-bootstrap/spec.md | 12 | plan-intake-detects-missing-design-handoff | guide-plan | retired-object | RETIRED | plan_intake.sh 不存在; .design-handoff.json 非 v4 主 handoff | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/plan-intake-bootstrap/spec.md | 14 | plan-intake-detects-missing-design-handoff | guide-design | retired-object | RETIRED | plan_intake.sh 不存在; .design-handoff.json 非 v4 主 handoff | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/plan-intake-bootstrap/spec.md | 35 | plan-intake-detects-stale-handoff | guide-design | retired-object | RETIRED | 30 天 stale 检测 v4 无等价 | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/plan-intake-bootstrap/spec.md | 46 | plan-intake-detects-empty-changes-pre-created | guide-design | retired-object | RETIRED | changes_pre_created 无活消费者 | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/plan-intake-bootstrap/spec.md | 64 | plan-intake-marks-abandoned-sessions | guide-design | retired-object | RETIRED | sessions_cmd.py:381 heartbeat 超时承接, 判据不同 | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/plan-intake-bootstrap/spec.md | 76 | plan-intake-skip-propose-for-design-precreated | guide-plan | retired-object | RETIRED | changes_pre_created 无活消费者 | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/plan-intake-bootstrap/spec.md | 77 | plan-intake-skip-propose-for-design-precreated | guide-plan | retired-object | RETIRED | changes_pre_created 无活消费者 | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/plan-intake-bootstrap/spec.md | 78 | plan-intake-skip-propose-for-design-precreated | guide-plan | retired-object | RETIRED | changes_pre_created 无活消费者 | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/plan-intake-bootstrap/spec.md | 99 | plan-intake-stale-handoff-with-empty-changes-folder | guide-plan | retired-object | RETIRED | stale 检测 + changes_pre_created 双前提失效 | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/iterative-plan-fill/spec.md | 6 | fill-phase-in-guide-plan | guide-plan | retired-object | PARTIAL | 保留补 tasks.md(phase1_plan.sh); 退役多选/design.md/状态迁移 | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/iterative-plan-fill/spec.md | 7 | fill-phase-in-guide-plan | guide-plan | retired-object | PARTIAL | 保留补 tasks.md(phase1_plan.sh); 退役多选/design.md/状态迁移 | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/iterative-plan-fill/spec.md | 17 | fill-phase-in-guide-plan | guide-plan | retired-object | PARTIAL | 保留补 tasks.md(phase1_plan.sh); 退役多选/design.md/状态迁移 | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/iterative-plan-fill/spec.md | 51 | fill-trigger-from-deps | guide-ship | retired-object | RETIRED | phase1_5_deps.sh 对 fill/planned/recommend 零命中 | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/iterative-plan-fill/spec.md | 54 | mixed-plan-done-gate | guide-plan | retired-object | RETIRED | gate.py:378 plan_done 是 artifacts_complete, 无混合判据 | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/iterative-plan-fill/spec.md | 57 | mixed-plan-done-gate | guide-ship | retired-object | RETIRED | gate.py:378 plan_done 是 artifacts_complete, 无混合判据 | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/iterative-plan-fill/spec.md | 70 | mixed-plan-done-gate | guide-ship | retired-object | RETIRED | gate.py:378 plan_done 是 artifacts_complete, 无混合判据 | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/iterative-plan-fill/spec.md | 73 | post-archive-fill-suggestion | guide-ship | retired-object | RETIRED | wave_scheduler_post_archive 无活调用方(phase3_archive.sh:277 只调 post_archive_cleanup) | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/iterative-plan-fill/spec.md | 76 | post-archive-fill-suggestion | guide-ship | retired-object | RETIRED | wave_scheduler_post_archive 无活调用方(phase3_archive.sh:277 只调 post_archive_cleanup) | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/iterative-plan-fill/spec.md | 77 | post-archive-fill-suggestion | guide-ship | retired-object | RETIRED | wave_scheduler_post_archive 无活调用方(phase3_archive.sh:277 只调 post_archive_cleanup) | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/iterative-plan-fill/spec.md | 78 | post-archive-fill-suggestion | guide-ship | retired-object | RETIRED | wave_scheduler_post_archive 无活调用方(phase3_archive.sh:277 只调 post_archive_cleanup) | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/iterative-plan-fill/spec.md | 81 | post-archive-fill-suggestion | guide-ship | retired-object | RETIRED | wave_scheduler_post_archive 无活调用方(phase3_archive.sh:277 只调 post_archive_cleanup) | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/iterative-plan-fill/spec.md | 83 | post-archive-fill-suggestion | guide-plan | retired-object | RETIRED | wave_scheduler_post_archive 无活调用方(phase3_archive.sh:277 只调 post_archive_cleanup) | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/iterative-plan-fill/spec.md | 87 | post-archive-fill-suggestion | guide-ship | retired-object | RETIRED | wave_scheduler_post_archive 无活调用方(phase3_archive.sh:277 只调 post_archive_cleanup) | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/iterative-plan-fill/spec.md | 93 | intake 消费 changes_pre_created | guide-plan | retired-object | RETIRED | changes_pre_created 无活消费者 | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/iterative-plan-fill/spec.md | 98 | intake 消费 changes_pre_created | guide-plan | retired-object | RETIRED | changes_pre_created 无活消费者 | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/verifier-v2-hardening/spec.md | 102 | read_verdict_cache SHALL fail closed on unknown schema_ver | ac-verifier | history | KEEP | schema_version==1 是 ac-verifier 时代的历史说明, 非活引用 | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/verifier-v2-hardening/spec.md | 162 | planner SHALL expose scan_deprecated_skills helper | ac-verifier | history | KEEP | 夹具为假设输入; scan_deprecated_skills 活于 planner_deprecation.py:74 | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/verifier-v2-hardening/spec.md | 164 | planner SHALL expose scan_deprecated_skills helper | skills/ac-verifier/ | history | KEEP | 夹具为假设输入; scan_deprecated_skills 活于 planner_deprecation.py:74 | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/verifier-v2-hardening/spec.md | 166 | planner SHALL expose scan_deprecated_skills helper | ac-verifier | history | KEEP | 夹具为假设输入; scan_deprecated_skills 活于 planner_deprecation.py:74 | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/verifier-v2-hardening/spec.md | 181 | remove-ac-verifier-completely SHALL be scheduled with manu | ac-verifier | history | KEEP | 计划已完成; change 归档 2026-09-07-remove-ac-verifier-completely | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/verifier-v2-hardening/spec.md | 183 | remove-ac-verifier-completely SHALL be scheduled with manu | ac-verifier | history | KEEP | 计划已完成; change 归档 2026-09-07-remove-ac-verifier-completely | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/verifier-v2-hardening/spec.md | 187 | remove-ac-verifier-completely SHALL be scheduled with manu | ac-verifier | history | KEEP | 计划已完成; change 归档 2026-09-07-remove-ac-verifier-completely | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/verifier-v2-hardening/spec.md | 188 | remove-ac-verifier-completely SHALL be scheduled with manu | ac-verifier | history | KEEP | 计划已完成; change 归档 2026-09-07-remove-ac-verifier-completely | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/post-archive-cleanup-hook/spec.md | 5 | (preamble) | guide-ship | rename-history | REPOINT | guide-ship Phase 3 -> rdd-builder P3 (phase3_archive.sh:277 -> post_archive_cleanup:62) | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/rddf-session-auto-archive/spec.md | 16 | entry hook triggers best-effort auto-archive | guide-arch | rename-history | REPOINT | 实现层 rdd-arch/SKILL.md:138 实传 rdd-arch | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/rddf-session-auto-archive/spec.md | 25 | entry hook triggers best-effort auto-archive | guide-arch | rename-history | REPOINT | 实现层 rdd-arch/SKILL.md:138 实传 rdd-arch | builder | critic APPROVE (2nd round) | 2026-11-20 |
| openspec/specs/rddf-session-auto-archive/spec.md | 37 | close hook triggers best-effort auto-archive | guide-arch | rename-history | REPOINT | 同上 | builder | critic APPROVE (2nd round) | 2026-11-20 |

**合计**：37 处（KEEP 8 / PARTIAL 3 / REPOINT 4 / RETIRED 22）。

**本批排除**：
- `verifier-archive-gate`（2 处命中均正当：`:10` 是 ADR-0035 的 4 场景历史叙述、`:31` 是「no ac-verifier fallback」的正确当前断言）
- `plan-intake-bootstrap` 的 `design-content-review-characterization-baseline`（**活契约**：对象 `run_design_checks` `:193` + characterization 测试均在，与 `plan_intake.sh` 无关）
- `verifier-v2-hardening` 的其余 8 个 Requirement（不涉已退役对象）

