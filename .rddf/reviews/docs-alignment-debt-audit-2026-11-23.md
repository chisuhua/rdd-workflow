# 文档 / 决策 / 代码 / 技能对齐审查 —— 债务台账（2026-11-23）

> 触发：用户要求「对架构文档、决策文档、代码、技能再做一次对齐和债务梳理，并检查是否对齐
> `~/.config/opencode` 下的多智能体、以及 build 智能体的多角色是否对齐」。
> 方法：两路只读调查（`explore` × 2）+ 主会话复核；所有结论都带 `file:line`。

## 一、已对齐的部分（无需动作）

| 维度 | 结论 | 证据 |
|---|---|---|
| skill 数 | **26 对齐** | `pytest tests/unit/test_docs_consistency.py` **16 passed**；`_lib/docs_consistency.py:58` 三方比对（package.json / INSTALL.md / disk `*/SKILL.md`） |
| 架构文档索引 | **18 份对齐** | `docs/architecture/README.md:11-29` Doc Map 17 链接 ↔ 17 非 README 文件，一一对应 |
| ADR 索引 | **63 份对齐** | `test_docs_consistency.py::test_adr_list_completeness` 守卫存在且绿 |
| 跨仓关系描述 | **正确** | `docs/architecture/agent-role-alignment.md:36-38`「rdd-workflow **不依赖** opencode」；6 处 opencode 指针全写成 `~/.config/opencode/...` 绝对路径（`:18,19,21,49,130,150`） |
| `~/.config/opencode` 自身守卫 | **125 pass / 0 fail** | `bun test tests/config-guards.test.ts` |
| 两套角色体系的解耦 | **正确** | 治理角色（`architect/planner/builder/verifier/general/no-role`）vs 阶段技能（`rdd-arch/rdd-planner/rdd-builder/rdd-verifier/rdd-quick`）—— `agent-role-alignment.md:28-38` 明确声明「名字相似但语义不同，且互不依赖」 |

## 二、本仓漂移（P1 — 会误导人）

### 2.1 `docs/architecture/skills-and-handoff.md` 与 v4 代码严重脱节（**最严重**）

| # | 位置 | 文档说 | 实际 |
|---|---|---|---|
| 1 | `:87-101` | `.plan-handoff.json` 是 `rdd-builder` P1.5 **read** 的 `execution_mode_decisions` | `skills/rdd-builder/scripts/phase1_5_deps.sh:24` 明写 **"Legacy plan-handoff execution_mode (v3 residue). no writer in v4"**；`:115-120` 只作 LOWEST priority 兜底并打「已忽略」警告 |
| 2 | 全篇 | **0 次**提 `.planner-handoff.json` | v4 真正在用：写 `_lib/planner_handoff.py:43,77`，读 `_lib/builder_deps.py:223,234`（v1.2） |
| 3 | 全篇 | 未提 `.planner-state.json` / `.planner-feedback.json` / `.rddf/state/builder/<change>.json` | 三者都是 v4 在用的状态文件 |
| 4 | `:54` / `:109` | `.arch-handoff.json` **v1**（ADR-0016） | `skills/rdd-arch/scripts/write_arch_handoff.py:183` 写 **version: 3**；`_lib/schemas/arch_handoff_schema.json:133` `enum: [1,2,3]` |
| 5 | `:107-114` schema 表 | 列 6 个 | `_lib/schemas/` 实际 **34 个** json；漏 `planner_handoff_schema.json` / `planner_state_schema.json` / `builder_handoff_schema.json` / `rdd_quick_context_schema.json` |

**同目录自相矛盾**：`state-and-events.md:59` 已正确写「v1~v3 的 `.design-handoff.json` / `.plan-handoff.json` 已废弃」⇒ 两篇文档结论相反。

**arch-handoff 版本三处口径不一**：`skills-and-handoff.md:54,109`（v1）· `workflow-phases.md:79`（v2）· `rdd-arch-rdd-planner-integration.md:19,344`（v2）· 代码（v3）。

