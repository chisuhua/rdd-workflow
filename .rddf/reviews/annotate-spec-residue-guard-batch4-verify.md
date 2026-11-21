# 验收报告 — annotate-spec-residue-guard-batch4

- **change**：`openspec/changes/annotate-spec-residue-guard-batch4/`
- **定位**：`fix-spec-residue-guard` 的 **Phase 1 第四批**。**首次混合形态**：纯标注 9 行 + 活契约改指 7 行
  + 已死块补注记 15 行（共 31 行 / 36 处 / 3 份）。
- **验收时间**：2026-11-21
- **实现提交**：本提交
- **判据来源**：`proposal.md` 的 `## Acceptance`（AC-1 ~ AC-11）

## 审查链

| 环节 | 结论 | 处置 |
|---|---|---|
| critic 第 1 轮 | **APPROVE_WITH_CONDITIONS**（0 BLOCKER + 2 SHOULD_FIX + 3 NITS） | **SF-1**：AC-5 的「issue 多重集相等」在本批**不成立**（7 行正文改动 ⇒ 正文长度变）⇒ 改为**枚举豁免式**（只允许 `very long` + 算术核对 + 白名单外即失败）。**SF-2**：`archive-gate-verification:72-76` 的 THEN 与实现**相反**（既有漂移），且 `ADR-0034:70` 的旧语义已被 ADR-0045 失效 ⇒ 两条都**记 tail**，ADR 那条**路由 architect**（builder 不得单方面改已签批 ADR 的决策内容）。**焦点 1(a)(b)(c) / 2 / 3 / 5 全部判定成立** |
| critic 焦点 4(b) 的长度预判 | 2 处高风险 + 1 处中风险 | 实施后**实测**：3 条新增 `very long` 全部落在预判的 3 个 Requirement 上（inline 两个已死块 + archive-gate 的 fallback 块） |

## 逐条判定与证据

| AC | 判定 | 证据 |
|---|---|---|
| AC-1 3 份未豁免命中 = 0、stale = 0 | **pass** | `scan_specs` ⇒ 3 份未豁免 **0**；`stale_allows` = **0**；`invalid_annotations` = **0** |
| AC-2 24 行标注（独占一行、紧跟命中行） | **pass** | 扫描器回读：inline 12 / doc-truth 4 / archive-gate 8 = **24** 行标注；按 code：`guard` 7 行 / 8 处、`history` 16 行 / 18 处、`rename-history` 1 行 / 2 处（合计 24 行 / 28 处 —— 改前 36 处，改指 7 行移除 8 处 token）。逐份：archive-gate 8 行全 `history`；doc-truth `guard` 3 + `rename-history` 1；inline `guard` 4 + `history` 8 |
| AC-3 7 行改指逐字节等于 proposal 表；改指后无退役名 | **pass** | 7 行新文本与 proposal 表一致；`scan_specs` 对 3 份的未豁免 = 0（改指行已无 token）；本批 3 份里 `rdd-builder.md` 出现 **0** 次；`doc-truth-sync:157` 的四连击断言本就不在这 3 份内（未被改动） |
| AC-4 4 处注记形态一致；注记文本无独立退役名；已死块内命中行仍逐行标注 | **pass** | 4 条注记均为单行 `> **RETIRED (2026-11-21, annotate-spec-residue-guard-batch4)** —— <理由>。保留原文[与 Scenario]作为历史记录。`；注记文本只引用 change 名 `remove-ac-verifier-completely` / spec 目录名 `inline-ac-verifier-into-rdd-verifier`（词边界不匹配 ⇒ 扫描器不视为命中）；15 个已死块命中行**全部**有 `allow=history` 标注（⇒ 未豁免 = 0 证明注记未替代标注） |
| AC-5 无新增 issue；若有则仅 `very long` 且可算术归因 | **pass** | 3 份 `validate` 的 `stdout`/`stderr` 与 T0 基线 diff：仅新增 3 条 `requirements[N]: very long`（inline `requirements[6]`/`[7]`、archive-gate `requirements[3]`）⇒ **类型白名单内**。算术核对（`/tmp/opencode/b4_arith.py`）：8 个有变化的 Requirement 的长度增量**全部**由该处插入/删除字符解释（Δ = 插入 − 删除，误差 ≤ 2）——`ac-verifier SHALL be marked deprecated` 431→906（+474 = 1 注记 + 4 标注）、`deprecation period…` 243→570（+327）、`Direct archive fallback…` 393→722（+329）、`Gate precedence…` 412→458（+46 = 改指句变长）、`Archive SHALL remain…` 461→495（+34 = 1 标注，**未越 500**）、`rdd-verifier self-contain` 422→454、`archive_gate_check…` 319→384、`doc-contract-tests-required` 2661→2734 |
| AC-6 改动文件恰 3 份 | **pass** | 与 T0 per-file 快照逐份 `diff -q` ⇒ 3 份（inline / doc-truth / archive-gate） |
| AC-7 `validate --all` ERROR == 11 | **pass** | **11**（与基线一致） |
| AC-8 台账覆盖 31 行、无 unset、每行有 evidence | **pass** | `.rddf/reviews/spec-residue-annotate-batch4-2026-11-21.md`：31 行（ANNOTATE 9 / REPOINT 7 / ADD_NOTE 15）+ 逐文件汇总 + 6 条 tail |
| AC-9 普查台账 102→66 / 27→24，幂等；常数同步 | **pass** | 机器实测 **66 处 / 49 块 / 24 份**（含已豁免 325 / 176 / 46，豁免 259）；两次生成 `diff` 为空；`test_r4_repo_residue_constant` 改为双口径 66/49/24 + 325/176/46 |
| AC-10 单测绿 | **pass** | `pytest test_v4_residue_check.py test_spec_residue_census.py` ⇒ **54 passed**；`ruff` 全绿 |
| AC-11 全量门 | **pass** | `BATS_TIMEOUT=120 BATS_TIMEOUT_RETRY=240 ./test.sh --full --regression` → **GATE_RC=0** + `✅ ALL PASSED`；bats **229/229 评估、未评估 0、新增失败 0** |

