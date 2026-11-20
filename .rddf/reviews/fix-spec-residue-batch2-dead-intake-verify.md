# 验收报告 — fix-spec-residue-batch2-dead-intake

- **change**：`openspec/changes/fix-spec-residue-batch2-dead-intake/`
- **定位**：`.rddf/improvements/fix-spec-residue-guard.md`（draft, P2）的 **Phase 1 第二批**（第一批 `retire-spec-musts-pointing-at-retired-objects` 已归档，13 份 / 34 处）
- **验收时间**：2026-11-20
- **实现提交**：本提交（唯一可入库交付物 = 处置台账 + 本验收报告；`openspec/specs/**` 的改动因 `.gitignore:45` 不产生 git diff）
- **归档**：`openspec/changes/archive/2026-11-20-fix-spec-residue-batch2-dead-intake/`（task 37/37；`iteration.json` 已由 `rddf archive-sync` + `sync_iteration_after_archive` 补齐 `tasks_done/tasks_total/archive_commit_sha`）
- **判据来源**：`proposal.md` 的 `## Acceptance`（AC-1 ~ AC-9 + AC-2b / AC-3b）

## 审查链

| 环节 | 结论 | 关键处置 |
|---|---|---|
| critic 第 1 轮 | **REJECT（3 BLOCKER + 2 SHOULD_FIX + 3 NITS）** | ① B1：`design-content-review-characterization-baseline` 是**活契约**（对象 `run_design_checks` `:193` + characterization 测试均在），我误判为「依赖 `design_content_review.sh`」；② B2：`iterative-plan-fill` 的两处「改指」不满足行为等价（`phase1_plan.sh` 单 change 只补 tasks.md、`phase1_5_deps.sh` 对 fill 零命中）；③ B3：`wave_scheduler_post_archive` **无活调用方**，不能作承接方 |
| 修正 | 9→8 条 RETIRED + 1 不动；2 改指 → 1 部分退役 + 5 RETIRED；`post-archive-fill-suggestion` 改判整条 RETIRED；`archive_change_for_mode` 换成活落点 | 另采纳 SF-1（死函数名）、SF-2（数字口径同步）、NITS-1（口径措辞） |
| critic 第 2 轮（复审） | **APPROVE_WITH_CONDITIONS**，mergeable: yes | 3 个 BLOCKER 全闭合经独立复核；新提 1 条 SHOULD_FIX（「2 部分退役 + 4 RETIRED」与逐条表「1 + 5」数字矛盾）+ 1 条 NITS（AC-1 冗余措辞）—— 均采纳 |

## 逐条判定与证据

| AC | 判定 | 证据 |
|---|---|---|
| AC-1 命中全落在 RETIRED/PARTIAL 段内 | **pass** | `/tmp/opencode/b2_bare_drift.py` → **`TOTAL bare drift: 0`**（判据：命中行须在 RETIRED/PARTIAL/已完成 段内，或落在正当注记的 ±8 行窗口内） |
| AC-2 RETIRED 标注 + Scenario 保留 | **pass** | `plan-intake-bootstrap` **8** 条、`iterative-plan-fill` **5** 条 RETIRED + **1** 条 PARTIAL、`verifier-v2-hardening` 2 处（KEEP + 注记）。**所有 Scenario 未删**（脚本只插注不改原文） |
| AC-2b `iterative-plan-fill` 零 REPOINT | **pass** | 台账中该 spec 的 `disposition` = PARTIAL×3 + RETIRED×12，**REPOINT×0** |
| AC-3 RETIRED/PARTIAL 注记写明承接方或判定依据 | **pass** | 逐条注记含证据锚点：`recommender.py:160` / `planner_deprecation.py:74` / `gate.py:378` / `phase3_archive.sh:277` / `sessions_cmd.py:17,381` / `SKILL.md:53` |
| AC-3b characterization 测试非 skip 且通过 | **pass** | `pytest tests/unit/test_propose_quality_check_characterization.py -q` → **3 passed**（复证 B1 的「活契约」判定） |
| AC-4 5 份 validate + strict 不增 | **pass** | 5/5：`openspec validate <cap>` 无 ERROR；`--strict` 的 `MUST include at least one Scenario` 与改前**同为 1**（基线即如此） |
| AC-5 改动文件 == 计划 5 份 | **pass** | 逐份 `diff -q` 与 T0.3 快照比对 → changed = **5**（iterative-plan-fill / plan-intake-bootstrap / post-archive-cleanup-hook / rddf-session-auto-archive / verifier-v2-hardening），无第 6 份 |
| AC-6 台账 37 行且无 unset | **pass** | `.rddf/reviews/spec-residue-census-2026-11-20-batch2.md` → **37 行**（KEEP 8 / PARTIAL 3 / REPOINT 4 / RETIRED 22），无 `unset` |
| AC-7 无源码改动 | **pass** | `git status --porcelain` 只有 `?? .rddf/reviews/spec-residue-census-2026-11-20-batch2.md` |
| AC-8 doc_contracts 绿 | **pass** | `pytest tests/unit/test_doc_contracts.py -q` → **13 passed** |
| AC-9 全量门 | **pass** | `BATS_TIMEOUT=120 BATS_TIMEOUT_RETRY=240 ./test.sh --full --regression` → **GATE_RC=0** + `✅ ALL PASSED`；bats regression **229/229 评估、未评估 0、已知失败 10、新增失败 0**；pytest unit **3455 passed / 3 skipped**；pytest integration **192 passed** |

