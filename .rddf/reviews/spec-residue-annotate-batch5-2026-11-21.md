# spec 残留处置台账 — Phase 1 第五批（2026-11-21）

> 定位：change `annotate-spec-residue-guard-batch5`。
> 本批**零文本改动** —— 只在命中行**下一行**插入 `<!-- v4-residue:allow=<code> -->`（HTML 注释，渲染不可见）。
> 批次边界由**形态抽样**决定（`.rddf/reviews/spec-residue-remaining-forms-2026-11-21.md`），不是按命中量取头几名。
> `line` 列是**改前**行号。

| code | 行数 | 处数 | 含义 |
|---|---|---|---|
| `history` | 9 | 14 | 已归档的历史叙述 —— 类别 ④（**过去发生过什么**；删掉它历史记录本身就不存在） |
| `guard` | 4 | 8 | 反漂移判据 / 夹具 —— 类别 ③（**断言旧名不存在或用作示例数据**） |
| **合计** | **13** | **22** | |

## 逐行处置

| file | line | requirement_title | matched_token | disposition | code | evidence |
|---|---|---|---|---|---|---|
| openspec/specs/archive-auto-commit/spec.md | 93 | `rdd-builder` P3 lightweight mode MUST also call hel | guide-ship | ANNOTATE | `history` | 既有「**NOTE** (re-pointed 2026-11-17, per ADR-0061)」注记 —— 已归档的重命名叙述 |
| openspec/specs/complete-project-yaml-config-gaps/spec.md | 203 | guide-ship-phase-1-detect-lightweight | guide-ship | ANNOTATE | `history` | 既有「**NOTE** (retired 2026-11-17, per ADR-0036 AMENDED)」注记 —— 已归档的重命名叙述 |
| openspec/specs/migration-docs/spec.md | 9 | migration-guide-content | guide-spec | ANNOTATE | `history` | 描述 `docs/migration/v1-to-v2.md` 的「Backward Compatibility (guide-spec alias, sync layer)」段 —— v1→v2 迁移指南的**历史内容**（该 spec 本身是 delta 形态的 v2.0 期工件） |
| openspec/specs/migration-docs/spec.md | 33 | usage-doc-update | guide-arch,guide-plan,guide-ship | ANNOTATE | `history` | 描述 v2.0 的 USAGE.md 技能清单（`guide-arch`, `guide-plan`, `guide-ship`）—— v2.0 发布内容 |
| openspec/specs/propose-changes/spec.md | 37 | parent-feature-name-validation | guide-design | ANNOTATE | `guard` | GIVEN 夹具：描述**已删除**脚本写入的 typo 值（`guide-design/scripts/approve_proposal.sh` 不存在） |
| openspec/specs/rddf-layout-manifest/spec.md | 118 | acceptance-13 | guide-design,guide-plan,guide-ship | ANNOTATE | `guard` | 断言「**不再残留** `guide-design`/`guide-plan`/`guide-ship`」—— 反漂移判据；实测 `docs/architecture/state-and-events.md` 对这 3 个名 0 命中 ⇒ 判据今天为真 |
| openspec/specs/rddf-layout-manifest/spec.md | 123 | acceptance-13 | guide-design,guide-plan,guide-ship | ANNOTATE | `guard` | 同上（Scenario 的 THEN 复述该判据） |
| openspec/specs/release-management/spec.md | 9 | beta-version-published | guide-arch,guide-plan,guide-ship | ANNOTATE | `history` | 「v2.0 skills (guide-arch, guide-plan, guide-ship, loop) are available」—— v2.0-beta 发布内容（该 spec 是 delta 形态的 v2.0 期工件） |
| openspec/specs/spec-validation-gates/spec.md | 183 | rdd-builder P3 archive pre-flight MUST call validate | guide-ship | ANNOTATE | `history` | 既有「**NOTE** (re-pointed 2026-11-17, per ADR-0036 AMENDED)」注记 —— 已归档的重命名叙述 |
| openspec/specs/v4-planner-scope-correction/spec.md | 136 | sh-broken-removed-or-repointed | guide-design | ANNOTATE | `history` | 描述**已完成**的处置：坏 shim（指向已删除的 `guide-design/scripts/approve_proposal.sh`）「MUST be deleted or re-pointed」—— 实测 `skills/rdd-arch/scripts/approve_proposal.sh` 已不存在 ⇒ Requirement 已被满足，括注里的旧名是**过去发生过的历史事实** ⇒ 按 ①(c) 的区分（history = 叙述过去发生过什么）归 `history`，不归 `guard`（critic 第 1 轮 SF-3） |
| openspec/specs/verifier-archive-gate/spec.md | 10 | ADR-0035 documents verifier/archive dual-track bound | ac-verifier | ANNOTATE | `history` | 描述 **ADR-0035 的内容**（4 个场景含 fallback）；ADR-0035 至今仍保留该历史段落 + 2026-09-07 修订注记（`docs/adr/ADR-0035-*.md:7`）⇒ Requirement 今天仍为真 |
| openspec/specs/verifier-archive-gate/spec.md | 31 | STRICT_AC_GATE escalation token | ac-verifier | ANNOTATE | `guard` | 「per ADR-0045: **no** ac-verifier fallback」—— 否定断言（ADR-0045:32 已移除 fallback） |
| openspec/specs/verifier-lifecycle/spec.md | 166 | Verification failures SHALL route back to plan or sh | guide-plan,guide-ship | ANNOTATE | `history` | 既有「**NOTE** (re-pointed 2026-11-17, per ADR-0036 AMENDED)」注记 —— 已归档的重命名叙述 |

