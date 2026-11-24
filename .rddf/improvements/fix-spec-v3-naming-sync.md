---
优先级: P2
priority: P2
来源: 2026-11-17 文档审查 P1-7 —— 从 fix-doc-drift-residual 拆出：它需要 spec delta，
  与其余 tech-debt 项的交付形态不同；2026-11-24 立项前重测 ⇒ 范围由「8 处 v3 命名」
  收窄为「2 行 roadmap 归属断言」（命名部分已被后续改动修掉）
阶段: phase-2
分类: spec-drift
类型: spec-drift
状态: 已实施并验收（2026-11-24 立项 → 归档为 2026-11-24-fix-spec-v3-naming-sync；10/10 AC pass；活规范 owns 断言与 SKILL.md 对齐 + 新增归属漂移守卫）

生成时间: 2026-11-17
范围重测: 2026-11-24
roadmap_ref:
---

# fix-spec-v3-naming-sync

**主题**: 规范与现实一致

> **立项理由（为什么单独一条）**：本项要改 `openspec/specs/**`（能力 spec），产生 **spec delta**；
> 而 `fix-doc-drift-residual` 的其余五项是文档/守卫直改、不产生 delta。混在一条 change 里，
> archive gate 无法判定「这条 change 到底该不该有 spec delta」。拆开后两者各自可归档。

## 架构依据

### 现状（2026-11-24 立项前重测 — 取代 2026-11-17 的「8 处」快照）

2026-11-17 的原始快照记的是「8 处 v3 命名漂移」。**立项前重测发现命名部分已被后续改动修掉**，
只剩两处**不同性质**的残留 —— 一处是**合法豁免**，一处是**真漂移**：

| 位置 | 当前内容 | 性质（2026-11-24 实测） |
|---|---|---|
| `:10` | 「The 4 phase SKILL.md files (`rdd-arch`, `rdd-planner`, `rdd-builder`, `rdd-verifier`)」 | ✅ **已修** —— 命名同步已完成 |
| `:15`, `:23` | `WHEN skill_use("rdd-arch") (or any phase skill)`，同行附「（v4 重命名，原 `guide-arch`）」历史注记，且**下一行**是 `<!-- v4-residue:allow=rename-history -->` | ✅ **合法豁免** —— `spec_residue_scan.py` 的 `ALLOW_CODES` 含 `rename-history`（⑤ 重命名说明），这两处是**刻意保留的改名历史**，被 doctor `v4-residue` 守卫显式放行。**不是漂移，不应删** |
| `:135` | `#### Scenario: rdd-arch owns ADR + roadmap` | ❌ **真漂移** —— Scenario 标题仍把 roadmap 算作 rdd-arch 的 owns |
| `:139` | `- THEN it contains \`docs/adr/ADR-*.md\` and \`roadmap.md\` (matching the existing "职责边界" section)` | ❌ **真漂移** —— 断言 `roadmap.md` 在 owns 里 |

**真漂移的对照事实（三方一致地指向 spec 错）**：

| 权威来源 | 对 rdd-arch 的 owns 的陈述 |
|---|---|
| `docs/adr/ADR-0048-v4-stage-merge-revision.md` 决策 1c | 「`role.boundaries.owns` 移除 roadmap 相关：`roadmap.md` / `.rddf/roadmap/phases/*.md` / `.rddf/roadmap/features/*.md`」 |
| `skills/rdd-arch/SKILL.md:25-36`（实现） | `owns:` = `docs/adr/ADR-*.md` + `docs/architecture/*.md` + `.rddf/state/.arch-handoff.json`；`not_owns:` 含 `roadmap.md` / `.rddf/roadmap/phases/*.md` / `.rddf/roadmap/features/*.md` |
| `openspec/specs/skill-role-model/spec.md:139`（本项要修的） | 「it contains `docs/adr/ADR-*.md` and `roadmap.md`」 ❌ |

