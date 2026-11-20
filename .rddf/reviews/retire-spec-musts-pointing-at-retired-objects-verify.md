# 验收报告 — retire-spec-musts-pointing-at-retired-objects

- **change**：`openspec/changes/retire-spec-musts-pointing-at-retired-objects/`
- **定位**：`.rddf/improvements/fix-spec-residue-guard.md`（draft, P2）的 **Phase 1 —— 逐 spec 清理**（第一批 13 / 48 份）
- **验收时间**：2026-11-20
- **实现提交**：本提交（唯一可入库交付物 = 处置台账 + 本验收报告；`openspec/specs/**` 的改动因 `.gitignore:45` 不产生 git diff）
- **判据来源**：`proposal.md` 的 `## Acceptance`（AC-1 ~ AC-9）

## 审查链

| 环节 | 结论 | 关键处置 |
|---|---|---|
| critic 第 1 轮 | **REJECT（1 BLOCKER）** | BLOCKER：`project-setup-check:91,93` 改指 `rddf guide` 是假契约（`guide_cmd.py` / `recommender.py` 对 `check_project_setup` / `safe_auto_fix` 0 命中） |
| 修复 | 判定翻转为 **RETIRED** + 能力缺口说明 | 另采纳 4 条 SHOULD_FIX（改指须行为等价+行号证据 / RETIRED 保留 Scenario / 与 `fix-spec-residue-guard` 协调+台账写 tracked / 回滚加固） |
| critic 第 2 轮（复审） | **APPROVE**，mergeable: yes | BLOCKER 闭合经独立复核；**上一轮「本 change 必须交付守卫」的建议被 critic 主动撤回**（守卫归 `fix-spec-residue-guard`） |

## 逐条判定与证据

| AC | 判定 | 证据 |
|---|---|---|
| AC-1 裸漂移为 0 | **pass** | `/tmp/opencode/verify_bare_drift.py` → **`TOTAL bare drift: 0`**（判据：每处命中要么落在已标 `RETIRED (2026-11-20, …)` 的 Requirement 内，要么本身是改指加注 / blockquote） |
| AC-2 RETIRED 标注 + Scenario 保留 | **pass** | 2 份整 spec RETIRED 逐个 Requirement 插注（`three-phase-skills` 4 个 + `workflow-design-phase` 7 个）；其余 RETIRED 7 处同样插注。**所有 Scenario 未删**（脚本只插注不改原文） |
| AC-3 改指附行号级证据 | **pass** | `arch_env_check.sh` 存在且 `:139-141` source helper / `:150-154` 调 `check_project_setup` / 逐条打印 + `return 1`；`rdd-arch/SKILL.md`、`propose_change.py`、`_lib/cli/guide_cmd.py` 均 `test -f` 通过 |
| AC-4 13 份 validate + strict 不增 | **pass** | 13/13：`openspec validate <cap>` 无 ERROR，`--strict` 的 `MUST include at least one Scenario` issue 数与改前**同为 1**（基线即如此，已实测） |
| AC-5 `general` + 守卫型未动 | **pass** | `diff -r` 对 `general` / `v4-residue-contract` / `docs-v4-sync-scope-followup` 全部为空 |
| AC-6 改动文件 == 计划 13 份 | **pass** | 逐份 `diff -q` 与 T0 快照比对 → changed = **13**（无第 14 份） |
| AC-7 台账 34 行 | **pass** | `.rddf/audits/spec-residue-census-2026-11-20.md` → **34 行**（REPOINT 11 / RETIRED 22 / PARTIAL 1），无 `unset` |
| AC-8 无源码改动 | **pass** | 提交前 `git status --porcelain` 只有 `?? .rddf/audits/`；提交后为空 |
| AC-9 `test_doc_contracts.py` 绿 | **pass** | `13 passed in 0.42s` |

## 实施中修正的判定（重要）

**原 proposal 的判定表有 4 处错误，实施时纠正**：

`workflow-design-phase` 被我初判为「逐 Requirement 改指 / 部分退役」，实施时实查发现**整 spec 应 RETIRED**：
- spec 声称 `guide-design` SHALL expose **exactly 5 phases: setup / intake / review / gate / exit**；而 v4 `rdd-planner` 是 **Phase 0 roadmap-bootstrap + Phase 1-5**（6 个，且 phase 名不同）⇒ 改指会声称一个不存在的结构；
- `rdd-builder` 对 `design-handoff` / `design_done` **grep 0 命中** ⇒ `plan Phase Design-done Gate` 的承接者不是它；
- `Dual-Scanner` 的 bash 侧已随 ADR-0062 退役 ⇒ 「两扫描器一致」无从落地。

⇒ 这正是 critic 第 1 轮 BLOCKER 教训的直接应用：**「仅路径存在」不构成改指理由，必须验行为等价**。

## 遗留清扫

- 本次范围内（T4.8）：无 TODO / FIXME / 半截改写；台账无 `unset`。
- **范围外（记 tail，已在 proposal 的 Out of Scope 登记）**：
  - **守卫**（`v4_residue_check` 扫 `openspec/specs/`）—— 归 `fix-spec-residue-guard`
  - **其余 35 份含漂移的 spec** —— 本批只做 13 份；台账头部记了「剩余 5 份（守卫型 2 + 已退役 2 + 已标 NOTE 1）不动」，另 35 份属更早批次的未处置残留，需后续批次
  - 改任何 Requirement 标题（触发 RENAMED 语义，`validate_delta_targets.py:159`）

## 失败项与路由建议

无。`implementation_gap` / `proposal_drift` 均不适用。
