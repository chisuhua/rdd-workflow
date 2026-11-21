# 验收报告 — annotate-spec-residue-dead-blocks-batch7a

- **change**：`openspec/changes/annotate-spec-residue-dead-blocks-batch7a/`
- **定位**：`fix-spec-residue-guard` 的 Phase 1 **第七批（7a）** —— 整块已死的 Requirement 补
  `RETIRED` 注记 + `allow=history` 标注，**零原文改动**。
- **验收时间**：2026-11-21
- **实现提交**：本提交
- **判据来源**：`proposal.md` 的 `## Acceptance`（AC-1 ~ AC-10）

## 审查链

| 环节 | 结论 | 处置 |
|---|---|---|
| critic 第 1 轮 | **REJECT**（2 BLOCKER + 3 SF）；`mergeable: no` | **BLOCKER-1**：`plan-done-quality-gate` 的「整块已死」不成立（`run_plan_checks` 是 `run_all_checks` 的活 alias，`propose_quality_checks` 在 `_lib/gate.py:388-394` 的 v4 plan_done 注册表里活跃注册）⇒ **移出 7a**（17→15 行）。**BLOCKER-2**：我的取证错误「`validate_baseline.py` 不存在」（实际在 `skills/propose/scripts/`）+ NOTE 未可审 ⇒ 6 条 NOTE 全文进 proposal + 措辞区分。**SF-1**：块数 35→29 非 31（已按实测修正）。**SF-2**：tpfl 应改 `execute` 非 `stage_builder`（后者是 session kind）。**SF-3**：批 7 按 annotate/rewrite 打标 |
| critic 第 2 轮（复审） | **REJECT**（1 新 BLOCKER + 1 SF） | **B-NEW**：`spec-validation-gates` 的 NOTE 写两个校验器「无生产调用方」—— **假**（CI 在 `.github/workflows/test.yml:113-127` 与 `skills/propose/SKILL.md:552-558` 调它们）⇒ 该 Requirement 的核心判据**今天仍为真** ⇒ **整份 3 块 / 4 行移出 7a**（15→11 行）。**SF**：「7 条 NOTE」旧数已改 5 条 |
| critic 第 3 轮（复审，**用户批准**） | **APPROVE_WITH_CONDITIONS**（0 BLOCKER + 1 SF + 1 NIT）；`mergeable: yes` | 5 条 NOTE 的**全部 file:line 断言**逐条核验通过；「NOTE 不含退役名」纪律 5/5 成立。**SF**：tasks T0.6 残留已证伪的取证断言 ⇒ 已删。**NIT**：proposal AC-3「4 份」⇒ 已改「3 份」 |

## 逐条判定与证据

| AC | 判定 | 证据 |
|---|---|---|
| AC-1 3 份的 9 块未豁免 = 0；全仓 25/20/10 | **pass** | `scan_specs` ⇒ **25 处 / 20 块 / 10 份**；`roadmap-incremental` / `openspec-version-degradation` 各 **0**；`roadmap-proposal-guidance` 剩 1（块 L148 PARTIAL，属 7b） |
| AC-2 每 Requirement 1 条 NOTE + 每命中行 1 个标注；NOTE 不含退役名 | **pass** | 实测 **11 标注 / 5 注记**；`stale`=`invalid`=`ignored`=`fence_rejected`=`in_fence` 全 **0**（格式正确）；5 条 NOTE 逐条 grep 无 `guide-arch`/`guide-design`/`guide-plan`/`guide-ship`/`guide-spec`/`ac-verifier` |
| AC-3 零原文改动 | **pass** | 过滤掉插入的 NOTE/标注行后与 T0 快照逐行比对：3 份**全部相同**（21/190/171 行） |
| AC-4 诊断全 0；含已豁免不变；豁免 283→294 | **pass** | 含已豁免 **319 / 170 / 44**（不变）；已登记豁免 **294**（+11） |
| AC-5 `--json` issue 多重集：新增 **4 条** `very long` | **pass** | `--json` 比对：roadmap-proposal-guidance +2（`requirements[3]`/`[4]`）、roadmap-incremental +1（`[0]`）、openspec-version-degradation +1（`[0]`）= **4 条**；长度实测 215→**543**、107→**539**、239→**655**、333→**624**（`thin-wrapper` = 142 不变 —— 注记落在 Scenario 区） |
| AC-6 `validate --all` ERROR == 11 | **pass** | **11**（与基线一致） |
| AC-7 台账 + 形态台账 | **pass** | `.rddf/reviews/spec-residue-annotate-batch7a-2026-11-21.md`（9 块 / 11 行 + 5 条 NOTE 全文 + 两次收缩 + 三轮教训 + 判据缺口）；形态台账更新为「7a 完成 / 7b 待办 21 行」+ 两形态并存 + 7b 前置纪律 |
| AC-8 census 幂等 + 常数同步 | **pass** | 两次生成 `diff` 为空；`unset` **25**、豁免 **294**；`test_r4_repo_residue_constant` 同步 25/20/10 |
| AC-9 pytest + ruff | **pass** | **65 passed**；`ruff` All checks passed |
| AC-10 全量门 | **pass** | `./test.sh --full --regression` → **GATE_RC=0** + `✅ ALL PASSED` |

## 实施期发现

**1. 一个既有判据缺口（重要）**：`openspec validate` 的**文本输出不显示** `requirements[N]` 这类 issue ——
只有 `--json` 才报。⇒ 批 3/4/5 的「validate 逐字节相同」判据**没有覆盖** `very long` 增量
（批 5 在 `skills/rdd-doctor/SKILL.md` 记录过这个副作用，但验证口径漏了它）。
⇒ 本批改用 `--json` 比对，实测新增 4 条；已记入台账 tail（建议后续批次与验收流程统一改用 `--json`）。

**2. 近似长度预检的口径误差**：我的近似脚本把「落在 Scenario 区的注记」也算进 Requirement 正文长度
⇒ 预测 5 条（含 `thin-wrapper` 的 511），实测 4 条（该 Requirement = 142 不变）。
根因：`extractRequirementBody` 遇第一个 header 即 break ⇒ **Scenario 不计入** Requirement 正文长度。
⇒ 已改用 openspec 自己的 `MarkdownParser.parseSpec` 取实测长度。

**3. 三轮 critic 连续抓到同类断言错误**（已写入形态台账作为 7b 的前置纪律）：
① 落点证据指向 WAVE 判定而非轻量模式判定；② 「文件不存在」只查了 `_lib/` 根目录；
③ 「无生产调用方」漏了 CI 的 `.yml` 与 `SKILL.md` 的 bash 流程。

## 遗留清扫

- 本次范围内（T3.11）：无 TODO / 半截改写；11 标注 + 5 注记全部落盘，零原文改动可机判。
- **未处置的 25 行**（范围外，已明确移交）：批 7b = 21 行（`annotate` 14 / 改指 6 / `rewrite` 1）+ `general` 专项 4 行。

## 失败项与路由建议

**本次验收无失败项** —— AC-1 ~ AC-10 全部 pass，全量门 `GATE_RC=0`。

## 已用轮次

- **critic 评审**：**3 轮**（REJECT → REJECT → APPROVE_WITH_CONDITIONS）—— 第 3 轮经用户明确批准。
- **验收轮次**：1 轮