⇒ **规范与已签批 ADR、与实现三方矛盾**。读者按 spec 去查 rdd-arch 的 owns，会得到一个与实现相反的答案。

### 为什么它没被现有守卫发现

`test_v4_doc_drift_contracts.bats` 的 guide-* 守卫扫的是 `skills/**` 与 `docs/architecture/**`
（本轮实测：扩到 `openspec/specs/` 会命中 48 份文件 / 223 处）。**`openspec/specs/**` 至今不在任何
guide-* 守卫的扫描面内** —— 所以 `skill-role-model` 的残留一直**没有任何断言能发现它过期**。

> ⚠️ **注意**：doctor 的 `v4-residue` 守卫**只**管「退役 token 是否被合法豁免标注」，
> **不**管「归属断言是否与 ADR-0048 / SKILL.md 一致」⇒ `:135` / `:139` 这一类漂移
> 落在两个守卫的**缝隙**里。这正是本项要补的那条断言。

### 为什么范围只限 `skill-role-model`

`openspec/specs/` 下 guide-* 共 48 处分布在 48 份 capability spec 里。全改等于重写 48 个 capability
的 spec delta —— 与本项的真实诉求（「本仓角色模型的规范描述与现实一致」）不成比例。
其余 47 份属历史 change 的 spec 快照，它们的 guide-* 是**当时正确**的记录，不改。

判据：`skill-role-model` 是**活规范**（它约束当前 SKILL.md 的 frontmatter），其余是**历史快照**。
只有活规范的过期才是缺陷。

## 范围

**In Scope**：
- `openspec/specs/skill-role-model/spec.md` 的 **`Requirement: skill-role-boundaries-accurate`** 段（`:135` Scenario 标题 + `:139` THEN 断言）—— 按 ADR-0048 决策 1c 改为 rdd-arch 的**实际 3 项 owns**
- 守卫：把「活规范归属断言」检查加进 `tests/integration/test_v4_doc_drift_contracts.bats`（**活规范清单**形式，清单显式化以便未来扩）

**Out of Scope**：
- `:10` / `:15` / `:23` 的命名 —— **已完成**（2026-11-24 实测）；`:15` / `:23` 的 `guide-arch` 历史注记**受 `v4-residue:allow=rename-history` 豁免保护，刻意保留，不得删**
- `openspec/specs/` 下其余 47 份 capability spec（历史快照，guide-* 是当时正确记录）
- `skills/**` / `docs/**` 的 guide-*（已由 `fix-doc-drift-residual` 覆盖）
- 修改 `rdd-arch` 的 owns 或任何 SKILL.md frontmatter（本项只改规范文本）—— `skills/rdd-arch/SKILL.md` **已经是正确的**，本项是让 spec 追上实现，不是反过来

## Why

活规范描述不存在的 skill，是本仓最贵的一类漂移：读者按 spec grep `guide-arch` 会 0 命中
（因为 skill 已删），于是要么以为 spec 作废、要么以为 skill 丢了。而其中那条 Scenario
断言 `guide-arch owns ADR + roadmap` 更是**直接与 ADR-0048 的已签批决策相反**——
规范与决策互相矛盾时，读者无法判断以谁为准。

## What Changes

