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

## 三、跨仓漂移（`~/.config/opencode`，P1/P2）

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

## 六、建议的处理顺序

1. **P1 本仓**（builder 权限内，可直接改）：`skills-and-handoff.md` handoff 族重写（#1-5）+ 幽灵路径/数量/行号（#6-10）+ ADR 状态统一（#2.4）
2. **P1 治理面**（需切 `architect` + oracle→critic）：`MULTI-AGENT-DESIGN.md` 计数与委派矩阵（#11-15）+ `build.md` 表内补项与标注（§3.2）+ 悬空引用（#16-20）
3. **P2**：按 #24-30 逐项立项

> ⚠️ 治理面那批（`prompts/**`、`docs/MULTI-AGENT-DESIGN.md`、`docs/SUBAGENT-ORCHESTRATION.md`）
> 按 `build.md` 的「治理面作用域」表必须走 oracle → critic；`builder` 撞到治理面缺陷时
> **不直接编辑**，交用户决定是否切 `architect`。
