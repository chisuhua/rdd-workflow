# spec 残留处置台账 — Phase 1 第七批（7b-1，2026-11-21）

> 定位：change `annotate-spec-residue-dead-blocks-batch7b1`。
> **机制已死**的 Requirement ⇒ **围栏式** `RETIRED` 注记 + `allow=history` 标注，**零原文改动**。
> **9 行 / 6 份 / 7 个 Requirement / 7 条注记**。
> `line` 列是**改前**行号。

## 1. 逐行处置

| file | line | requirement | disposition | code | 证据 |
|---|---|---|---|---|---|
| `openspec/specs/skeleton-planning/spec.md` | 43 | skeleton-minimal-artifacts | ANNOTATE（注记 ①） | `history` | `list_ready_for_fill`（`_lib/iteration/store.py:446`）只有定义 + 导出 + 单测，**无生产调用方**；`skills/rdd-builder/scripts/phase1_plan.sh` 对 `planned`/`skeleton` **零命中** |
| 同上 | 47 | 同上（Scenario） | ANNOTATE | `history` | 同上（同一 Requirement 共用注记 ①） |
| 同上 | 83 | proposal-suggestions-skeleton-status | ANNOTATE（注记 ②） | `history` | `planned` → `proposed` 在 v4 由 **P0 approval** 完成（`skills/rdd-builder/scripts/phase0_approval.sh:252` 调 `store.set_status(data, name, "proposed")`）；P1 脚本对 `planned`/`skeleton` 零命中；legacy propose 流仍有「待创建 → skeleton」（`skills/propose/SKILL.md:515`）但**无 fill 完成触发器** |
| `openspec/specs/plan-done-quality-gate/spec.md` | 8 | run_plan_checks 在 plan_done_gate 正常执行路径中被调用 | ANNOTATE（注记 ③） | `history` | `run_plan_checks`（`skills/propose/scripts/propose_quality_check.py:234`）只是 `run_all_checks` 的别名且**无生产调用方**（仅测试）；plan_done 门注册表（`_lib/gate.py:378-394`）虽含 `propose_quality_checks`，但 `GateMechanism.verify_transition`（`:441`）**无生产调用方**（`get_suggestion()`（`:519`）亦只在测试中被调） |
| 同上 | 12 | 同上（Scenario） | ANNOTATE | `history` | 同上（共用注记 ③） |
| `openspec/specs/cross-repo-deps/spec.md` | 126 | Hub dependency issue creation | ANNOTATE（注记 ④，**PARTIAL**） | `history` | `rddf hub` 只注册 retry-failed（`_lib/cli/__init__.py:94`）⇒ `rddf hub issue --deps` 不存在；`create_hub_issue`（`_lib/hub_issue.py:17`）**无生产调用方**。⚠️ **WHEN 侧（强依赖 + `STRICT_DEPS_GATE`）仍为真** ⇒ 注记明确区分 |
| `openspec/specs/cross-repo-federation/spec.md` | 119 | Design Gate Integration | ANNOTATE（注记 ⑤） | `history` | pending 状态只被 `skills/report-issue/scripts/report_issue_rfc.py:124`（写）与 `skills/watch-hub/scripts/watch_hub.py:24`（读）使用，**无任何设计门读它并阻断** |
| `openspec/specs/roadmap-hierarchy/spec.md` | 149 | plan-done gate 集成 fragment 校验 | ANNOTATE（注记 ⑥） | `history` | `validate_fragment_refs`（`_lib/roadmap_validate.py:82`）现由**两个入口**调用（`skills/roadmap/scripts/roadmap_validate_fragments.sh:35` + `skills/rdd-doctor/scripts/checks/roadmap_refs_check.py:41`，见同 spec 的「双入口校验」Requirement）；**plan-done 路径无调用方** |
| `openspec/specs/roadmap-proposal-guidance/spec.md` | 148 | rdd-doctor 不感知主题覆盖率字段 | ANNOTATE（注记 ⑦，**PARTIAL**） | `history` | **后半**（coverage 显示仅在已退役的 preflight）已不成立；**前半仍为真**（`skills/rdd-doctor/scripts/checks/roadmap_feature_check.py:38` 校验的是 feature fragment frontmatter 的 `主题`，不是 proposal 的 `**主题**:`） |