1. **重写 `openspec/specs/skill-role-model/spec.md` 的 `Requirement: skill-role-boundaries-accurate` 段**：

   - `:135` Scenario 标题：`Scenario: rdd-arch owns ADR + roadmap`
     → **`Scenario: rdd-arch owns ADR + theme doc`**（**不含 roadmap** —— 守住 AC-1）
   - `:139` THEN 断言：`it contains \`docs/adr/ADR-*.md\` and \`roadmap.md\``
     → **`it contains \`docs/adr/ADR-*.md\`, \`docs/architecture/*.md\` and \`.rddf/state/.arch-handoff.json\``**
     （3 项取自 `skills/rdd-arch/SKILL.md:26-28` 的 `owns:`，逐字一致）

   > **⚠️ 为什么 spec 正文不写「does NOT contain roadmap.md」**：那会让该文件的 `roadmap.md` 命中数变成 1，
   > 与 **AC-2（命中数 = 0）** 直接冲突；而且 AC-1 要求标题**不含** `roadmap`。
   > ⇒ spec 正文只说「**拥有哪 3 项**」（正面答案），**「不把 roadmap 归给 rdd-arch」这层负向事实交给守卫**（AC-6）。
   > 读者从 spec 得到的是与实现一致的正面答案；归属漂移由断言盯住，而不是在正文里留一个被 AC-2 禁止的 token。
   > 这也是「按**形态类**治理、不按措辞治理」的一致做法（参见 `test_spec_requirement_form.py` 的教训 ⑦）。

2. **守卫**：`tests/integration/test_v4_doc_drift_contracts.bats` 增加「活规范归属断言」检查：

   - 维护一个**活规范清单**（当前只有 `openspec/specs/skill-role-model/spec.md`），以变量形式写在测试顶部，注明「新增活规范时追加，历史快照不追加」
   - 对清单内每份 spec 断言：**不得**出现 `owns ADR + roadmap` 这类把 roadmap 归给 rdd-arch 的表述；且 rdd-arch 的 owns 断言里**不得**出现 `roadmap.md`（含 Scenario 标题 —— 标题含 `roadmap` 也算漂移）
   - **不做** guide-* 零命中断言 —— 清单内 spec 允许带 `<!-- v4-residue:allow=rename-history -->` 标注的改名历史注记（doctor `v4-residue` 的合法豁免）；本项不与该守卫抢同一判据

## Acceptance

- [x] `grep -c "owns ADR + roadmap" openspec/specs/skill-role-model/spec.md` = 0；且新 Scenario 标题含 `owns ADR` 且**不含** `roadmap`
- [x] `grep -c "roadmap.md" openspec/specs/skill-role-model/spec.md` = 0（2026-11-24 实测：`:135` 标题含 `ADR + roadmap`（无 `.md`），`:139` 含 `roadmap.md` ⇒ 全文 `roadmap.md` 命中数为 **1**；改完须为 0）
- [x] 新 Scenario 的 Given/When/Then 与 `skills/rdd-arch/SKILL.md` 的 `role.boundaries.owns` **逐项一致**（3 项：`docs/adr/ADR-*.md` / `docs/architecture/*.md` / `.rddf/state/.arch-handoff.json`），且该 spec 正文**不再出现** `roadmap.md`（与 AC-2 一致）；「不把 roadmap 归给 rdd-arch」的负向断言由**守卫**承担（见 AC-6），不写进 spec 正文
- [x] `grep -c "guide-arch\|guide-design\|guide-plan\|guide-ship" openspec/specs/skill-role-model/spec.md` = 2，**且这 2 行的下一行**都是 `<!-- v4-residue:allow=rename-history -->`（即：本项**不删**改名历史，只保证它们仍是合法豁免而不是漏标）
- [x] `rddf doctor --category v4-residue` 对该 spec **无新增 finding**（改动不得破坏既有豁免标注）
- [x] 守卫：「活规范清单」内的文件**不得**出现把 roadmap 归给 rdd-arch 的表述；变异验证：往该 spec 的 Scenario 标题加回 `+ roadmap` ⇒ 红
- [x] **不误伤历史快照**：`grep -rlc "guide-arch" openspec/specs/ --include=*.md | grep -v skill-role-model` 的命中文件数保持不变（本项不改它们），且新守卫不把它们算成失败
- [x] `git diff --stat openspec/specs/` 只含 `skill-role-model/spec.md`
- [x] 本项产生 spec delta：`openspec/changes/<name>/specs/skill-role-model/spec.md` 存在且与主 spec 的改动一致
- [x] `openspec validate skill-role-model --strict` **不新增 warning**（⚠️ 口径更正：原写「通过」不可满足 —— 该 spec 改动**前**就有 2 条既存 warning：`## Purpose` 是 archive 写的 `TBD` 占位、`requirements[1]`（`skill-role-schema-defined`，3372 字符）超 500；两条都与本项无关，**不在本项范围**。判据改为「改动前后 warning 集合不变」—— 本项改的是 `requirements[2]`（204 字符），不产生新 warning）