### 2.2 幽灵路径 + 数量陈数

| # | 位置 | 文档说 | 实际 |
|---|---|---|---|
| 6 | `hub-and-spoke-federation.md:72` | `skills/rdd-builder/scripts/approve_proposal.sh` | **文件不存在**（实际是 `phase0_approval.sh`；`workflow-phases.md:244` 引用的是对的） |
| 7 | `loop-engine.md:7` | 「16 modules: `loop_state`, `agents`, …, **`gate`**, …」 | **数量对**（`_lib/loop/` 实为 16 个 .py），但清单里的 **`gate` 不存在** —— gate 在顶层 `_lib/gate.py`；目录里的 `__init__.py` 未列入清单。逐名核对：其余 15 个全部存在 |

### 2.3 行号漂移

| # | 位置 | 文档引 | 实际 |
|---|---|---|---|
| 8 | `state-and-events.md:59` | `_lib/cli/guide_cmd.py:172-173` | 该文件**只有 90 行**；legacy 探测在 `guide_cmd.py:69` |
| 9 | `rddf-layout.md:84` | `.planner-handoff.json` 由 `rdd-planner` 写，据点是 `_lib/builder_deps.py:42` | `builder_deps.py:42` 是 `def decide_execution_mode(...)`；写方是 `planner_handoff.py:43/77`，`builder_deps.py:223/234` 是**读方** |
| 10 | `improvement-check-mechanisms.md:47` | `_lib/gate.py:341-370` 的 `review_debt_recorded` | 函数从 `gate.py:333` 开始；`:310`「`_lib/schemas/` 17 个文件」现为 **34** |

**文档间自相矛盾**：`workflow-phases.md:136` 说 hash 排除项在 `_lib/planner_handoff.py`，`v4-pipeline-data-flow.md:573` 说在 `_lib/planner_state.py`（后者对，实际是 `planner_state.py:56`）。

### 2.4 ADR 状态字段格式三分裂 + 4 份「待定」

- 三种写法并存：`> **状态**: 待定` / `> **状态**: 已采纳` / `> **Status**: 已采纳（2026-11-19，oracle + critic 双审…）`
- **停在「待定」**：`ADR-0014` · `ADR-0030` · `ADR-0032` · `ADR-0033` ⇒ doctor 每次报 4 条 WARNING

### 2.5 本轮已处置（2026-11-23，builder 权限内）

改动的文档共 **10 份**：`docs/architecture/**` 9 份 + `docs/strict-gate-boundary.md` 1 份（纯文档，零代码改动）。

