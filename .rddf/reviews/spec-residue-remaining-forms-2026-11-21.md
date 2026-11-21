# spec 残留 —— 剩余部分的形态抽样台账（2026-11-21）

> **定位**：`fix-spec-residue-guard` 的 Phase 1 剩余待办（批 5 之前的态：**66 处 / 56 行 / 24 份**）。
> 本台账是**逐行形态判定**（每行带实现事实证据），不是机器生成的普查台账（后者刻意不合并人工判定，见 `spec-residue-census-2026-11-20-full.md` 的「既有签批」段）。
> 批 6 / 批 7 的 proposal 以本表为输入；`line` 列是**改前**行号。

## 形态分布

| 形态 | 行 | 处置 | 归属 |
|---|---|---|---|
| A 既有 re-pointed/retired 注记内的历史叙述 | 4 | `ANNOTATE` | 批 5（纯标注） |
| B 纯 guard / 否定断言 / 夹具 | 5 | `ANNOTATE` | 批 5（纯标注） |
| C 枚举值（今天仍在 schema） | 1 | `ANNOTATE` | 尾项 1（代码块内，机制缺口） |
| D 历史叙述（v1/v2/v3 时代的文档或发布） | 4 | `ANNOTATE` | 批 5（纯标注） |
| E 活 actor 的机械改指 | 17 | `REPOINT` | 批 6（actor 改指） |
| F 活契约但符号已改名 | 3 | `REPOINT` | 批 6（actor 改指） |
| G 整块已死（补 RETIRED 注记） | 18 | `ADD_NOTE` | 批 7（死块注记） |
| — 专项：`general/spec.md` | 4 | **不可动** | 尾项 2 |
| **合计** | **56** | | |

处置分布：`REPOINT` 20 / `ADD_NOTE` 18 / `ANNOTATE` 14（另有专项 4 行不动）

## 批 5（纯标注） —— 13 行 / 10 份

| spec | 行 | 形态 | 处置 | code | 证据 |
|---|---|---|---|---|---|
| `archive-auto-commit` | 93 | A | ANNOTATE | `history` | 既有「**NOTE** (re-pointed 2026-11-17, per ADR-0061)」注记 —— 已归档的重命名叙述 |
| `complete-project-yaml-config-gaps` | 203 | A | ANNOTATE | `history` | 既有「**NOTE** (retired 2026-11-17, per ADR-0036 AMENDED)」注记 —— 已归档的重命名叙述 |
| `migration-docs` | 9 | D | ANNOTATE | `history` | 描述 `docs/migration/v1-to-v2.md` 的「Backward Compatibility (guide-spec alias, sync layer)」段 —— v1→v2 迁移指南的**历史内容**（该 spec 本身是 delta 形态的 v2.0 期工件） |
| `migration-docs` | 33 | D | ANNOTATE | `history` | 描述 v2.0 的 USAGE.md 技能清单（`guide-arch`, `guide-plan`, `guide-ship`）—— v2.0 发布内容 |
| `propose-changes` | 37 | B | ANNOTATE | `guard` | GIVEN 夹具：描述**已删除**脚本写入的 typo 值（`guide-design/scripts/approve_proposal.sh` 不存在） |
| `rddf-layout-manifest` | 118 | B | ANNOTATE | `guard` | 断言「**不再残留** `guide-design`/`guide-plan`/`guide-ship`」—— 反漂移判据；实测 `docs/architecture/state-and-events.md` 对这 3 个名 0 命中 ⇒ 判据今天为真 |
| `rddf-layout-manifest` | 123 | B | ANNOTATE | `guard` | 同上（Scenario 的 THEN 复述该判据） |
| `release-management` | 9 | D | ANNOTATE | `history` | 「v2.0 skills (guide-arch, guide-plan, guide-ship, loop) are available」—— v2.0-beta 发布内容（该 spec 是 delta 形态的 v2.0 期工件） |
| `spec-validation-gates` | 183 | A | ANNOTATE | `history` | 既有「**NOTE** (re-pointed 2026-11-17, per ADR-0036 AMENDED)」注记 —— 已归档的重命名叙述 |
| `v4-planner-scope-correction` | 136 | B | ANNOTATE | `history` | 描述**已完成**的处置：坏 shim（指向已删除的 `guide-design/scripts/approve_proposal.sh`）「MUST be deleted or re-pointed」—— 实测 `skills/rdd-arch/scripts/approve_proposal.sh` 已不存在 ⇒ Requirement 已被满足，括注里的旧名是**过去发生过的历史事实** ⇒ 按 ①(c) 的区分（history = 叙述过去发生过什么）归 `history`，不归 `guard`（critic 第 1 轮 SF-3） |
| `verifier-archive-gate` | 10 | D | ANNOTATE | `history` | 描述 **ADR-0035 的内容**（4 个场景含 fallback）；ADR-0035 至今仍保留该历史段落 + 2026-09-07 修订注记（`docs/adr/ADR-0035-*.md:7`）⇒ Requirement 今天仍为真 |
| `verifier-archive-gate` | 31 | B | ANNOTATE | `guard` | 「per ADR-0045: **no** ac-verifier fallback」—— 否定断言（ADR-0045:32 已移除 fallback） |
| `verifier-lifecycle` | 166 | A | ANNOTATE | `history` | 既有「**NOTE** (re-pointed 2026-11-17, per ADR-0036 AMENDED)」注记 —— 已归档的重命名叙述 |

