# 验收报告 — align-spec-residue-prior-18

- **change**：`openspec/changes/align-spec-residue-prior-18/`
- **定位**：`fix-spec-residue-guard`（已归档）的 **Phase 1 第一步** —— 让 18 份已签批 spec 的机器可读状态
  与既有签批一致。
- **验收时间**：2026-11-20
- **实现提交**：本提交（唯一 tracked 交付物 = 处置台账 + 重生成的普查台账 + 测试常数）
- **判据来源**：`proposal.md` 的 `## Acceptance`（AC-1 ~ AC-13）

## 审查链

| 环节 | 结论 | 关键处置 |
|---|---|---|
| critic 第 1 轮 | **REJECT（2 BLOCKER + 3 SHOULD_FIX + 5 NITS）** | ① **B1**：`proposal-lifecycle-sync:113` 的 REPOINT 会冻进**假契约** —— `.plan-handoff.json` 已随 ADR-0044 Wave 3 RETIRE（`docs/schemas/README.md:51`），`skills/rdd-builder/` 对 `plan-done` **0 命中**（v4 的 `plan_done` checks 无 dirty-improvement-approved 判据），语义祖先 `check_dirty_key_files` 是孤儿。② **B2**：AC-7 / AC-11 字面不可通过 —— 18 份里 **3 份已 0 命中**（实际改动面 15 份），且 AC-11「只有台账」与 AC-10/AC-12 矛盾 |
| 修正 | B1 → 改判 ADD_NOTE RETIRED（REPOINT 17→16、ADD_NOTE 7→8）；B2 → AC-1/7/11 改为「仍有命中的 15 份」+ 三项白名单 | SF-3 **升格**：`workflow-design-phase` 的 `Session Schema` 块被 batch1 **过度退役**（其断言今天仍为真）⇒ 该行改 `enum` + 追加块级澄清 |
| critic 第 2 轮（复审） | **APPROVE_WITH_CONDITIONS**，mergeable: yes | 2 个 BLOCKER 全闭合（独立复核）；新提 1 SF（Impact 段计数残留 94/7/17）+ 2 NITS —— 均采纳 |

## 逐条判定与证据

| AC | 判定 | 证据 |
|---|---|---|
| AC-1 15 份未被豁免命中 = 0 | **pass** | `scan_specs` ⇒ 这 18 份的未豁免命中 **0**（3 份本就 0 命中） |
| AC-2 96 行标注（93 + ENUM 3）独占一行、紧跟命中行 | **pass** | 应用脚本单趟 emit：`line → annotation` 紧邻；`grep -c 'v4-residue:allow='` 新增 **142**（含注记自带的标注） |
| AC-3 8 行 ADD_NOTE 形态与 batch1/batch2 一致 | **pass** | 单行注记 `> **RETIRED\|PARTIAL (2026-11-20, align-spec-residue-prior-18)** —— <理由>。保留原文与 Scenario 作为历史记录。`；**Scenario 一律保留** |
| AC-4 16 行 REPOINT 逐字节等于 proposal 表 | **pass** | `rdd-builder.md` 出现 **0** 次；`skill-role-model:157` 为 `(`rdd-arch`, `rdd-planner`, `rdd-builder`, `rdd-verifier`)`（`rdd-builder` 不重复） |
| AC-5 无 `stale allow` | **pass** | `stale_allows` = **0** |
| AC-6 15 份 validate 无 ERROR、strict 不增 | **pass** | 15/15 合规（ERROR=0 / strict=1，与 T0.3 基线一致） |
| AC-7 改动文件 ⊆ 15 份，3 份零改动 | **pass** | 逐份 `diff -q` 与 T0.2 快照比对 = **15 份**（3 份 0 命中的文件未变） |
| AC-8 `validate --all` ERROR 不增 | **pass** | **11**（与基线一致） |
| AC-9 台账覆盖 120 行、无 `unset`、汇总表 15 行 | **pass** | `.rddf/reviews/spec-residue-align-18-2026-11-20.md`：120 行（ANNOTATE 93 / ENUM 3 / ADD_NOTE 8 / REPOINT 16）+ 15 行汇总 + 「0 命中的 3 份」段 |
| AC-10 普查台账重生成 ⇒ 18 份 0；全集 350→191 | **pass** | 全集待办 **350 → 191 处 / 192 → 111 块 / 46 → 31 份**；幂等（两次生成 `diff` 为空）。⚠️ 低于原估 230：16 行改指**移除**了 token，且补的注记文本自身也落在标注下 |
| AC-11 `git status` 只出现三项 | **pass** | 处置台账 + 普查台账 + `tests/unit/test_v4_residue_check.py` |
| AC-12 单测绿 + 常数同步 | **pass** | `pytest test_v4_residue_check.py test_spec_residue_census.py` ⇒ **54 passed**；常数改为**双口径**（未豁免 191/111/31 + 含已豁免 333/181/46） |
| AC-13 全量门 | **pass** | `BATS_TIMEOUT=120 BATS_TIMEOUT_RETRY=240 ./test.sh --full --regression` → **GATE_RC=0** + `✅ ALL PASSED`；bats **229/229 评估、未评估 0、新增失败 0** |