| # | 处置 | 落点 |
|---|---|---|
| 1 | `.plan-handoff.json` 降级为「**v3 残留，v4 无写入方**」：补 `phase1_5_deps.sh:24` 的原文引用 + `:115-120` 的「已忽略」警告原文；不再声称它是 P1.5 的判定来源 | `skills-and-handoff.md` |
| 2 | 新增 `.planner-handoff.json`（`planner-handoff-v1`）段：写方 `_lib/planner_handoff.py:33,77` / 读方 `_lib/builder_deps.py:223,234`；标注 `recommended_route` 被 `_lib/planner_state.py:56` 排除在语义哈希外 | `skills-and-handoff.md` |
| 3 | 新增 `.planner-state.json`（v1）/ `.planner-feedback.json`（`planner-feedback-v1`）/ `.rddf/state/builder/<change>.json`（`builder-handoff-v1`）/ `.rddf/state/rdd-quick-context.json` 四段 | `skills-and-handoff.md` |
| 4 | arch-handoff 全文重写为 **v3**：JSON 示例改成 writer 的**实际输出形状**（`write_arch_handoff.py:164-187`），删掉不存在的 `schema` / `owner` / `roadmap_path` 字段；补 `discovered` 的**语义变更**（v1 布尔 → v2/v3 逐工件对象） | `skills-and-handoff.md` + `v4-pipeline-data-flow.md:158-172` |
| 5 | schema 表补 4 个（`planner_handoff` / `builder_handoff` / `planner_state` / `rdd_quick_context`），并修正 `iteration` 的版本（`enum: [3,4,5,6,7]`，原写 v1） | `skills-and-handoff.md` |
| 6 | arch-handoff 版本口径统一为 **v3**（原 v1 / v2 / v3 三处不一） | `skills-and-handoff.md` · `state-and-events.md:53` · `workflow-phases.md:79` · `rdd-arch-rdd-planner-integration.md:19,344` |
| 7 | 幽灵路径 `approve_proposal.sh` ⇒ 改标「**实现已移除**（v4 stage-merge / ADR-0043）」而非替换成 `phase0_approval.sh`（后者**不实现**该门禁 —— 见 #31）。⚠️ 措辞必须含豁免词「**已移除**」，否则触发 `doc_drift_v4` 守卫（见 §2.7） | `hub-and-spoke-federation.md:53,72` |
| 8 | `loop-engine.md:7` 清单去掉不存在的 `gate`，改注「16 = 15 功能模块 + `__init__.py`」并点明 gate 在顶层 `_lib/gate.py`；`:26` 的 Module 列同改 | `loop-engine.md` |
| 9 | 行号订正：`guide_cmd.py:172-173` → **`:68-73`**（该文件仅 90 行）；`builder_deps.py:42` → 写方 `planner_handoff.py:77` / 读方 `builder_deps.py:234`；`adr_catalog.py:127` → 真写方 `write_arch_handoff.py:194`（`adr_catalog.py:127` 是**读** `adr_regex` 的地方） | `state-and-events.md` · `rddf-layout.md` |
| 10 | `gate.py:341-370` → **活实现 `_lib/review_debt_checker.py:62`**（`gate.py:333` 的同名函数已标 `@deprecated`）；两条「已知局限」（语言范围窄 / gate 过松）在活实现里**已修复** ⇒ 标为已修复并给出依据 | `improvement-check-mechanisms.md` |
| 11 | 「`_lib/schemas/` 17 个文件」→ **34** | `improvement-check-mechanisms.md:322` |
| 12 | 文档自相矛盾统一为 `_lib/planner_state.py:56` | `workflow-phases.md:136` + `v4-pipeline-data-flow.md:573` |
| 13 | `rdd-arch-rdd-planner-integration.md` §8「消费者兼容」重写：列出真实消费者（`arch_quality_gate.py:87-88` / `gate.py:119-120` / `adr_catalog.py:133` / `recommender.py:178,248` / `detectors.py:184` / `actions.py:350`），删掉已不读 handoff 的 `planner_stage_entry.sh`；标注「v3 writer 不写 `roadmap_path` / `owner` / `schema` ⇒ 消费者必须走回落路径」 | `rdd-arch-rdd-planner-integration.md:342-354` |
| 14 | **v1（2026-08-15）的 `docs/strict-gate-boundary.md` 全面重写**：补「v4 实现状态」列，把 4 个死门 + 1 个仅文档门 + 2 个未接线的门标出；CI 示例只留**确实生效**的 6 个，并加「env var 必须在执行该门的那条路径上生效」的前提；新增「新增门流程」的第 5 步「验证触发链」 | `docs/strict-gate-boundary.md`（v1 → v2） |

**验证**：10 份文档的相对链接 + 锚点全部可解析（自写校验脚本）· `pytest tests/unit/test_docs_consistency.py` **16 passed** · `doctor --category docs-consistency` **OK** · 引用的 18 个文件 × 30 处行号**逐条核对内容**（不是只查存在）· `pytest tests/unit/` **3537 passed / 3 skipped** · `./test.sh --gates` **5 道门全绿** · `bats tests/integration/test_v4_doc_drift_contracts.bats` **20 例全绿** · `./test.sh --full --regression` **GATE_RC=0**（未评估 0 · 已知失败 10 = 基线 · **新增失败 0**）。