**合计 9 行 / 6 份 / 7 个 Requirement**（`allow=history` × 9，围栏注记 × 7）。

## 2. 处置形态：**围栏式**（本批确立，相对批 7a 的引用块形态代价为零）

```
<命中行>
<!-- v4-residue:allow=history -->
```text
> **已退役（2026-11-21）**：<该 Requirement 专属的退役说明 + 依据>
```
```

**为什么是围栏**：openspec 的 `extractRequirementBody`（`dist/core/parsers/requirement-text.js:62-84`）
**跳过 fenced code block 内的行** ⇒ 围栏内的注记**不计入 Requirement 正文长度** ⇒ **不产生 `very long`**。
而 HTML 注释 / 引用块**都会被计入**（它们是正文行）⇒ 只有围栏能做到「零代价」。

**标注行在围栏外**（必须紧跟命中行）⇒ 它**仍计入**长度（~35 字符）⇒ 必须预检是否会跨 500。

### 全点位预检（7/7 全过，`b7b1_pretest_all.py`）

| 插入点 | 目标 Requirement 正文长度 | + 标注 | 结果 |
|---|---|---|---|
| `skeleton-planning` 块 43（2 标注） | 395 | +70 → **465** | ≤ 500 ✓ |
| `skeleton-planning` 块 83（1 标注） | 256 | +35 → 291 | ✓ |
| `plan-done-quality-gate` 块 8（2 标注） | 285 | +70 → 355 | ✓ |
| `cross-repo-deps` 块 126 | 101 | +35 → 136 | ✓ |
| `cross-repo-federation` 块 119 | 95 | +35 → 130 | ✓ |
| `roadmap-hierarchy` 块 149 | 85 | +35 → 120 | ✓ |
| `roadmap-proposal-guidance` 块 148 | 122 | +35 → 157 | ✓ |

7 点逐点试插：豁免 −9 正确、`stale`/`invalid`/`in_fence`/`fence_rejected` 全 **0**、
`very long` **全部 +0**（62 → 62）。

⚠️ **预检首轮红过**：逐次 `insert` 导致**行号漂移**（`skeleton-planning` 3 点 / `plan-done` 2 点插错
⇒ `fence_rejected=1`）⇒ 改成**单趟重建**（按原始行号 emit）后 7/7 全过。**这正是 tasks T1.7 的纪律**。

## 3. 批 7b 的拆分与「逐行复核推翻原分类」

批 7b 原计划 21 行。**逐行全仓复核后分类几乎全错**：

| | 台账原判（按句子形态猜测） | 逐行全仓核实后 |
|---|---|---|
| rewrite | 1 行 | **12 行** |
| 改指 | 6 行 | **0 行** |
| 注记 | 14 行 | **9 行** |

**「改指」归零** —— 没有一行满足批 6 的「纯 token 替换 + 行为等价」：

- `plan-done-quality-gate`：`run_plan_checks` **无生产调用方** + `verify_transition` **无生产调用方**
  ⇒ plan_done 门整体是死代码 ⇒ **已死**（不是「已注册未接线 ⇒ 改指」—— 上一轮 critic 的判断已被本轮推翻）
- `spec-validation-gates`：actor 换成 CI 成立，但「before writing `.plan-handoff.json`」在 v4 **已无 writer**
  ⇒ 纯改指会保留一句假判据 ⇒ 须 **rewrite**
