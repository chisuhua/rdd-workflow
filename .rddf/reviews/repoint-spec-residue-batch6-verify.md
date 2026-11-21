# 验收报告 — repoint-spec-residue-batch6

- **change**：`openspec/changes/repoint-spec-residue-batch6/`
- **定位**：`fix-spec-residue-guard` 的 Phase 1 第六批 —— **actor / 符号改指**（改文本，零标注）。
- **验收时间**：2026-11-21
- **实现提交**：本提交
- **判据来源**：`proposal.md` 的 `## Acceptance`（AC-1 ~ AC-11）

## 审查链

| 环节 | 结论 | 处置 |
|---|---|---|
| critic 第 1 轮 | **REJECT**（2 BLOCKER + 3 SF）；`mergeable: no` / `scope_exceeded: false` | **BLOCKER-1**：rfc-rddf 三行改指不成立 —— 我声明的落点（`ship_execution_mode.sh:97`）是**事实错误**（那是 WAVE 串并行判定，注释明写「it says nothing about the execution mode」；轻量模式判定是 `builder_deps.py::decide_execution_mode`，无 `openspec_tracked` 输入）⇒ 已移出，移交批 7。**BLOCKER-2**：常数须重算 ⇒ 已按实测钉死。**SF-1**：块数 35→31 应为 **35→29**（块口径 = Requirement **和** Scenario 各自成块）⇒ 已实测确认 6 块。**SF-2**：tpfl 应改 `execute` 而非 `stage_builder`（后者是 rddf-session kind，不是 trace 前缀）⇒ 已改。**SF-3**：repoint/annotate 二分漏 rewrite ⇒ 批 7 台账已按 `annotate` 31 / `rewrite` 1 打标 |
| critic 第 2 轮（复审） | **APPROVE**（0 BLOCKER / 0 SF / 1 NIT）；`mergeable: yes` | 只验 BLOCKER 闭合 + 新 diff。1 NIT = 「三种处置口径表」应沿用到批 7 ⇒ 已写进 `test_r4_repo_residue_constant` docstring |

## 逐条判定与证据

| AC | 判定 | 证据 |
|---|---|---|
| AC-1 3 份未豁免 = 0；全仓 36/29/12 | **pass** | `scan_specs(REPO_ROOT)` ⇒ 未豁免 **36 处 / 29 块 / 12 份**；`third-party-feedback-loop` / `post-flow-analysis` / `complete-project-yaml-config-gaps` 各 **0** |
| AC-2 落点可 grep | **pass** | `_lib/cli/orchestrate_cmd.py:728`（`glob(f"{phase}-*.jsonl")`）；`.rddf/state/trace/` 有 **60 个 `execute-*.jsonl`**；`_lib/cli/rdd_verify_cmd.py:33,132-141,158-160,514-521`（`_stage_context_runner` 是默认 runner，`_default_runner` 是已移除的 ADR-0045 shim 别名） |
| AC-3 配套一致性 | **pass** | tpfl 的 GIVEN（`execute-*.jsonl`）与 WHEN（`show execute`）**同 kind**；post-flow 的 `--phase rdd-builder` 与 `"builder crashed"` **同阶段** |
| AC-4 诊断全 0 + 含已豁免变化 | **pass** | `stale`/`invalid`/`ignored_inline`/`fence_rejected`/`in_fence` 全 **0**；含已豁免 **319 / 170 / 44**（325−6 / 176−6 / 46−2）；已登记豁免 **283 不变** |
| AC-5 doctor 29 WARNING | **pass** | `doctor.sh --category v4-residue` ⇒ `0 CRITICAL · 29 WARNING · 1 INFO`（35−6） |
| AC-6 validate 逐字节相同 | **pass** | 3 份 × 4 组输出（`stdout`/`stderr`/`--strict` stdout/`--strict` stderr）+ exit code 与 T0 基线**逐字节相同**；`validate --all` 的 `out`/`err`/`rc` 也**逐字节相同** |
| AC-7 `--all` ERROR == 11 | **pass** | **11**（与基线一致） |
| AC-8 台账 + 形态台账 | **pass** | `.rddf/reviews/spec-residue-repoint-batch6-2026-11-21.md`（6 行 + 1 配套 + 两次收缩 + 诚实边界 + 口径表）；形态台账更新为「批 7 = 32 行（annotate 31 / rewrite 1）+ 专项 4 行」 |
| AC-9 census 幂等 + 常数同步 | **pass** | 两次生成 `diff` 为空；`unset` **36**；常数同步为 36/29/12 + 319/170/44 |
| AC-10 pytest + ruff | **pass** | `pytest` ⇒ **65 passed**；`ruff` ⇒ All checks passed |
| AC-11 全量门 | **pass** | `./test.sh --full --regression` → **GATE_RC=0** + `✅ ALL PASSED`；bats **229/229、未评估 0、新增失败 0**；`--gates` ALL PASSED |

## 实施期发现

**口径缺陷（已修正并写进常数测试 docstring）**：我初稿把 AC-4 写成「含已豁免 325/176/46 **不变**」——
那是**标注**的口径。本批是**改指**，token 真的消失 ⇒ 含已豁免也减少（−6 处 / −6 块 / −2 份）。

三种处置对两个口径的影响：

| 处置 | 未豁免 | 含已豁免 |
|---|---|---|
| 标注（`allow`） | −N | **不变**（token 还在，只是被标记） |
| 改指（换 token） | −N | **−N**（token 真的消失） |
| 纯清理（删行） | −N | −N |

⇒ 已写进 `test_r4_repo_residue_constant` 的 docstring，避免下次再混。

**诚实边界**：`post-flow-analysis:10` 改后**仍不可验证** —— 其 GIVEN「SKILL.md Phase Exit 段指示
agent 调 `rddf report-issue`」在 v4 无对应物（`skills/rdd-builder/SKILL.md` 全文无 report-issue /
Phase Exit 段）。本批只做 token 处置，**不声称**恢复了该 Scenario 的可验证性。

## 遗留清扫

- 本次范围内（T3.10）：无 TODO / 半截改写；7 行改动全部落盘且逐行有落点证据。
- **未处置的 36 行**（范围外，已明确移交）：批 7 = 32 行（`annotate` 31 / `rewrite` 1）+ `general` 专项 4 行。
- **范围外历史遗留（只记录）**：`spec_residue_scan.py:488` 的 `hit_lines` 死变量（改前就存在）。

## 失败项与路由建议

**本次验收无失败项** —— AC-1 ~ AC-11 全部 pass，全量门 `GATE_RC=0`。

## 已用轮次

- **critic 评审**：2 轮（REJECT → APPROVE）—— **已用满上限**；后续不再对该 change 调 critic。
- **验收轮次**：1 轮