### 2.6 审查链

| 轮 | 结论 | 处置 |
|---|---|---|
| 1 | **REJECT**（1 个 arch BLOCKER + 2 SHOULD_FIX + 2 NIT）；`mergeable: no` / `scope_exceeded: false` | 全部处置，见下 |
| 2（复审） | **APPROVE**；`mergeable: yes` / `scope_exceeded: false` | **BLOCKER 判定 CLOSED**；**无新增 BLOCKER**；仅 1 NIT（台账 §2.5 #7 的措辞与落稿字面不一致）⇒ 已改 |

> 复审范围按规矩限定为「上一轮 BLOCKER 是否闭合」+「本轮新增 diff 是否引入新 BLOCKER」，
> **未重审**第 1 轮已确认的 focus A/B/C 结论。
> 复审对「守卫豁免」的判定：**正确使用豁免，不是绕过** —— 判据两条都满足
> （①「已移除」是事实；②两行都带 ⚠️ 并明说「没有这道门」，读者不会误以为该 skill 仍可用）。

#### 第 1 轮处置

| # | finding | 处置 |
|---|---|---|
| **BLOCKER** | `skills-and-handoff.md` **残留旧的 `.design-handoff.json` / `.plan-handoff.json` 两节**（本轮只插新未删旧）⇒ 同一文档对 `execution_mode_decisions` 给出两个相反答案（旧节说是 P1.5 的判定来源，新节说只打警告永不覆盖）—— arch BLOCKER 第 3 类「文档内自相矛盾」 | **删除残留旧节**（`:194-225`）⇒ 现每节唯一 |
| **SF-1** | 台账 #31 称 `docs/strict-gate-boundary.md`「仍按『已实施』描述（本轮未改）」，但同一份 diff 已把该文件重写为 v2 ⇒ 同批交付物内部互相矛盾 | 改为「本轮已重写为 v2，`:32` / `:61` 均标 ❌ 无代码」 |
| **SF-2** | 「`GateMechanism` 全仓只有定义处一个命中」措辞过强（测试与历史文档亦有命中） | 改为「**生产代码零命中**」 |
| **NIT-1** | `cleanup_context.sh:49` 指到的是变量定义，实际 `rm -f` 在 `:58` | 改为 `:58`（路径定义 `:49`） |
| **NIT-2** | 「门禁待重实现」偏向 #31 的选项 A | 改为「**待裁决：重实现 / 退役**」 |

#### 第 1 轮 focus 结论（critic 独立复核）

- **A（6 处「无实现 / 未接线 / 已移除」断言）**：**全部成立**。critic 独立重跑 grep，并额外查了动态引用面
  （`.sh` 里的 `python -c "from ... import ..."` / `getattr` / `importlib` / 字符串拼接）——
  `GateMechanism` / `verify_transition` 在生产路径零调用；`STRICT_*` 4 个死门 grep 无 include 过滤仍零命中；
  `cross_repo_audit.py` 只有 identity-merge shim + 测试引用。
- **B（是否引入新的自相矛盾 / 新错误）**：BLOCKER 之外全部通过 ——
  arch-handoff JSON 示例与 `write_arch_handoff.py:162-184` **逐字段一致**；
  4 份文档的 arch-handoff 版本口径统一 v3；抽查 ~20 处 `file:line` 引用**全部指对**；
  计数（schemas 34 / debt improvements 7 / `_lib/loop/` 16 = 15+`__init__`）全对；
  与 `openspec/specs/**` 的既有 RETIRED 注记**同向**，无新冲突。
- **C（未决写成已决）**：**基本无**。#31 / #33 均如实标「需用户裁决」、两条路径并列；
  CI 示例删掉两个未接线的门属「如实标注当前状态」，不越权。
  critic 指出 ADR-0031 正文自身需要修订（Verification 里的 `[x]` 现可被证伪）⇒ 记入 #31 的后续 backlog，不阻断本轮。