## 实施期发现并修正的 4 个缺陷（都在应用脚本，不在 spec）

| # | 缺陷 | 修正 |
|---|---|---|
| 1 | **注记不产生豁免** —— 扫描器只认行内标注；补了 `RETIRED` 注记后块内命中仍未豁免 | ADD_NOTE 块的**所有命中行**同时补 `allow=history` 标注 |
| 2 | **同一块被插 3 条注记** —— `roadmap-feature-fragment` 的 3 个命中行各自触发一次插入 | 按「块标题」去重，一块一条 |
| 3 | **行号漂移** —— 先用 `insert` 再按原行号改标注 ⇒ 标注落到错行（7 个 stale + 9 个漏标） | 改为**单趟重建**：按原始行号顺序 emit（line → annotation → note），插入不影响未处理行 |
| 4 | **注记自身也可能命中旧名**（如「`skills/guide-design/` 不存在」）⇒ 无条件给它加标注会产生 stale | 条件化：注记文本匹配 token 才追加标注 |

> 另修 **`_block_end` 的块边界**：Requirement 块应**包含**其下 Scenario（首版在第一个 `#### Scenario:` 处就截断 ⇒ 2 行漏标）。

## ⚠️ 事后发现的判据缺陷（AC-6 过窄）

本报告的 AC-6 原本只数 `openspec validate --strict` 输出里的 **`MUST include at least one Scenario`**
这一种 issue ⇒ **漏掉了另一种** issue：`REQUIREMENT_TOO_LONG`（`requirements[N]: very long (>500 characters)`）。

**实测后果**：标注行（`<!-- v4-residue:allow=... -->`，约 33 字符）落在 Requirement 正文里 ⇒
被 openspec 的 `extractRequirementBody` 计入正文长度 ⇒ 三个原本 457/437/473 字符的 Requirement
越过 500 阈值：

| spec | Requirement | 正文（去标注） | 正文（含标注） |
|---|---|---|---|
| `roadmap-feature-fragment` | `guide-arch Phase 4 menu integration` | 457 | 526 |
| `three-phase-skills` | `guide-arch-skill` | 437 | 505 |
| `workflow-design-phase` | `plan Phase Design-done Gate (hard switch)` | 473 | 541 |

（另有 **25 处** `very long` 是**既有**的 —— 去掉标注后仍超 500。）

**性质**：这是**标注机制固有的副作用**，不是内容回归 —— HTML 注释渲染不可见、不改变任何 MUST/SHOULD 语义；
`REQUIREMENT_TOO_LONG` 是 advisory WARNING（`openspec validate --all` 的 ERROR 数仍为 11）。
**已记录，不返工**：见 `skills/rdd-doctor/SKILL.md` 的 R4 段（机制副作用说明）。

**判据修正（后续批次适用）**：验证「标注不改变 issue」必须按 **issue 类型 + 目标**做**多重集比对**，
不能只数一种 issue —— 否则判据被平凡满足。`annotate-spec-residue-guard-batch3` 已按此口径执行
（`stdout`/`stderr` 分开存档 + 逐字节 `diff`）。

## 遗留清扫

- 本次范围内（T5.10）：无 TODO / 半截改写；**0 个 `stale allow`**；台账无 `unset`。
- **spec 改动不可 git 验证**（`openspec/` gitignored）⇒ 回滚凭据：整树备份 `/tmp/opencode/specs-backup-align18-<TS>/`（165 份）
  + per-file 快照（18 份）+ diff 日志 `/tmp/opencode/specs-align18-diff.log`（777 行 / 18 个文件）。
- **记 tail（范围外）**：
  | tail | 归属 |
  |---|---|
  | 剩余 **31 份 / 191 处 / 111 块**（Phase 1 后续批次） | 下一批 change |
  | `stage_plan` / `stage_ship` **kind 名漂移**（v4 实际创建 `stage_builder` / `stage_verify`；守卫只扫 skill 名，扫不到 kind 名） | 后续批次（critic SF-1） |
  | `rddf_session_hook_*` 在 v4 生产代码**无调用方**（仅 tests，注释还写 guide-ship Phase 3） | 既有漂移（critic NIT-5） |
  | 150/165 spec 的 `## Purpose` TBD 占位 | 仓库级历史债 |
  | 6 个非 capability 目录（`phase-*` ×5 + `tests`） | 测试残留，不删 |
  | `test.sh:86` 的「advisory gate (4 categories)」与 `_GATES["advisory"]` 的 5 个不符 | 既有漂移 |
  | `general/spec.md`（`test_doc_contracts.py:64-68` 锁定） | Phase 1 后续批次 |

## 失败项与路由建议

**本次验收无失败项** —— AC-1 ~ AC-13 全部 pass，全量门 `GATE_RC=0`。

## 已用轮次

- **critic 评审**：2 轮（REJECT → 修正 → APPROVE_WITH_CONDITIONS），已达每 change 2 轮上限。
- **验收轮次**：1 轮（含 4 个应用脚本缺陷的迭代修正 —— 属实施过程，不是验收失败）。