## 实施期发现并处理的问题（3 个）

| # | 问题 | 处置 |
|---|---|---|
| 1 | **算术核对脚本口径错配** —— `before` 用「含标注」口径、`after` 用「不含标注」口径 ⇒ 8 个 Requirement 全报 MISMATCH | 统一为含标注口径（与 openspec 的 `extractRequirementBody` 一致：它把 HTML 注释计入正文）⇒ 全部可归因 |
| 2 | **`grep -c 'ac-verifier'` 误报 3 条注记含退役名** —— `grep -E` 无词边界 ⇒ 把 `remove-ac-verifier-completely` / `inline-ac-verifier-into-rdd-verifier` 也算进去 | 以扫描器为准（它有词边界）：注记文本**不产生命中**（未豁免 = 0 已证明） |
| 3 | **`docs-v4-sync-scope-followup:13`** 说 README 树显示 `rdd-arch.md` / `rdd-builder.md` 等**单文件**名（v4 实为 `rdd-*/SKILL.md` 目录形态）—— 与本批 `doc-truth-sync:85` 同类漂移 | 记 tail（该文件属批 3，本批未改） |

## 遗留清扫

- 本次范围内（T5.9）：无 TODO / 半截改写；`stale allow` = 0；台账无 `unset`。
- **spec 改动不可 git 验证**（`openspec/` gitignored）⇒ 回滚凭据：整树备份
  `/tmp/opencode/specs-backup-b4-<TS>/`（165 份）+ per-file 快照（3 份）+ T0 的 6 组 validate 输出
  （`/tmp/opencode/b4-base/`）+ 长度基线（`b4-len-before-inc.json`）。
- **记 tail（范围外）**：见台账「记 tail」段 6 条 —— 其中两条**需路由**：
  ① `archive-gate-verification:72-76` 的 THEN 与实现相反 ⇒ 须**专项立项**（改 THEN = 改活契约的 MUST）；
  ② `docs/adr/ADR-0034-*.md:70` 的旧语义已被 ADR-0045:32 失效 ⇒ 须**切 architect** 补 amendment
  （builder 不得单方面改已签批 ADR 的决策内容）。

## 失败项与路由建议

**本次验收无失败项** —— AC-1 ~ AC-11 全部 pass，全量门 `GATE_RC=0`。

## 已用轮次

- **critic 评审**：1 轮（APPROVE_WITH_CONDITIONS，0 BLOCKER）—— 未用满 2 轮上限。
- **验收轮次**：1 轮（含 3 个实施期问题的修正，均在核对脚本/台账，不在 spec 内容里）。