## 尾项 1（代码块内，机制缺口） —— 1 行 / 1 份

| spec | 行 | 形态 | 处置 | code | 证据 |
|---|---|---|---|---|---|
| `dashboard-verification-status` | 50 | C | ANNOTATE | `enum` | route 枚举值 —— 实测 `_lib/schemas/verifier_loop_schema.json` 的 route 枚举今天仍含 `guide-ship` / `guide-plan`（存量 state 兼容输入，R1 判据同此） |

## 批 6（actor 改指） —— 20 行 / 9 份

| spec | 行 | 形态 | 处置 | code | 证据 |
|---|---|---|---|---|---|
| `complete-project-yaml-config-gaps` | 70 | F | REPOINT | `-` | `_default_runner` 已于 2026-09-07 移除（`_lib/cli/rdd_verify_cmd.py:158-161`「Callers MUST use `_stage_context_runner` directly」）⇒ 符号名改指 + 括注「(existing ac-verifier behavior)」同样过时（行为已内联进 rdd-verifier 的 stage-context 协议，per ADR-0045） |
| `complete-project-yaml-config-gaps` | 179 | F | REPOINT | `-` | 同上 |
| `complete-project-yaml-config-gaps` | 297 | F | REPOINT | `-` | 同上 |
| `cross-repo-deps` | 126 | E | REPOINT | `-` | `guide-plan` → `rdd-builder`（v3-to-v4.md:30） |
| `cross-repo-federation` | 119 | E | REPOINT | `-` | `guide-design` → `rdd-planner`（v3-to-v4.md:29） |
| `post-flow-analysis` | 10 | E | REPOINT | `-` | `rddf report-issue --phase` 是**自由字符串元数据**（`_lib/cli/report_issue_cmd.py:44`）⇒ 示例改用当前阶段名 |
| `rfc-rddf-project-yaml-config-i10` | 26 | E | REPOINT | `-` | `guide-ship` → `rdd-builder`（v3-to-v4.md:31） |
| `rfc-rddf-project-yaml-config-i10` | 28 | E | REPOINT | `-` | 同上（Scenario 标题） |
| `rfc-rddf-project-yaml-config-i10` | 31 | E | REPOINT | `-` | 同上（Scenario 正文） |
| `roadmap-hierarchy` | 149 | E | REPOINT | `-` | **不是**纯改名：`validate_fragment_refs` 仍活（`_lib/roadmap_validate.py:82`），但今天的调用方是 `skills/rdd-doctor/scripts/checks/roadmap_refs_check.py:22`（rdd-doctor 的 roadmap-refs 检查，WARNING 级不阻断），**不是** v3 的 plan-done 门 ⇒ 改指须写明新 actor |
| `skeleton-planning` | 11 | E | REPOINT | `-` | v3→v4 映射（`docs/migration/v3-to-v4.md:31`）：`guide-ship` → `rdd-builder` |
| `skeleton-planning` | 22 | E | REPOINT | `-` | 同上（Scenario 标题） |
| `skeleton-planning` | 23 | E | REPOINT | `-` | 同上（Scenario 正文） |
| `skeleton-planning` | 43 | E | REPOINT | `-` | `guide-plan` → `rdd-builder`（v3-to-v4.md:30）；v4 的 fill（design+tasks 生成）由 `rdd-builder` P1 承担 |
| `skeleton-planning` | 47 | E | REPOINT | `-` | 同上 |
| `skeleton-planning` | 83 | E | REPOINT | `-` | 同上 |
| `state-management` | 65 | E | REPOINT | `-` | `guide-plan` fill → `rdd-builder`（v3-to-v4.md:30） |
| `state-management` | 73 | E | REPOINT | `-` | 同上 |
| `third-party-feedback-loop` | 33 | E | REPOINT | `-` | `rddf orchestrate show <phase>` 的 phase 是**自由字符串**（`_lib/cli/orchestrate_cmd.py:66` 「Phase name (e.g. rdd-arch)」，无枚举校验）⇒ 示例应改用当前阶段名 `rdd-builder` |
| `third-party-feedback-loop` | 39 | E | REPOINT | `-` | 同上 |