### 2.7 全量回归门抓到的 2 处新增失败（同一根因，已修）

`./test.sh --full --regression` 两次各报 **新增失败 1**：
`doc_drift_v4: ALL docs/architecture/*.md have no live guide-* skill references (AC-3 follow-up)`
（`tests/integration/test_v4_doc_drift_contracts.bats:272`）

**根因**：该守卫的匹配式含 `skills/(guide-arch|guide-design|guide-plan|guide-ship|guide-spec)/`，
豁免词表是 `shim|DEPRECATED|deprecated|compat|**已移除**|已废弃|retired|hard removal|removed`
—— 我写的「随 v4 stage-merge **移除**」不含**「已移除」**，故未命中豁免。

**两处触发点**（同一根因，第二处是修完第一处后又引入的）：

| # | 位置 | 修法 |
|---|---|---|
| 1 | `hub-and-spoke-federation.md:53,72` | 改为「该脚本**已移除**（v4 stage-merge / ADR-0043）」/「**实现已移除**」 |
| 2 | `improvement-check-mechanisms.md:293`（G1「测试盲区」段引用 `skills/guide-ship/`） | 改为「依赖已移除的 `skills/guide-ship/`（该 skill 目录在 v4 已移除）」 |

⇒ `test_v4_doc_drift_contracts.bats` **20 例全绿**。

> ⚠️ **教训**：改架构文档时，「提到已退役的 skill 路径」本身就被守卫管着 ——
> 措辞必须命中豁免词表（`已移除` / `已废弃` / `removed`），不能只写「移除」/「被删」。
> 这条约束**不在**文档里，只能靠跑全量门发现 ⇒ 涉及 `docs/architecture/**` 的改动，
> **先跑 `bats tests/integration/test_v4_doc_drift_contracts.bats` 再跑全量门**。

## 三、跨仓漂移（`~/.config/opencode`，P1/P2）

> ⚠️ **本节所有路径均相对 `~/.config/opencode/`**（治理面仓，**不是**本仓）——
> 例：`docs/MULTI-AGENT-DESIGN.md` = `~/.config/opencode/docs/MULTI-AGENT-DESIGN.md`。
>
> ⚠️ 这些文件属**治理面**（`prompts/**`、`docs/MULTI-AGENT-DESIGN.md`）⇒ 按 `prompts/build.md`
> 的「治理面作用域」表，**builder 不得直接编辑**，须切 `architect` + oracle→critic 双审。
> 本台账只记录 findings。

### 3.1 `docs/MULTI-AGENT-DESIGN.md` 计数滞后（全部逃逸 `config-guards.test.ts`）

| # | 位置 | 文档说 | 实际 |
|---|---|---|---|
| 11 | `:61` | 「Agent 体系（**11 个**）」 | 配置 **12 个**（漏 `plan-worker`）；同文件 `§2.1` 表（`:65-78`）自己列了 12 行 |
| 12 | `:153` | 「Subagents（**7 个**）」 | 卡片 **9 张** / `mode:subagent` **8 个**（7 是 `plan-worker` 加入前的旧数） |
| 13 | `:382` | agent 枚举 11 项 | 漏 `plan-worker` |
| 14 | `:49` | 「本地 provider 池（**3 个** provider、**12 个** model）」 | **5 provider / 13 model**（同文件 `§5.1` 表 `:925-931` 自己已列 7 行且各项吻合） |
| 15 | `§3.1 委派矩阵`（`:630-641`） | 表头 10 列 | **无 `plan-worker` 列**（而 `tests/config-guards.test.ts:4359` 认定它可被 `{build,plan}` 派发） |

> `docs/SUBAGENT-ORCHESTRATION.md:15-28` 的清单表 **12 行、逐个与配置一致**（含模型列）⇒ **此文档无缺失**，是 MAD 落后于它。