## Capabilities

- 读者：`skill-role-model` spec 里 rdd-arch 的 owns 与 `skills/rdd-arch/SKILL.md` / ADR-0048 一致，不再出现「规范说拥有、实现说 not_owns」的反向答案
- 维护者：活规范清单显式化 —— 归属断言的漂移从「靠人工审查发现」变成「有断言能发现」
- 边界：本项**不改**任何归属关系（ADR-0048 已签批，实现已正确），只让规范追上实现

## Impact

- **受影响文件**：`openspec/specs/skill-role-model/spec.md`（**2 行**：`:135` Scenario 标题 + `:139` THEN 断言）、`tests/integration/test_v4_doc_drift_contracts.bats`（活规范归属断言守卫）
- **回归风险**：低 —— 只改一份 spec 的 2 行措辞 + 1 条守卫；风险在「改错归属」（须对照 ADR-0048 决策 1c 与 `skills/rdd-arch/SKILL.md:26-28` 的 `owns:` 三项）
- **前置依赖**：`ADR-0048`（rdd-arch 脱离 roadmap）是重写 Scenario 的依据；`ADR-0043/0044`（v4 阶段与 guide-* 硬删除）
- **估算**：~1 小时
- **范围变更记录**：2026-11-17 初稿记「8 处 v3 命名」；2026-11-24 立项前重测 ⇒ 命名部分已被后续改动修掉（`:10` 已改，`:15`/`:23` 是**合法豁免**的历史注记，不得删），真漂移收窄为 2 行 roadmap 归属断言。原 AC「guide-* 零命中」**已废弃** —— 它会要求删掉 doctor `v4-residue` 明确豁免的 `rename-history` 注记。

## 审稿记录

**metis 第 1 轮（2026-11-17，作为 `fix-doc-drift-residual` 的一部分受审）**：

| finding | 处置 |
|---|---|
| 「P1-7 需要 spec delta，与其余 10 条 AC 生命周期不同，混在一起会永远 archive 不干净」 | ✅ **采纳** → 本项从 `fix-doc-drift-residual` 拆出，成为独立 improvement |
| 「AC『`openspec/specs/` 全目录 guide-* 零命中』实测 223 处 / 48 份，与『P1-7 需一条 spec delta』差两个数量级」 | ✅ **采纳（实测 48 份确认）**：本项范围只限 `skill-role-model`，并在 Out of Scope 写明「其余 47 份是历史快照，其 guide-* 是当时正确记录」 |
| 「`Scenario: guide-arch owns ADR + roadmap` 与 v4 矛盾（ADR-0048）」 | ✅ 采纳：What Changes #3 按 ADR-0048 重写该 Scenario，并写明新 owns 的 3 项 |

**2026-11-24 立项前重测（builder，自查）**：

| 观察 | 处置 |
|---|---|
| `:10` / `:15` / `:23` 的命名**已不是漂移** —— `:10` 已改；`:15`/`:23` 是带 `<!-- v4-residue:allow=rename-history -->` 标注的**合法豁免**历史注记（`spec_residue_scan.py::ALLOW_CODES` 第 ⑤ 类） | ✅ **范围收窄** ⇒ 原 AC「guide-* 零命中」**废弃**（它会要求删掉合法豁免），改为「命中只允许出现在带 `rename-history` 标注的行」 |
| 真漂移收窄为 `:135`（Scenario 标题）+ `:139`（THEN 断言）两行：都把 `roadmap.md` 算作 rdd-arch 的 owns | ✅ 按 ADR-0048 决策 1c + `skills/rdd-arch/SKILL.md:26-28` 重写为实际 3 项 owns + 显式「不含 `roadmap.md`」 |
| 守卫缺口：现有 guide-* 守卫不扫 `openspec/specs/**`；doctor `v4-residue` 只管退役 token 的豁免标注，**不管归属断言** | ✅ 新守卫改为「活规范归属断言」，与 `v4-residue` **不抢判据**（前者查归属、后者查豁免标注） |

