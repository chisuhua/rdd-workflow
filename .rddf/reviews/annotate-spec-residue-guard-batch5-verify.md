# 验收报告 — annotate-spec-residue-guard-batch5

- **change**：`openspec/changes/annotate-spec-residue-guard-batch5/`
- **定位**：`fix-spec-residue-guard` 的 **Phase 1 第五批**。**纯标注，零文本改动**：13 行 / 22 处。
  批次边界由**形态抽样**决定（不是按命中量取头几名）。
- **验收时间**：2026-11-21
- **实现提交**：本提交
- **判据来源**：`proposal.md` 的 `## Acceptance`（AC-1 ~ AC-9）

## 审查链

| 环节 | 结论 | 处置 |
|---|---|---|
| critic 第 1 轮 | **APPROVE_WITH_CONDITIONS**（0 BLOCKER + 3 SHOULD_FIX + 3 NITS） | **SF-1**：我对 `general/spec.md:127` 的取证**错了** —— ADR-0001 实际写的是 `guide-spec` 的 5 phase（setup/roadmap/propose/deps/spec-done）+ ship 端「5 阶段 + 1 退出」，与该行的 phase 名单和「7 numbered subphases」**都对不上** ⇒ 它是**失效断言**，**不能**按 `history` 豁免 ⇒ 形态台账的尾项 2 理由已改写。**SF-2**：AC 必须钉死新常数 ⇒ 已钉死（并被实测修正，见下）。**SF-3**：`v4-planner-scope-correction:136` 应归 `history`（按 ①(c) 自己的区分：history = 叙述过去发生过什么）⇒ 已改，批 5 变 `history` 9 / `guard` 4。**NIT-1**：`:10` 与 `:31` 两个 code 并存成立（code 分类的是**文本角色**，不是逻辑极性）⇒ 维持。**NIT-2**：采集口径补 4 项。**NIT-3**：尾项 1 的机制扩展补 3 个限制条件 |
| 实施期修正 | — | **AC-7 的份数被我初稿与 critic 的推断同时算错** ⇒ 实测修正（见「实施期发现的判据缺陷」） |

## 逐条判定与证据

| AC | 判定 | 证据 |
|---|---|---|
| AC-1 10 份未豁免命中 = 0、stale = 0、invalid = 0 | **pass** | `scan_specs` ⇒ 批 5 的 13 行**全部**转为豁免；`stale_allows` = **0**；`invalid_annotations` = **0**；`ignored_inline` = **0**（标注格式正确：独占一行、紧跟命中行） |
| AC-2 13 行标注（`history` 9 / `guard` 4）独占一行紧跟命中行 | **pass** | 扫描器回读：批 5 的 code 分布 = `history` 9 行 / 14 处、`guard` 4 行 / 8 处 = **13 行 / 22 处** |
| AC-3 正文零改动（validate 逐字节不变） | **pass** | 10 份 × 5 组输出（`stdout` / `stderr` / `--strict` stdout / `--strict` stderr / exit code）与 T0 基线**逐字节相同**；`openspec validate --all` 的 `out` / `err` / exit code 也**逐字节相同**。预检：13 行涉及的 Requirement 正文长度（含标注口径）最大 471 ⇒ 无一跨 500 ⇒ 不会新增 `very long` |
| AC-4 改动文件恰 10 份 | **pass** | 与 T0 per-file 快照逐份 `diff -q` ⇒ **10** 份（`dashboard-verification-status` 零改动） |
| AC-5 `validate --all` ERROR == 11 | **pass** | **11**（与基线一致；`migration-docs` / `release-management` 各 1 个是**既有** ERROR —— 未合并的 delta 形态工件） |
| AC-6 台账覆盖 13 行、无 unset、每行有 evidence | **pass** | `.rddf/reviews/spec-residue-annotate-batch5-2026-11-21.md`：13 行（`history` 9 / `guard` 4）+ 逐文件汇总 + 4 条 tail |
| AC-7 普查台账 66→44 / 49→36 / 24→16，幂等；常数同步 | **pass** | 机器实测 **44 处 / 36 块 / 16 份**；含已豁免保持 **325 / 176 / 46**（豁免 259 → **281**）；两次生成 `diff` 为空；`test_r4_repo_residue_constant` 同步为 44/36/16 + 325/176/46 |
| AC-8 单测绿 + ruff 全绿 | **pass** | `pytest test_v4_residue_check.py test_spec_residue_census.py` ⇒ **54 passed**；`ruff` ⇒ All checks passed |
| AC-9 全量门 | **pass** | `BATS_TIMEOUT=120 BATS_TIMEOUT_RETRY=240 ./test.sh --full --regression` → **GATE_RC=0** + `✅ ALL PASSED`；bats **229/229 评估、未评估 0、新增失败 0**；`./test.sh --gates` ALL PASSED |

## 实施期发现的判据缺陷（1 处，已修正）

**AC-7 的「份数」被我初稿与 critic 的推断同时算错。**

我初稿写「未豁免 44 / 36 / **14** 份 + 含已豁免 **303 / 163** / 46」，critic 的推断也是 44 / 36 / 14。
**实测 = 44 / 36 / 16**，且含已豁免的三个数**不变**（325 / 176 / 46）。两处错因：

1. **标注不消除命中，只标记豁免** ⇒ 「含已豁免」的处数/块数/份数**一个都不变**（我误当成「命中被移除」，
   减了 22 处 / 13 块）。只有「已登记豁免」计数 +22（259 → 281）。
2. **份数只减 8（不是 10）** —— 10 份里有 2 份**仍有未豁免命中**：
   `complete-project-yaml-config-gaps`（3 处，属批 6 的 `_default_runner` 改指）、
   `spec-validation-gates`（4 处，属批 7 的死块）⇒ 它们留在待办清单里。

⇒ 已按实测值改写 AC-7 与 T3.5；**块数 36 恰好正确**（13 行各自独占一个 block）。

## 遗留清扫

- 本次范围内（T3.9）：无 TODO / 半截改写；`stale allow` = 0；台账无 `unset`。
- **spec 改动不可 git 验证**（`openspec/` gitignored）⇒ 回滚凭据：整树备份
  `/tmp/opencode/specs-backup-b5-<TS>/`（165 份）+ per-file 快照（10 份）+ T0 的 53 组 validate 输出
  （`/tmp/opencode/b5-base/`，含 `--strict` 与 `--all`）。
- **记 tail（范围外）**：4 条（见台账「记 tail」段）——
  ① 代码块内命中无法用行内标注豁免（**机制缺口**，需另立项扩展扫描器，含 3 个限制条件）；
  ② `general/spec.md` 4 行（测试锁定 + `:127` 断言漂移 ⇒ 专项三方联动）；
  ③ 批 6 / 批 7 的 38 行；④ 2 条 scope_exceeded backlog（围栏示例与 schema 脱节 / 9 份 delta 形态工件）。

## 失败项与路由建议

**本次验收无失败项** —— AC-1 ~ AC-9 全部 pass，全量门 `GATE_RC=0`。

## 已用轮次

- **critic 评审**：1 轮（APPROVE_WITH_CONDITIONS，0 BLOCKER）—— 未用满 2 轮上限；3 SF + 3 NITS 全部处置。
- **验收轮次**：1 轮（含 1 处 AC 数值的实测修正 —— 属判据本身，不属实施失败）。