### 3.2 `build.md` 角色矩阵 vs `lib/role-policy.ts`（六角色）

| 角色 | build.md 允许列 | `ROLE_WRITE_POLICY` | 判定 |
|---|---|---|---|
| architect | arch-docs.json + archPaths + 治理面 | 同上 **+ `.rddf/reviews`** | ⚠️ **表内漏 `.rddf/reviews`**（`:638` 后端作用域表有，`:454` 没有） |
| planner | 5 项 | 同 5 项 | ✅ |
| builder | 全部 | `["**"]` + `governance: true` | ⚠️ 见下 |
| verifier | 「写验收报告到 `.rddf/reviews/`」 | `.rddf/reviews` **+ `.rddf/state/verifier`** | ⚠️ **表内漏 `.rddf/state/verifier`**（`:374`/`:439` 有说明，`:457` 没有）；且缺「机器层无强制」标注 |
| no-role | 一切 edit 禁 | `allow: []` + `denyAll: true` | ✅ |
| general | 全部 | `["**"]` + `governance: true` | ✅ |

**builder 那条经复核：不是逻辑冲突，是表述缺口。**
`:553`「`~/.config/opencode/**` 不在 builder 的产出归属内」是**流程归属**；policy 的 `governance: true` 是**机器权限**（builder 的 `**` 本就覆盖全仓，不给 `governance: true` 反而会把 builder 挡在治理面外）。`build.md` 角色表上方的「约束性质」段已声明「② 其余面仍是软约束」，逻辑自洽 —— 但 `:553` 缺一句「机器层放行、流程层须走 architect」的标注（对比 `:456` 的 ADR 决策行**有**此标注）。

### 3.3 悬空引用

| # | 位置 | 问题 |
|---|---|---|
| 16 | `build.md:411`「见 §4.2 裁决」· `:455`「同 §4.4 builder 行」 | `build.md` 全文 **35 个标题无任何 `§4.x` 编号节**（只有中文标题）；MAD 的 §4.2/§4.4 语义也不匹配 ⇒ 旧版编号残留 |
| 17 | `docs/SUBAGENT-ORCHESTRATION.md:30` | 称 MAD 有「**链路分档**」节 —— 全文件 grep **零命中** |
| 18 | `docs/SUBAGENT-ORCHESTRATION.md:172` | 「`.rddf/reviews/` … 该目录共 **38 份**」 | 实测 **128 份**（`~/.config/opencode/.rddf/reviews/*.md`） |
| 19 | `docs/SUBAGENT-ORCHESTRATION.md:174` | 「CHANGELOG（v2.12–v2.19 覆盖本轮）」→ 已到 **v2.66** |
| 20 | `docs/SUBAGENT-ORCHESTRATION.md:1` | 标题日期「2026-11-13」未随 11-20 加入的 `plan-worker` 段更新 |

### 3.4 ✅ CHANGELOG 未落后

`docs/CHANGELOG.md:13` 最新条 = **v2.66（2026-11-23）**，与 HEAD 提交逐字对应。

### 3.5 跨仓指针的固有限制

`docs/architecture/agent-role-alignment.md:21` 声明「本页关于 opencode 侧的描述对应 `prompts/build.md` 的 **2026-11-17** 状态」。opencode 侧已到 **v2.66（2026-11-23）**，中间 v2.64/2.65/2.66 三轮改动（v2.66 改的正是 `build.md:454` 那行）。

该文档**已自我声明不是真源**（`:5-6`「本页不是真源…与代码/契约不一致时以真源为准」）且**只保留不随实现漂移的部分**（命名/归属判定/双落点）⇒ 影响可控。但本仓**无法机检**这 6 处指针。

## 四、遗留 P0（本回合已清）