## 实施记录

**2026-11-24 · 立项 → 实现 → 归档（全绿）**

| 项 | 内容 |
|---|---|
| change | `2026-11-24-fix-spec-v3-naming-sync`（`openspec/changes/archive/`） |
| 改动 | `openspec/specs/skill-role-model/spec.md`（**2 行**：Scenario 标题 + THEN 断言）+ `tests/integration/test_v4_doc_drift_contracts.bats`（新增 1 个守卫用例 + 活规范清单变量） |
| spec delta | `## MODIFIED Requirements` ⇒ 归档时 `skill-role-model: update`（delta 与主 spec 逐字一致） |
| 代码改动 | **零**（未改任何 `.sh` / `.py`） |
| 验收 | 10/10 AC pass（verdict cache 锚点 = 分支 tip `8e391a18`） |
| 门禁 | 主仓 `./test.sh --full --regression` **ALL PASSED**（bats 新增失败 0 / 未评估 0 / zombie 0；pytest unit 3641 passed 0 failed；integration 192 passed；validate 163 passed 0 failed） |

### 立项前修正：两条 AC 互斥（已消解）

初稿的 **AC-2**（`roadmap.md` 命中数 = 0）与 **AC-3**（Scenario 须断言「不含 `roadmap.md`」）**不能同时成立** ——
断言「不含 roadmap.md」本身就得在正文里写出这个 token。同样 **What Changes #1** 给的标题
`owns ADR + theme doc (no roadmap)` 与 **AC-1**（标题须**不含** `roadmap`）也冲突。

**处置**：spec 正文只说「**拥有哪 3 项**」（正面答案，与实现逐字一致），
「不把 roadmap 归给 rdd-arch」这层**负向事实交给守卫**（AC-6）。读者从 spec 得到的是与实现一致的正面答案；
归属漂移由断言盯住，而不是在正文里留一个被 AC-2 禁止的 token。

### 立项前修正：AC-10 不可满足（已改判据）

原 AC「`openspec validate skill-role-model --strict` 通过」**达不到** —— 该 spec 改动**前**就有 2 条既存 warning：
`## Purpose` 是 archive 写的 `TBD` 占位、`requirements[1]`（`skill-role-schema-defined`，3372 字符）超 500。
两条都与本项无关（本项改的是 `requirements[2]`，204 字符）⇒ 判据改为「**改动前后 warning 集合不变**」，
并在 AC 文本里写明既存 warning 的出处与为何不在本项范围。

### 守卫设计：为什么是双向断言

只查负向（不出现 roadmap）会漏掉「**有人删掉某个真实 owns**」这类漂移 ⇒ 守卫同时做
**正向逐项比对**（owns 断言的条目必须与 `skills/rdd-arch/SKILL.md` 的 `owns:` 逐字一致）。
且**不与 doctor 的 `v4-residue` 抢判据**：后者查豁免标注，前者查归属。

### ⚠️ 第三次撞上同一堵墙（仓库级缺陷，见 `add-skills-lib-api-doc` 的实施记录）

本 change 归档时，D3 spec-delta 生成器**又一次**产出 `acceptance-N` + 恒真 WHEN 的退化形态 ⇒
`test_spec_requirement_form` 与 R4 常量双红 ⇒ 第三次合规重写 + 常量同步（161→162）。
**三次同因同构**（step 2 / step 4 / step 5）⇒ 根因确在 `generate_spec_delta()`，**另案立项**，本项不越界修改。

