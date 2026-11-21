# 验收报告 — annotate-spec-residue-dead-blocks-batch7b1

- **change**：`openspec/changes/annotate-spec-residue-dead-blocks-batch7b1/`
- **定位**：`fix-spec-residue-guard` 的 Phase 1 **第七批（7b-1）** —— 机制已死的 Requirement 补
  **围栏式** `RETIRED` 注记 + `allow=history` 标注，**零原文改动**。
- **范围**：**9 行 / 6 份 / 7 个 Requirement / 7 条注记**。
- **验收时间**：2026-11-21
- **实现提交**：本提交
- **判据来源**：`proposal.md` 的 `## Acceptance`（AC-1 ~ AC-9）

## 审查链

| 环节 | 结论 | 处置 |
|---|---|---|
| critic 第 1 轮 | **APPROVE_WITH_CONDITIONS**（0 BLOCKER + 3 SHOULD_FIX + 4 NITS）；`mergeable: yes` / `scope_exceeded: false` | **7 条「已死」判定全部独立复核成立**（critic 未采信我的证据，逐条重跑全仓 grep）；`plan-done-quality-gate` 的**反转成立**（独立证据：全仓 `verify_transition` 37 命中 = 测试 + 文档 + 定义 + `get_suggestion()`，无生产调用方；旁证 `.rddf/improvements/wire-plan-done-quality-gates.md:15` 自身写明该执行路径「可能未调用」）。**SF-1**（`roadmap-hierarchy`「唯一调用方」**事实错误**：`roadmap_validate_fragments.sh:35` 也是活调用方，且同 spec 有「双入口校验」Requirement）→ 已改为「两个入口 + plan-done 无调用方」。**SF-2**（`plan-done`「`:521` 自测」**事实错误**：`:519-522` 是 `get_suggestion()`）→ 已改。**SF-3**（预检只覆盖 1/7 点 + 标注行在围栏外仍计入长度）→ 已扩到 **7 点全过**（含长度预算，最大 465 ≤ 500）。**NIT-1~4** 全部处置。 |

## 逐条判定与证据

| AC | 判定 | 证据 |
|---|---|---|
| AC-1 7 个 Requirement 未豁免 = 0；全仓 16/11/5 | **pass** | `scan_specs` ⇒ **16 处 / 11 块 / 5 份**（与实测预测一致） |
| AC-2 每命中行 1 标注 + 每 Requirement 1 注记；注记不含退役名 | **pass** | 精确比对（after − before）：新增标注 9（应 9）、注记 7（应 7）、围栏 7 对；退役名自检 **7/7 通过** |
| AC-3 零原文改动 | **pass** | `after == before + 按 HITS 插入的行` ⇒ 6 份**逐行相同**（257+4 / 402+4 / 80+5 / 184+4 / 177+4 / 86+9） |
| AC-4 诊断全 0；含已豁免不变；豁免 303 | **pass** | `stale`/`invalid`/`in_fence`/`fence_rejected` 全 **0**；含已豁免 **319/170/44**（不变）；豁免 **303** |
| AC-5 validate issue 多重集不变 + very long 不变 + ERROR 11 | **pass** | `--json` 比对：改前 **224** 条 / 改后 **224** 条，**新增 0 / 消失 0**；`very long` **62 → 62**；`validate --all` ERROR = **11** |
| AC-6 新守卫保持绿 | **pass** | `test_spec_requirement_length.py` 绿（`FROZEN_VERY_LONG` 62 / `FROZEN_INJECTED_VL` 25 均不变） |
| AC-7 台账 + 形态台账 | **pass** | `.rddf/reviews/spec-residue-annotate-batch7b1-2026-11-21.md`（9 行 / 7 Requirement + 7 条注记全文 + 全点位预检表 + 拆分理由）；形态台账更新（7b-1 完成 / 7b-2 待办 12 行 rewrite） |
| AC-8 pytest + ruff + census | **pass** | 3 个测试文件 **67 passed**；`ruff` 全绿；census 幂等（`unset` **16** / 豁免 **303**）；常数同步 **16/11/5 + 319/170/44** |
| AC-9 全量门 | **pass** | `./test.sh --full --regression` ⇒ **GATE_RC=0** + 未评估 0 + 新增失败 0 |

## 实施期发现

**1. 批 7b 的形态台账几乎全错（本批最重要的发现）**：逐行全仓复核后 —— 原判
`annotate` 14 / 改指 6 / rewrite 1，实际 **rewrite 12 / 注记 9 / 改指 0**。
**「改指」归零**：没有一行满足批 6 的「纯 token 替换 + 行为等价」。

**2. `plan-done-quality-gate` 的判定被反转（推翻上一轮 critic 的结论）**：
上一轮 critic 判「已注册未接线 ⇒ 改指」；本轮核实 `GateMechanism.verify_transition`（`_lib/gate.py:441`）
**无生产调用方**（`get_suggestion()` 亦只在测试中被调）⇒ plan_done 门整体无执行路径 ⇒ 该
Requirement 描述的机制**不存在** ⇒ 注记。**本轮 critic 独立复核确认反转成立。**

**3. 围栏形态的「零代价」是真的，但有前提**：围栏内的注记不计入 Requirement 正文（`very long` 62→62）；
但**标注行在围栏外**（必须紧跟命中行）⇒ 仍计入长度（~35 字符）⇒ 必须预检。
实测 7 个目标 Requirement 加标注后最大 **465** ≤ 500 ⇒ 全部安全。

**4. 预检首轮红过（`fence_rejected=1`）**：逐次 `insert` 导致**行号漂移**
（`skeleton-planning` 3 点 / `plan-done` 2 点插错）⇒ 改成**单趟重建**后 7/7 全过。
⇒ 印证 tasks T1.7 的纪律。

**5. critic 抓到两处我的事实错误**（`roadmap-hierarchy` 的「唯一调用方」、`plan-done` 的「`:521` 自测」）
⇒ 这是连续第 **五** 轮在「存在/不存在/调用方」类断言上栽跟头。
已落盘到台账 §5 与形态台账的复核纪律段。

## 遗留清扫

- 本次范围内：无 TODO / 半截改写 / 未处置行；9 标注 + 7 注记全部落盘，零原文改动可机判。
- **未处置项**（范围外，已明确移交）：批 7b-2 的 rewrite 12 行 / 4 份 · `general/spec.md` 4 行 ·
  既有 62 条 `very long`（冻结）· delta 形态垃圾结构。

## 失败项与路由建议

**本次验收无失败项** —— AC-1 ~ AC-9 全部 pass，全量门 `GATE_RC=0`。

## 已用轮次

- **critic 评审**：**1 轮**（APPROVE_WITH_CONDITIONS，0 BLOCKER ⇒ 无需复审）
- **验收轮次**：1 轮