| # | 债务 | 状态 |
|---|---|---|
| 21 | 6 份 4 行空壳 spec ⇒ `validate` ERROR 6 | ✅ 已删（`openspec-tracked-specs-2026-11-23.md`） |
| 22 | `openspec/` 整树 gitignore ⇒ 159 份 spec 无 git 保护 | ✅ 方案 B 已实施（specs + config.yaml 入库） |
| 23 | CI 无 `openspec validate` 门 | ✅ 严格门已加（ERROR=0）+ 本地门镜像 |

## 五、其余已知债务（P2）

| # | 项 | 说明 |
|---|---|---|
| 24 | 136 份 spec 的 `## Purpose` 仍是 `TBD - created by archiving change X` | WARNING 级；严格门放行 |
| 25 | 62 条 `very long` issue | 已冻结（不新增） |
| 26 | `rddf archive` 缺交互确认门 | 行为变更，需用户拍板 |
| 27 | `install.sh:27` 的 `deprecated:` 口径分叉 · `docs/improvement-approved-format.md:3` | 小口径不一致 |
| 28 | `doc-truth-sync` 的 Requirement 主题划分 | 需重新划分 |
| 29 | doctor 8 WARNING：4 条 ADR「待定」+ `quick-ci-runner-parity.md` 缺 TDD 标记 + AGENTS.md 无 Layer 0 块 + 2 条陈旧基线（roadmap backup 94 天 / KNOWN_FAILURES 46 天） | 逐条可修 |
| 30 | 形态清单应按「形态类」登记（`spec_form_compliant.json` 现只按文件登记 `acceptance-N`） | 第 5 批 critic 的 SF-5，已记 backlog |

## 四·五、本轮新发现的 P1 契约缺口（**需用户裁决**）

### #31 ADR-0031 的「跨项目人类兜底门禁」在 v4 stage-merge 后**无实现**

| 证据 | 结果 |
|---|---|
| ADR-0031 的实现载体 `skills/guide-design/scripts/approve_proposal.sh` | **文件不存在**（v4 stage-merge ADR-0043 移除 `guide-design`） |
| `RDDF_REQUIRE_HUB_APPROVAL`（ADR-0031 的门控开关） | 在 `_lib/` / `skills/` / `tests/` 中**零命中** ⇒ 无任何读取点 |
| ADR-0031 Verification 声称的 `tests/integration/test_strict_human_approval.bats`（9 cases） | **文件不存在** |
| `_lib/cross_repo_audit.py`（ADR-0031 新增的审计模块） | 存在，但**无调用方**（只被 `skills/_lib/` 的 identity-merge shim 引用） |
| `skills/rdd-builder/scripts/phase0_approval.sh`（v4 的 P0 批准门） | **不处理** `category=cross-repo`（grep 零命中） |

⇒ **ADR-0031 的核心承诺「所有 `**分类**: cross-repo-federation` 的提案，AI 不可自动批准」当前无代码兑现。**

仍在声称它存在的文档：
- `docs/architecture/hub-and-spoke-federation.md:53,72` —— **本轮已改为「实现缺失」标注**（不再声称有门禁）
- `docs/strict-gate-boundary.md` —— **本轮已重写为 v2**：`:32`（矩阵行）与 `:61`（已消失的门）均标 ❌ 无代码，
  并注明「ADR-0031 声称的集成测试不存在」⇒ 该文件**不再声称门禁存在**（待随 #31 裁决一起定稿）

**需要用户裁决的两条路径**（本仓 builder 无权自行决定）：
- **A. 重实现**：把 cross-repo 硬阻断接进 `phase0_approval.sh`（P0 批准门），补 `RDDF_REQUIRE_HUB_APPROVAL` 读取点 + 集成测试 ⇒ 兑现 ADR-0031
- **B. 退役**：把 ADR-0031 标为 superseded / 部分未实现，同步改 `docs/strict-gate-boundary.md`
  （该文件已在本轮标为「无代码」，退役裁决只需补 ADR 状态 + 最终口径）⇒ 承认该门禁不存在