## 批 7（死块注记） —— 18 行 / 5 份

| spec | 行 | 形态 | 处置 | code | 证据 |
|---|---|---|---|---|---|
| `openspec-version-degradation` | 8 | G | ADD_NOTE | `history` | **已死**：`OPENSPEC_DAG_AVAILABLE` 与 DAG 版本检测在 `_lib/`+`skills/` 全仓 **0 命中**；「guide-plan intake」的实现 `plan_intake.sh` 已不存在（批 2 台账已证）⇒ Requirement 整体失效 |
| `openspec-version-degradation` | 13 | G | ADD_NOTE | `history` | 同上（Scenario） |
| `openspec-version-degradation` | 19 | G | ADD_NOTE | `history` | 同上（Scenario） |
| `plan-done-quality-gate` | 8 | G | ADD_NOTE | `history` | **已死**：v3 的 `plan_done_gate` 路径不存在（`plan_done_gate.sh` 不存在；仅 `_lib/cross_repo_gate.py:5,9` 的**注释**提到它）；`run_plan_checks`（`skills/propose/scripts/propose_quality_check.py:234`）在 v4 **无调用方** ⇒ 「在 plan-done 正常路径中被调用」不成立 |
| `plan-done-quality-gate` | 12 | G | ADD_NOTE | `history` | 同上（Scenario） |
| `roadmap-incremental` | 8 | G | ADD_NOTE | `history` | **已死**：`guide-arch` Phase 5/6 在 v4 不存在（`skills/rdd-arch/SKILL.md` 只有 Phase 1 setup / 2 adr-create / 3 arch validation / 4 arch-done(Exit)）；Roadmap Sync 步骤已**完全删除**（`skills/rdd-arch/SKILL.md:553` per ADR-0048：`.populate-state.json` 改由 `rdd-planner` 维护）；`roadmap_incremental_update.sh` 不存在 |
| `roadmap-incremental` | 11 | G | ADD_NOTE | `history` | 同上（Scenario） |
| `roadmap-incremental` | 132 | G | ADD_NOTE | `history` | **已死**：`populate-roadmap-from-arch` skill 不存在（实测 `skills/populate-roadmap-from-arch` 不存在） |
| `roadmap-incremental` | 137 | G | ADD_NOTE | `history` | 同上（Scenario） |
| `roadmap-proposal-guidance` | 69 | G | ADD_NOTE | `history` | **已死**：`guide-design` 的「Phase 1 preflight 显示 roadmap 主题覆盖率」在 v4 无对应物（`skills/rdd-planner/SKILL.md` 只有 Phase 0 roadmap-bootstrap / Phase 1 setup，无 preflight / 无主题覆盖率） |
| `roadmap-proposal-guidance` | 71 | G | ADD_NOTE | `history` | 同上（正文） |
| `roadmap-proposal-guidance` | 103 | G | ADD_NOTE | `history` | **已死**：「Phase 2 菜单新增按路线图主题创建提案」在 v4 无对应物（rdd-planner 无该菜单） |
| `roadmap-proposal-guidance` | 105 | G | ADD_NOTE | `history` | 同上（正文） |
| `roadmap-proposal-guidance` | 142 | G | ADD_NOTE | `history` | **半死**：前半「rdd-doctor SHALL NOT 将 `**主题**:` 纳入 schema 校验」仍活；后半「coverage 显示 SHALL 仅在 `guide-design` Phase 1 preflight 中出现」随该 preflight 一起失效 ⇒ 按 PARTIAL 处理（退役子句注记 + 仍生效子句保留） |
| `spec-validation-gates` | 149 | G | ADD_NOTE | `history` | **已死**：v3 的 `skills/guide-plan.md` Phase 4 plan-done 门不存在；其写的 `.plan-handoff.json` 已随 ADR-0044 Wave 3 RETIRE（`docs/schemas/README.md:51`）；`validate_baseline.py` **不存在**（只剩 `validate_delta_targets.py`）⇒ Requirement 整体失效。（同 spec 的下一个 Requirement 已被 re-point 到 `rdd-builder` P3 archive pre-flight ⇒ 本条是漏网） |
| `spec-validation-gates` | 151 | G | ADD_NOTE | `history` | 同上（正文） |
| `spec-validation-gates` | 158 | G | ADD_NOTE | `history` | 同上（Scenario） |
| `spec-validation-gates` | 167 | G | ADD_NOTE | `history` | 同上（Scenario） |