## 逐文件汇总

| spec | 行数 | 处数 |
|---|---|---|
| `archive-auto-commit` | 1 | 1 |
| `complete-project-yaml-config-gaps` | 1 | 1 |
| `migration-docs` | 2 | 4 |
| `propose-changes` | 1 | 1 |
| `rddf-layout-manifest` | 2 | 6 |
| `release-management` | 1 | 3 |
| `spec-validation-gates` | 1 | 1 |
| `v4-planner-scope-correction` | 1 | 1 |
| `verifier-archive-gate` | 2 | 2 |
| `verifier-lifecycle` | 1 | 2 |

## 记 tail（范围外，本批不改）

1. **代码块内的命中无法用行内标注豁免（机制缺口）**：`dashboard-verification-status:50`（2 处：`guide-plan` / `guide-ship`）在 **fenced JSON 代码块内**（`"route": "archive-ready|guide-ship|guide-plan|halted|null",`）。现有机制要求标注**紧跟命中行** ⇒ 标注会落进 JSON 示例（污染读者会照抄的示例）；放到围栏之后则前一行无命中 ⇒ 报 `stale allow`。**两个方向都不通** ⇒ 本批不动它。它是**全仓剩余唯一的 code-block 命中** ⇒ 扩展机制后即可清零。

   **建议的机制扩展**（另行立项，不并入本批）：标注紧跟**围栏结束行**时，豁免该代码块内的**全部**命中；三个限制条件：① 标注必须紧跟围栏结束行（局部性）；② 台账仍要求逐行 disposition；③ `code` 限 `enum` / `guard`。

2. **`general/spec.md`（4 行）—— 专项**：`:145-146` 被 `tests/unit/test_doc_contracts.py:67-68` 的子串断言锁定（必须含 `guide-arch` / `guide-plan`）且其描述的 `docs/improvement-suggestions-format.md` 本身仍是 v3 名 ⇒ 需「改测试 → 改文档 → 改 spec」三方联动。`:127-128` 对 ADR-0001 的断言**已漂移**（实测 ADR-0001 写的是 `guide-spec` 的 5 phase + ship 端「5 阶段 + 1 退出」）⇒ **不能**按 `history` 豁免。

3. **批 6 / 批 7**：E+F 形态 20 行（actor / 符号改指）、G 形态 18 行（已死块补 `RETIRED` 注记）—— 见形态抽样台账。

4. **既有缺陷（scope_exceeded backlog）**：① `dashboard-verification-status` 的围栏示例与 schema 脱节（缺 `rdd-builder` / `pending-agent`，含 enum 外的 `null`）⇒ 需文本修正专项；② 9 份 spec 是**未合并的 delta 形态**工件（首行 `## ADDED Requirements`）⇒ 它们的 validate 既有 ERROR 源于此。