⚠️ 选 B 意味着**「跨项目提案可被 AI 自动批准」成为既定事实** —— 需先确认 Hub 侧是否有等价管控。

### #32 `_lib/planner_feedback.py:8` 的 docstring 引用不存在的 schema

`_lib/planner_feedback.py:8` 写「see `_lib/schemas/planner_feedback_schema.json`」，但该文件**不存在**
（`_lib/schemas/` 下只有 `feedback_entry_schema.json`）⇒ 悬空引用（小债，本轮已在
`skills-and-handoff.md` 的 schema 表下注明，未改代码 docstring）。

### #33 `_lib/gate.py` 的 `GateMechanism` 未在生产路径接线（**P1 实质缺口**）

| 证据 | 结果 |
|---|---|
| `_lib/gate.py:404` `class GateMechanism` | **生产代码零命中**（唯一定义处；仅 `tests/unit/test_gate.py` · `tests/integration/test_gate_transition.py` import）—— 没有任何 skill / CLI 实例化它 |
| `_lib/gate.py:371` `_DEFAULT_CHECKS`（`arch_done` / `plan_done` / `ship_done` 三组） | 只在 `gate.py:416` 内部被读，无外部消费方 |
| `STRICT_CHANGE_GATE` 的 3 个 Check（`gate.py:385-387`） | 注册在未接线的机制里 ⇒ **设了不生效** |
| `STRICT_PROPOSE_GATE` 的 Check（`gate.py:390`） | 同上 |
| `_lib/change_alignment.py`（ADR-0019 的 3 个检查） | 只被 `_lib/gate.py:34` import，**无其它调用方**；doctor 的 category 列表里也没有 change-alignment |
| 唯一的 import 方 | `tests/unit/test_gate.py` · `tests/integration/test_gate_transition.py`（**只有测试**） |

⇒ **ADR-0019（change 与架构对齐）声明的 3 项检查在生产流程中不执行。**
这比「无实现」更隐蔽：代码在、测试绿、但门是虚的。

⚠️ **需用户裁决**：
- **A. 接线**：把 `GateMechanism` 接进 v4 的阶段出口（`planner_stage_exit.sh` / `phase3_archive.sh`），
  或把 3 个检查改挂到已接线的机制（如 `arch_quality_gate.py` / doctor category）
- **B. 退役**：把 ADR-0019 标为部分未实现 + `_lib/gate.py` 的 Check 注册表标为 legacy

本轮**只做文档标注**（`docs/strict-gate-boundary.md` 补「实现状态」列 + 明确未接线），
不改机制 —— 接线是行为变更，需先定 ADR-0019 的口径。

## 六、建议的处理顺序

1. ~~**P1 本仓**（builder 权限内，可直接改）~~ ✅ **本轮已做**：handoff 族重写（#1-5）+ 幽灵路径/数量/行号（#6-10）+ 文档自相矛盾 + arch-handoff 版本统一 + §8 消费者兼容重写（处置明细见 §2.5）
2. **#31 跨项目人类兜底门禁** —— 需用户裁决 A（重实现）/ B（退役），**不进本轮**（行为变更）
3. **#33 `GateMechanism` 未接线** —— 需用户裁决 A（接线）/ B（退役 ADR-0019 口径），**不进本轮**
4. **P1 治理面**（需切 `architect` + oracle→critic）：`MULTI-AGENT-DESIGN.md` 计数与委派矩阵（#11-15）+ `build.md` 表内补项与标注（§3.2）+ 悬空引用（#16-20）
5. **P2**：#24-30 逐项立项 + ADR 状态格式统一（§2.4）+ #32 docstring 悬空引用

> ⚠️ 治理面那批（`prompts/**`、`docs/MULTI-AGENT-DESIGN.md`、`docs/SUBAGENT-ORCHESTRATION.md`）
> 按 `build.md` 的「治理面作用域」表必须走 oracle → critic；`builder` 撞到治理面缺陷时
> **不直接编辑**，交用户决定是否切 `architect`。