## 专项（不可动）

| spec | 行 | 理由 |
|---|---|---|
| `general` | 127 | **断言已漂移（今天为假）**：`general/spec.md:127-128` 断言 ADR-0001 的 Decision 「spec-side 5 phases (setup/adr-create/architecture/roadmap-define/arch-done per `guide-arch`) + ship-side 7 numbered subphases」；实测 ADR-0001 实际写的是 `guide-spec.md` 的 **5 phase (setup/roadmap/propose/deps/spec-done)** 与 ship 端 **「5 阶段 + 1 退出」** ⇒ 两处 phase 名单都对不上 ⇒ 这是**失效断言**，**不能**按 `history` 豁免（豁免一条假断言 = 给假通过发通行证）⇒ 需文本处置或批 7 的 RETIRED 注记形态 |
| `general` | 145 | **三方锁定**：`tests/unit/test_doc_contracts.py:67-68` 断言 `"guide-arch" in spec` 且 `"guide-plan" in spec`（子串锁）⇒ 改指就红测；且它描述的 `docs/improvement-suggestions-format.md` **本身仍是 v3 名**（实测 `:9` 仍写 `guide-design` / `guide-plan`）⇒ 需专项（改测试 → 改文档 → 改 spec 三方联动） |
| `general` | 146 | 同上 |
| `general` | 147 | 同上（`:147` 的 `guide-spec` 是**阴性**断言「SHALL NOT list」，不受 `:46-59` 的 active-reference 正则约束 ⇒ 不构成额外锁定） |

## 记 tail（范围外）

1. `dashboard-verification-status` 的围栏示例与 schema 脱节：缺 `rdd-builder` / `pending-agent`，且含 schema 枚举外的 `null` ⇒ 需**文本修正**专项（不是标注能解决的）。
2. `general/spec.md:123-130` 整个 Scenario 对 ADR-0001 的断言漂移（phase 名单与 ship 端计数都对不上）⇒ 需文本处置或 RETIRED 注记形态（**不能**按 history 豁免）。
3. 9 份 spec 是**未合并的 delta 形态**工件（首行 `## ADDED Requirements`；`migration-docs` / `release-management` 的 validate 既有 ERROR 即源于此）⇒ 它们是 v2.0/v3 期的 change delta 被误归档为 capability spec ⇒ 台账里各记一行，防批 6 / 批 7 把它们当普通形态误判。