- `skeleton-planning`：`planned → fill` 在 v4 **无活实现**（`list_ready_for_fill` 无生产调用方、
  `phase1_plan.sh` 零命中、`wave_scheduler` 无活调用方）⇒ **已死**
- `state-management`：`planned → proposed` 由 **P0 approval** 完成（`phase0_approval.sh:252`）⇒ rewrite
- `rfc-rddf`：`git.openspec_tracked` 已**不影响**执行模式（`builder_deps.py:42` 只吃 file/task/risk）
  ⇒ 判据被**反证** ⇒ rewrite

⇒ 拆成 **7b-1（本批：注记 9 行）** + **7b-2（rewrite 12 行 / 4 份）**。
**拆分理由**：rewrite 必然改原文 ⇒ 与「零原文改动」判据混批会让后者失效（批 7a 的先例）。

## 4. 实测数字

| 指标 | 改前 | 改后 |
|---|---|---|
| 未豁免 | 25 处 / 20 块 / 10 份 | **16 处 / 11 块 / 5 份** |
| 含已豁免 | 319 / 170 / 44 | **319 / 170 / 44（不变）** |
| 已登记豁免 | 294 | **303** |
| `stale` / `invalid` / `in_fence` / `fence_rejected` | 0 / 0 / 0 / 0 | **0 / 0 / 0 / 0** |
| `very long`（openspec `--json`） | 62 条 / 38 spec | **62 条 / 38 spec（不变）** |
| `openspec validate --all --json` 的 issue 多重集 | 224 条 | **224 条（新增 0 / 消失 0）** |
| `validate --all` ERROR | 11 | **11** |
| `doctor --category v4-residue` | 20 WARNING | **11 WARNING** |
| **零原文改动** | — | ✅ 6 份的原有行逐行相同（after == before + 按 HITS 插入的行） |

## 5. 审查链

| 环节 | 结论 | 处置 |
|---|---|---|
| critic 第 1 轮 | **APPROVE_WITH_CONDITIONS**（0 BLOCKER + 3 SHOULD_FIX + 4 NITS）；`mergeable: yes` | 7 条「已死」判定全部独立复核成立；`plan-done-quality-gate` 的**反转成立**。**SF-1**（`roadmap-hierarchy`「唯一调用方」事实错误）→ 已改为「两个入口 + plan-done 无调用方」；**SF-2**（`plan-done`「`:521` 自测」事实错误）→ 已改为 `get_suggestion()`（`:519`）；**SF-3**（预检只覆盖 1/7）→ 已扩到 7 点全过；**NIT-1~4** 全部处置。 |

⚠️ critic 的**未能独立复核**项（openspec fence 跳过行为 / 预检实测 / doctor WARNING 口径）
⇒ 已由本方实测兜底（`very long` 62→62、预检 7/7、WARNING 20→11）。

## 6. 记 tail（范围外）

1. **7b-2：rewrite 12 行 / 4 份** —— `skeleton-planning` 的 `planned-status-lifecycle`（3 行）、
   `spec-validation-gates`（4 行）、`state-management`（2 行）、`rfc-rddf-project-yaml-config-i10`（3 行）。
   ⚠️ 重写已采纳契约的判据正文 + Scenario ⇒ critic 须重点审「改写后判据是否仍为真且可验证」。
2. **`general/spec.md`（4 行 / 2 块）** —— 测试锁定 + 断言漂移，三方联动专项。
3. **既有 62 条 `very long`** —— 接受并冻结（`fix-spec-very-long-verification-gap` 的守卫阻止新增）。
4. delta 形态垃圾结构 / 围栏示例与 schema 脱节 —— 各自专项。

## 7. 回滚

- 台账 / 测试：`git revert <sha>`（tracked）。
- spec 改动：`openspec/` gitignored ⇒ 回滚凭据 = `/tmp/opencode/specs-b7b1-before/`（6 份改前快照）
  + `/tmp/opencode/specs-backup-b7b1-<ts>/`（165 份整树）。