## 判据缺陷修正记录

本批暴露 **2 处判据/验证脚本自身的缺陷**（已修正，非改实现）：

1. **AC-2b 措辞过窄** —— 原写「本批 0 处改指 ⇒ 台账无 REPOINT 行」，但 `post-archive-cleanup-hook`（`guide-ship` → `rdd-builder` P3）与 `rddf-session-auto-archive`（`guide-arch` → `rdd-arch`）的改动**确属 REPOINT**。收窄为「**`iterative-plan-fill` 零 REPOINT**」——那才是 critic B2 纠正的对象。

2. **T6.1 验证脚本过窄** —— 首版只检查「命中行本身或 Requirement 标题后 8 行」是否含 RETIRED/PARTIAL 标记，导致 `verifier-v2-hardening` 的 8 处 KEEP 命中（历史说明 `ac-verifier era`、已加注的 scan 夹具、已标「已完成」的 Requirement）被误报为裸漂移。修正为「**±8 行窗口 + 已完成标记**」后归零。

⇒ 印证既有教训：**零残留判据必须区分「活指令」与「历史说明 / 判据夹具 / 已完成计划」**，且**多行结构的注记要用窗口判定，不能只查单行**。

## 遗留清扫

- 本次范围内（T6.8）：**无新增** TODO / FIXME / 半截改写；台账无 `unset`（`grep -c unset` = 0）；注入标记 `fix-spec-residue-batch2` 共 **16** 处（= 8 + 6 + 2，与判定表一致）。
- 检出 **4 处既有 `TBD` 占位**（各 spec 的 `## Purpose` 段）—— 已核实**改前快照中同样存在**（T0.3 快照各 1 处）⇒ **非本次引入**，且是 **150/165 spec 的仓库级历史债** ⇒ 记 tail，不在本次清理。
- **范围外（记 tail，已在 proposal 的 Out of Scope 登记）**：
  - **其余 28 份含漂移 spec** —— 留给 `fix-spec-residue-guard` 的守卫（`v4_residue_check` 扫 `openspec/specs/`）驱动
  - **守卫**（`v4_residue_check` 的 spec 扫描面扩展 + 行内 allow + stale-allow 报错 + `checked 0` vs clean 区分）—— 归 `fix-spec-residue-guard`
  - **`AGENTS.md:118` / `:133` 的既有漂移**（`intake（含 changes_pre_created 跳过）` 与 `wave_scheduler_hooks.sh` 列为在役 bash 工具）—— critic NITS-2 指出，属后续批次

## 失败项与路由建议

**本次验收无失败项** —— AC-1 ~ AC-9（含 AC-2b / AC-3b）全部 pass，全量门 `GATE_RC=0`。

### 记 tail（范围外，不在本次路由）

以下都是**本次范围外**的既有问题，按「改动最小化」不趁机清理：

| tail | 性质 | 归属 |
|---|---|---|
| **其余 28 份含漂移 spec** | 剩余清理工作 | `fix-spec-residue-guard` 的守卫（`v4_residue_check` 扫 `openspec/specs/`）落地后按其输出驱动 |
| **守卫本身**（spec 扫描面扩展 + 行内 allow + stale-allow 报错 + `checked 0` vs clean 区分） | 上位规划 | `fix-spec-residue-guard` |
| **150/165 spec 的 `## Purpose` 仍是 `TBD - created by archiving ...` 占位** | 仓库级历史债（**非本次引入** —— 5 份的 Purpose 在 T0 快照里就已是 TBD） | 后续批次（与「剩余 28 份」同批处理更经济） |
| **`AGENTS.md:118` / `:133` 的既有漂移**（`intake（含 changes_pre_created 跳过）` / `wave_scheduler_hooks.sh` 列为在役 bash 工具） | critic NITS-2 指出 | 后续批次 |
| **B change 的 `wave_scheduler_hooks.sh:38,72` print 是死代码里的 print** | 该 hook 无活调用方 ⇒ 「每次 archive 都会告诉用户」的描述不准确 | 已在 B 的 proposal 记 tail；**若将来接线**，须同步该描述 |

### 回滚凭据

`openspec/` 整体 gitignored ⇒ 不可 `git revert`。回滚路径：

1. 整树备份 `/tmp/opencode/specs-backup-b2-<TS>/`（165 份）
2. per-file 快照 `/tmp/opencode/specs-b2-before/`（5 份）
3. per-file diff 日志 `/tmp/opencode/specs-b2-diff.log`（230 行 / 5 个文件）
4. 台账 `.rddf/reviews/spec-residue-census-2026-11-20-batch2.md` 记录每处改前行号 + 判定依据

## 已用轮次

- **critic 评审**：2 轮（第 1 轮 REJECT → 修正 → 第 2 轮 APPROVE_WITH_CONDITIONS）。未用满 2 轮上限，无需第 3 轮。
- **验收轮次**：1 轮（AC 全 pass，无需回 builder 修复）。

