# 验收报告 — annotate-spec-residue-guard-batch3

- **change**：`openspec/changes/annotate-spec-residue-guard-batch3/`
- **定位**：`fix-spec-residue-guard` 的 **Phase 1 第三批**。**零文本改动**，只在 52 个命中行的下一行插入
  `<!-- v4-residue:allow=<guard|rename-history> -->`。
- **验收时间**：2026-11-21
- **实现提交**：本提交
- **判据来源**：`proposal.md` 的 `## Acceptance`（AC-1 ~ AC-10）

## 审查链

| 环节 | 结论 | 关键处置 |
|---|---|---|
| critic 第 1 轮 | **REJECT（1 BLOCKER + 3 SHOULD_FIX + 2 NITS）** | ① **B1**（claim）：「`v4-residue-contract:10` 的 Requirement 正文 476 字符，加标注后 508 > 500 ⇒ 新增 `REQUIREMENT_TOO_LONG` ⇒ AC-3 不可能」② SF-1：`docs-v4-sync-scope-followup:85` 的 guard 判定正确，但行内引用的过滤词表已被 `c49ea379` 放宽 ⇒ 属 spec-vs-impl 漂移，必须记 tail（静默标注等于洗白）③ SF-2：proposal 表的处数是估算，应以机器实测为准 ④ SF-3：T2.5 须钉死「单趟重建」 |
| B1 实证 | **不成立**（但暴露了真问题） | 实测：`v4-residue-contract` 的命中行是 **L41**（`route-schema-enums-preserve-legacy-values` 的 GIVEN 夹具），**不是** L10 的长 Requirement ⇒ 插入后 `very long` 仍为 **0**，4/4 份 validate 输出**逐字节相同**。但 critic 指出的**机制副作用是真的** —— 它让我去查上一批，实测发现 `align-spec-residue-prior-18` 因只数一种 issue 而**漏判了 3 个新引入的 `very long`** |
| SF 处置 | ① 记 tail（含 `bats:273/288` 证据）② AC-7 改为机器实测 102 处 / 69 块 / 27 份 ③ T2.5 钉死单趟重建 ④ 新增 AC-3 采集口径（人类可读输出、`stdout`/`stderr` 分开、非 TTY、记 exit code）| N-1/N-2 均采纳 |

## 逐条判定与证据

| AC | 判定 | 证据 |
|---|---|---|
| AC-1 4 份未豁免 = 0、stale = 0 | **pass** | `scan_specs` ⇒ 4 份未豁免 **0**；`stale_allows` = **0** |
| AC-2 52 行标注，49 guard + 3 rename-history，独占一行紧随命中行 | **pass** | 扫描器对批 3 的分类：`{'guard': 86, 'rename-history': 3}` = 89 处；`rename-history` 3 处全在 `doc-architecture-v4-sync` 的 `rename-history-bug-fixed` 块（L98/101/105） |
| AC-3 正文零改动（validate 输出逐字节） | **pass** | 4 份 `stdout`/`stderr` 与 T0 基线 `diff` **逐字节相同**（`stderr` 仅含既有 Purpose 占位 warning） |
| AC-4 改动文件恰 4 份 | **pass** | 逐份 `diff -q` ⇒ 4 份（快照 4 份，无第 5 份） |
| AC-5 `validate --all` ERROR == 11 | **pass** | 11 |
| AC-6 台账覆盖 52 行、无 unset、有 evidence | **pass** | `.rddf/reviews/spec-residue-annotate-batch3-2026-11-21.md`：52 行 + 逐文件汇总（10+3 / 14 / 15 / 10）+ tail 段 |
| AC-7 普查台账 191→102 / 111→69 / 31→27，幂等 | **pass** | 机器实测 **102 处 / 69 块 / 27 份**；两次生成 `diff` 为空 |
| AC-8 常数同提交更新 | **pass** | `test_r4_repo_residue_constant` 改为未豁免 102/69/27 + 含已豁免 333/181/46 |
| AC-9 单测绿 | **pass** | `pytest test_v4_residue_check.py test_spec_residue_census.py` ⇒ **54 passed** |
| AC-10 全量门 | **pass** | `BATS_TIMEOUT=120 BATS_TIMEOUT_RETRY=240 ./test.sh --full --regression` → **GATE_RC=0** + `✅ ALL PASSED`；bats **229/229 评估、未评估 0、新增失败 0** |

## 实施期发现并修正的问题（3 个）

| # | 问题 | 修正 |
|---|---|---|
| 1 | **台账分类用了改前行号** —— 应用时用改前行号是对的，但生成台账时扫描返回的是**改后**行号 ⇒ `rename-history` 被误判成 0 行 | 台账改按 **Requirement 标题** 判定（`rename-history-bug-fixed` 块）⇒ 恢复为 49 + 3 |
| 2 | **上一批（`align-18`）的 AC-6 判据过窄** —— 只数 `MUST include at least one Scenario` 一种 issue，漏掉 `REQUIREMENT_TOO_LONG` ⇒ 实测漏判 **3 个新引入的 `very long`**（`roadmap-feature-fragment` 457→526、`three-phase-skills` 437→505、`workflow-design-phase` 473→541） | ① 在 `align-18` 的验收报告里补「事后发现的判据缺陷」段（含三行明细 + 25 处既有的区分）② 本批改为 `stdout`/`stderr` 分开 + 逐字节 `diff` ③ 判据修正写入 `skills/rdd-doctor/SKILL.md` |
| 3 | **标注机制的固有副作用未记录** —— HTML 注释计入 openspec 的 Requirement 正文长度 ⇒ 临界长度（467–500）的 Requirement 加标注后会新增 advisory WARNING | 写进 `skills/rdd-doctor/SKILL.md` 的 R4 段（「机制固有代价、不是内容回归、验证须按 issue 类型多重集比对」） |

## 遗留清扫

- 本次范围内（T3.9）：无 TODO / 半截改写；`stale allow` = 0；台账无 `unset`。
- **记 tail**：`docs-v4-sync-scope-followup:85` 引用的过滤词表已被 `c49ea379` 放宽 ⇒ **spec-vs-impl 漂移**
  （不属五类 code），留后续批次；证据 `tests/integration/test_v4_doc_drift_contracts.bats:273,288`。
- **回滚凭据**：整树备份 `/tmp/opencode/specs-backup-b3-<TS>/`（165 份）+ per-file 快照（4 份）+ T0 的
  8 组 validate 输出（`/tmp/opencode/b3-base/`）。

## 失败项与路由建议

**本次验收无失败项** —— AC-1 ~ AC-10 全部 pass，全量门 `GATE_RC=0`。

## 已用轮次

- **critic 评审**：1 轮（REJECT on a claim that proved invalid empirically）—— 未用满 2 轮上限；
  其 3 条 SHOULD_FIX / 2 条 NITS 全部采纳。
- **验收轮次**：1 轮。
