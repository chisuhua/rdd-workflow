---
优先级: P1
priority: P1
来源: 2026-11-17 第八批 5 项归档过程发现（follow-up H/I/J 合并）——P1.5 的执行模式判定喂给判据的
  是三个占位值（task_count=5 硬编码 / risk_keywords=[] / file_count 数的是 change 目录文件数）
  ⇒ lightweight 分支不可达、handoff 里写下的是假 reason；且 schema 与已签批 spec 承诺的
  「openspec_tracked=false ⇒ lightweight」无任何实现
阶段: phase-2
分类: bugfix
类型: bugfix
状态: draft

生成时间: 2026-11-17
roadmap_ref:
---

# fix-execution-mode-decision

**主题**: 阶段步骤化执行

> ⚠ **本项含一条已签批 spec Requirement 的 retire-or-implement 决策**（`openspec/specs/complete-project-yaml-config-gaps/spec.md:203-217`），需 architect 签批（见「架构依据 · 三方一致性」）。

## 架构依据

### 缺陷一：判据的三个输入全是占位值，handoff 里写下的是**假 reason**

`_lib/builder_deps.py:16-27` 的判据本身与 **ADR-0024 的决策表**是一致的：

```
| 信息类型 | 来源 | 对执行模式的影响 |          （docs/adr/ADR-0024）
| **文件数** | design.md (Create/Modify/Delete 行) | ≤2 → lightweight |
| **任务数** | tasks.md (checkbox 行) | ≤3 → lightweight |
| **风险关键词** | proposal.md | refactor/migration/breaking → worktree |
| **文件冲突** | deps-analysis.json → conflicts | 有冲突 → worktree |

### 决策阈值
if is_risky:          return "worktree"
elif file_count <= 2 and task_count <= 3:  return "lightweight"   # 小改动
elif file_count <= 5 and task_count <= 6:  return "lightweight"   # 中等改动 - 优化小改动开销
```

**问题在唯一的生产调用方** `skills/rdd-builder/scripts/phase1_5_deps.sh:53-61`：

```python
files_changed = sum(1 for _ in glob.glob("openspec/changes/$CHANGE_NAME/**", recursive=True))
task_count = 5                       # ← 硬编码
risk_keywords=[]                     # ← 硬编码（RISK_KEYWORDS 规则永不触发）
```

| 输入 | 实际来源 | 问题 |
|---|---|---|
| `file_count` | change 目录下的**条目数**（`glob` 连目录一起数） | 不是「这个 change 会改多少文件」，而是「change 目录里放了几份文档」；且 `glob` 未过滤 `isfile` ⇒ 目录也算 |
| `task_count` | 常量 `5` | `tasks > 3` **恒真** ⇒ `lightweight` 分支**不可达** |
| `risk_keywords` | 空列表 | `RISK_KEYWORDS = {"refactor","migration","breaking","schema-change"}`（`_lib/builder_deps.py:13`）这条规则**永不触发** |

⇒ 结论：**P1.5 的执行模式判定实际只有「恒 worktree」一种结果**，且它与 ADR-0024 的三段梯度**直接矛盾**（ADR 的中段 `≤5 文件 且 ≤6 任务` 也是 lightweight）。

**实测证据（本批 2 份 handoff 原文）**：

```
.rddf/state/builder/fix-flow-drift-batch-1.json      "reason": "files=6>2 AND tasks=5>3"
.rddf/state/builder/fix-phase3-cleanup-wiring.json   "reason": "files=6>2 AND tasks=5>3"
```

而 `fix-flow-drift-batch-1` 的 tasks.md 实际只有 **4** 条 ⇒ **写进 handoff 的 reason 是编造的**（tasks 恒为 5、files 是目录条目数）。
⇒ **用户真正要的首先是「P1.5 别再输出假话」**，而不是「让 change 走 lightweight」—— 后者是推论，不是现场痛点。

### 缺陷二：「lightweight」有三个互不等价的定义

| 出处 | 「lightweight」指什么 |
|---|---|
| `skills/rdd-builder/scripts/phase2_execute.sh:117-119` | **无 worktree、无分支**（`EXEC_DIR="$PROJECT_ROOT"`） |
| `_lib/schemas/config_schema.json:225` / `spec.md:209,212` | **无 worktree、但有分支**（"branch only, no worktree"） |
| `_lib/ship_execution_mode.sh:80-96` | **serial 波次执行**（注释写 "forces lightweight (serial)"，返回 `serial`） |

⇒ 不先把定义钉死，任何「模式判定」的 AC 都不可判定，`phase3_archive.sh` 的 lightweight 分支意味着什么也会随定义漂移。

### 缺陷三：schema 与**已签批 spec** 都承诺了一件没实现的事

- `_lib/schemas/config_schema.json:222-226`：
  > "openspec_tracked": … "If false, **force lightweight mode (branch only, no worktree)** and skip git merge/commit in archive"
- `openspec/specs/complete-project-yaml-config-gaps/spec.md:203-217` —— 一条 **normative Requirement**：
  > `### Requirement: guide-ship-phase-1-detect-lightweight`
  > The … Phase 1 SHALL include Step 1.5 that reads `.rddf/project.yaml` `git.openspec_tracked` field **BEFORE worktree creation** (Step 2), and **force lightweight mode when set to `false`**.
  > Scenario: … SHALL set `RDDF_EXECUTION_MODE=lightweight` environment variable … SHALL proceed directly to lightweight branch execution.

而实现里：`openspec_tracked` 被 `_lib/archive.sh`（归档路径）与 `_lib/ship_execution_mode.sh:87`（→ `serial`）读过，但**执行模式判定完全不看它**；
`RDDF_EXECUTION_MODE` 全仓 **0 个读取点**。

**实测**：本仓 `git.openspec_tracked: false`，P1.5 却判出 `mode=worktree` ⇒ 与 schema 描述、spec Requirement **双重矛盾**。

⇒ 「false ⇒ lightweight」不是「文档写错了」这么简单：它是一条**已签批的 spec Requirement**。删掉 schema 描述会留下未实现的 spec ⇒ **需要 spec delta 或 retire ⇒ architect 决策**，不是实施细节。

### 附带：ADR-0024 的两个来源已死

ADR-0024 的文件数来源是 **design.md 的 Create/Modify/Delete 行**，而 v4 的归档里 **17 个近期 change 无一含 design.md**（v4 由 ADR-0043/0048 改为 proposal/design/tasks 三件，但 design.md 在本仓实际不生成）⇒ 该来源已失效，需要换来源或显式记为不可得。

## 范围

- **In Scope**：① 把「lightweight」的定义钉死为一份契约（三个来源取一）；② P1.5 的三个输入改为**反映真实工作量**，且**输入不可得 ⇒ fail-closed（worktree）**；③ `reason` 如实反映实际输入值；④ 风险规则改为**结构化声明**（`roadmap-meta.yaml` 的 `risk: normal|high`，该文件 P1.5 已在读）；⑤ 抽出可测的输入计算函数 `_lib/builder_deps.py::compute_mode_inputs(project_root, change_name)`；⑥ `LEGACY_EXEC_MODE` 残留处置；⑦ 冲突维度的最小实现（ADR-0024 第 4 行从未实现）；⑧ `openspec_tracked=false ⇒ lightweight` 的 **三方一致性**（schema + 代码 + spec Requirement），**由 architect 签批**。
- **Out Scope**：不改 `decide_execution_mode` 的**函数签名**与 RISK_KEYWORDS 词表；不改 deps 阻塞分析（`analyze_deps` / strict gate）；不改 rdd-quick 的 auto-pick（ADR-0047：最终由 LLM 判断）；不改 `git.openspec_tracked` 的**归档**语义（跳过 merge/commit 那半句已实现）；不在 `skills/rdd-builder/scripts/` 新增 `phase*` 脚本（会打红「恰好 6 个 phase 脚本」的既有断言）；不改 `decide_execution_mode` 的**阈值**（阈值要不要按 ADR-0024 调整是独立的策略决策，见「备选方案」与 Impact）。

## Why

**首要意图是「P1.5 别再输出假话」**：handoff 里那句 `"files=6>2 AND tasks=5>3"` 是**编造的**（该 change 实际 4 条 task、6 是目录条目数）。它会被后续阶段、看板、agent 当作事实读取 ⇒ 一条假证据会持续影响后续决策。

「让小 change 走 lightweight」是**推论**而非现场痛点，且代价明确：本批 5 项实测全是 worktree（`fix-flow-drift-batch-1` 只改 4 个源文件 + 3 个测试）；ADR-0024 明写「中等改动也优先 lightweight，这是优化小改动开销的**核心目标**」—— 即目标早已写进 ADR，只是实现没兑现。

**第三条意图：让 `project.yaml` 变成可信的配置面**。但「false ⇒ lightweight」不只是描述 —— 它同时是一条已签批 spec Requirement ⇒ 动它是**架构决策**，不能由实施者顺手「要么实现要么删描述」。

metis 指出的**成本权衡**（已写进「备选方案」）：只做「诚实化」（删伪梯度 + reason 说真话 + 输入 fail-closed）能一次性消除**有实测证据**的两个缺陷，不暴露 lightweight 缺口、不引入文本扫描与并发风险、不需要 ADR 签批扩展，成本约为「全量对齐」方案的 1/3。

## What Changes

1. **钉死 lightweight 的定义**（契约段落，写进 `skills/rdd-builder/SKILL.md` 与 `docs/architecture/workflow-phases.md`）：
   明确 lightweight = **无 worktree、无独立分支、在主仓当前分支直接实施**（对齐 `phase2_execute.sh:117-119` 的既有行为）；
   `ship_execution_mode.sh` 的 `serial` 是**波次并发维度**，不是执行模式维度 ⇒ 两者解耦并各自命名（`execution_mode` ∈ {worktree, lightweight}、`wave_mode` ∈ {serial, parallel}）。
2. **输入计算抽成可测函数**（`_lib/builder_deps.py` 新增 `compute_mode_inputs(project_root: str, change_name: str) -> dict`）：
   内部一律用**绝对路径**（现状是 cwd 相对路径 + `sys.path.insert(0,"$PROJECT_ROOT")`，导致「只能在 fixture 里测函数、不能测接线」）；
   返回 `file_count` / `task_count` / `risk_keywords` / `notes`（`notes` 记录哪些输入不可得）。
   `decide_execution_mode` 的签名与阈值**不动**（`phase1_5_deps.sh` 只做 glue）。
3. **三个输入的来源与 fail-closed 规则**：
   - `task_count`：`openspec/changes/<name>/tasks.md` 的 checkbox **total**（`[x]` + `[ ]`，大小写不敏感）—— **不是** open 数（否则归档后全勾选会得 0）；**缺失或为 0 ⇒ fail-closed（worktree）+ notes 记 `tasks=unknown`**。
     ⚠ **真实反例**：`phase1_plan.sh:50` 只抽取 `^### Task `（三井号），而仓内真实 plan 用 `## Task N:`（二井号，21 个 plan）⇒ 这些 plan 会生成**只有段头的空 tasks.md**（0 checkbox）⇒ 若按 0 计会把大 change 判成 lightweight ⇒ 必须 fail-closed。
   - `file_count`：唯一可行来源是 **`.rddf/plans/<change>.md` 的 `**Files:**` 段**（`Create:` / `Modify:` / `Test:` 行；`rdd-workflow-writing-plans/SKILL.md:198` 强制要求，仓内 plan 确实有）。解析需去重、剥行号、剥反引号、按路径归类。
     **不采用**：design.md（v4 归档里不存在 ⇒ ADR-0024 的来源已死）、proposal 的 Capabilities/Impact 段（本仓 proposal 时有时无 ⇒ 伪造精度）。
     plan 缺失 ⇒ **`files=unknown`，该输入不参与判定**（不是「取默认值」）。
   - `risk_keywords`：**删除文本扫描**（证据见下），改为读 `openspec/changes/<name>/roadmap-meta.yaml` 的 `risk: normal|high`（该文件 P1.5 已在读，`phase1_5_deps.sh:41-50`）；默认 `normal` ⇒ risk 规则不触发；`high` ⇒ worktree。
4. **reason 诚实化**：`reason` 必须**只写实际用到的输入值与不可得项**（如 `tasks=4>3 AND files=unknown`），禁止出现常量 5；`files=unknown` 时判定只由 tasks/risk 决定，并在 reason 里写明。
5. **三方一致性（architect 签批）**：`config_schema.json:225` + P1.5 的判定代码 + `complete-project-yaml-config-gaps` 的 `guide-ship-phase-1-detect-lightweight` Requirement —— 三者必须一致：
   - **选项 A（实现）**：P1.5 在建 worktree **之前**读 `git.openspec_tracked`，false ⇒ 强制 lightweight（并按 ADR-0024 补 `RDDF_EXECUTION_MODE` 的实际读取点，或删掉该 env 要求）；本仓（false）此后**不再有 worktree** ⇒ 执行模型整体变化 ⇒ 需 ADR + 迁移说明。
   - **选项 B（retire）**：把该 Requirement 与 schema 描述一并 retire，改为「该开关只影响归档路径」，并把 spec 的「force lightweight」表述改成与实现一致的表述。
   - 两条都需 spec delta；**本项不替 architect 做这个选择**，但必须把两条路线的代价写清（见 Impact）。
6. **`LEGACY_EXEC_MODE` 残留处置**（v4 残留：`.plan-handoff.json` 已无写入方，但存在即无条件覆盖新判定并把 reason 换成固定文案）：
   删除，或降为**最低优先级** + 覆盖时打印 WARN + 保留计算得到的 reason（不得用固定文案替换）。
7. **冲突维度最小实现**（ADR-0024 第 4 行「文件冲突」从未实现 —— `analyze_deps` 只返回 `blockers`/`cross_manifest`/`cross_repo_pending`）：
   `compute_mode_inputs` 顺带计算「其它 change 的 plan `Files:` 与本 change 的交集」或「`.rddf/wt/` 下是否有活跃 worktree」；非空 ⇒ worktree。
   ⇒ 这是「放开 lightweight」的安全前提：两个 lightweight change 在主仓同文件并发，没人隔离。
8. **计数口径**与 `fix-iteration-tasks-total` 共用同一标准（该草案已把口径收敛到 `archive_sidecar.count_tasks(text) -> (done, total)`）⇒ **本项不新造第三套**（metis 指出仓内已有两套漂移口径：`_lib/archive.sh:137,140,389` 锚定 `^- \[[xX]\]` vs `_lib/discover_ship_changes.py:82` 非锚定 `count`）。

### 备选方案（成本更低，先评估它）

**Option A（诚实化，最小）**：`decide_execution_mode` 只保留 `task_count` 一条真实输入，删掉 `file_count` / `risk` 两条死规则；`reason` 直书「worktree（lightweight 未接线 / 未验证）」；schema 承诺与 spec Requirement 一并 retire。
- 收益：一次性消除**有实测证据**的两个缺陷（假 reason、schema 撒谎）；不暴露 lightweight 缺口；不引入文本扫描与并发风险；不需扩展 ADR。
- 代价：「小 change 走 lightweight」的目标继续推迟（与 ADR-0024 的核心目标仍有差距）。

## Acceptance

- [ ] 「lightweight」的定义被写成一份契约（**有 `openspec/<change>` 分支、无 worktree、在主仓该分支上实施** —— per ADR-0036 的 2026-11-17 修订：与 ADR-0024 / ADR-0036 Decision 表 / schema / `verifier-lifecycle` 五处既有文本一致；⚠ **原草稿写的「无独立分支、主仓当前分支实施」是把实现缺陷当成契约，已作废**）；`ship_execution_mode.sh` 的 `serial` 被改名为波次维度（不再与执行模式混用）
- [ ] `compute_mode_inputs(project_root, change_name)` 存在于 `_lib/builder_deps.py`，内部全用绝对路径；`decide_execution_mode` 的签名与阈值不变
- [ ] `task_count` 取 tasks.md 的 checkbox **total**（大小写不敏感）；**缺失或 0 ⇒ fail-closed（worktree）** 并在 notes/reason 写 `tasks=unknown`
- [ ] 夹具断言（**改动前第一条必须是红的**）：`tasks.md` 2 条 + plan `Files:` 2 个 ⇒ `lightweight`；`tasks.md` 5 条 ⇒ `worktree`；`tasks.md` 只有段头（0 checkbox，取自 `## Task` vs `### Task` 的真实反例）⇒ `worktree`。⚠ **启用前置**：第 1 条（小改动 ⇒ lightweight）**只有在 `fix-lightweight-branch-and-archive` 落地后**才成立 —— 在它落地前，同一组输入必须判 **worktree** 并在 `reason` 里写明「lightweight 未落地（无实现分支 / 归档路径未补齐）」⇒ 夹具断言分两段验收（见下方「plan_drift 处置」）
- [ ] `file_count` 来自 `.rddf/plans/<change>.md` 的 `**Files:**` 段（去重、剥行号、剥反引号）；plan 缺失 ⇒ `files=unknown` 且**该输入不参与判定**（不取默认值）
- [ ] `risk_keywords` 改为读 `roadmap-meta.yaml` 的 `risk: normal|high`；**不做 proposal/tasks 文本扫描**；默认 `normal` 不触发 risk 规则
- [ ] `reason` 只写实际输入值与不可得项；**不再出现常量 5**；handoff 里写入的 reason 与实际一致（对本批 change 重跑 P1.5 验证）
- [ ] 冲突维度有最小实现（其它 change 的 `Files:` 交集非空 或 存在活跃 worktree ⇒ worktree）+ 夹具断言
- [ ] `LEGACY_EXEC_MODE` 已删除或降为最低优先级（覆盖时 WARN 且保留计算 reason）+ 对应测试
- [ ] **三方一致性**：**已由 architect 签批裁定**（ADR-0036 的 2026-11-17 修订，Status `已采纳 + AMENDED (2026-11-17)`，审稿报告 `.rddf/reviews/adr-0036-amendment-2026-11-17.md`）—— 选**退役/改写**（非「实现 false ⇒ lightweight」），理由与逐条处置见该 ADR 的修订节与审稿报告。⇒ 本项的落地动作 = 执行该修订已定的处置：`config_schema.json` 描述收窄为归档路径语义；`README.md:87/:100` 同步；退役清单 R1~R10 逐条处置（负向断言 / 退役僵尸变量 `RDDF_EXECUTION_MODE` / R4 正向重指向 / owner 与路径重指向）+ 全局残余面（204 处 / 47 份 spec）作为**独立 backlog** 立项（不冒充本项验收项）
- [ ] 计数口径与 `fix-iteration-tasks-total` 共用同一标准，未新造第三套
- [ ] 同名函数防护：`_lib/subagent_strategy.py:44` 的 `decide_execution_mode(task_type, quota_status)` 与 `_lib/builder_deps.py:16` 签名不同 ⇒ 加 `inspect.signature` 断言，或重命名 builder 版（唯一生产调用点仅 `phase1_5_deps.sh`）
- [ ] 新增代码不落在 `skills/rdd-builder/scripts/phase*`（不打红「恰好 6 个 phase 脚本」断言）
- [ ] `./test.sh --unit` + `./test.sh --full --regression` 全绿 + `bats tests/integration/test_rdd_builder_phases.bats` + `bats tests/integration/test_builder_deps*` 全绿

## Capabilities

- P1.5 不再输出**编造的 reason** —— handoff 里写下的每个数字都对应真实输入
- 输入不可得时**fail-closed**（判 worktree），不再把「未知」当成「很小」
- 风险判定从**文本扫描**（英扫召回≈0、中扫假阳为主）改为**结构化声明**
- `project.yaml` 的 schema 描述、spec Requirement 与代码行为三者一致（不再三方各说各话）
- 「lightweight」不再有三种互相矛盾的定义

## Impact

- **影响面**：`_lib/builder_deps.py`（新增 `compute_mode_inputs`）、`skills/rdd-builder/scripts/phase1_5_deps.sh`（改为 glue + 传绝对路径 + 新增 `risk` 读取 + fail-closed）、`openspec/changes/<name>/roadmap-meta.yaml`（新增 `risk` 字段）、`_lib/schemas/config_schema.json`（描述）、`openspec/specs/complete-project-yaml-config-gaps/spec.md`（Requirement）、`skills/rdd-builder/SKILL.md` + `docs/architecture/workflow-phases.md`（契约）、`skills/rdd-builder/scripts/phase1_5_deps.sh` 的 `LEGACY_EXEC_MODE` 分支（删除或降级）、`_lib/ship_execution_mode.sh`（命名解耦）、新增 pytest + bats。
- **风险**：
  - **三方一致性那一项是架构决策，不是 bugfix**：若选「实现 false ⇒ lightweight」，本仓（false）此后**不再有 worktree** ⇒ 整个执行模型变化（本批第 2 项 `fix-worktree-archive-path` 做的正是 worktree 路径的归档修复）⇒ 需 ADR + 迁移说明 + architect 签批。**本项的前 7 条（诚实化与 fail-closed）可独立先行**，第 8 条（三方一致性）单独走架构流程。
  - 放开 lightweight 会暴露 lightweight 路径的既有缺口：`skills/rdd-builder/scripts/phase3_archive.sh:135-145` 的 inline 分支**不做 `post_archive_cleanup`、不调 `mark_iteration_archived`**（后者在 `_lib/archive.sh:626` 是独立函数，lightweight 可直接调用，不必经需要 worktree 的 `archive_change`（`:591-594`））。
    ⚠ **注意**：lightweight 下 `phase2_execute.sh` **不建分支** ⇒ 「提交停在分支上无人合并」**不成立**（该缺口只属于 worktree 路径，已由 `fix-worktree-archive-branch-merge` 覆盖）⇒ 本项要补的是 **cleanup + iteration 同步**，不是「分支是否合入」。
  - 冲突维度若不实现，放开 lightweight 会让两个 change 在主仓同文件并发 ⇒ 故本项把冲突维度列入 In Scope。
  - 文本扫描被移除后，**过去依赖英文风险词命中**的行为消失（实际从未命中过 ⇒ 无回归）。
- **兼容性**：`decide_execution_mode` 的签名与阈值不变 ⇒ `tests/unit/test_builder_deps.py` 的既有断言（`:20` 断言 reason 精确子串 `"files=2<=2 AND tasks=3<=3"`）**若 reason 格式变化需同步更新**（本项要求 reason 格式保持稳定、只换数值 ⇒ 该断言应仍绿）。
- **依赖**：
  - 与 `fix-iteration-tasks-total` 共用「tasks.md 计数」标准（该草案已收敛到 `archive_sidecar.count_tasks`）⇒ 本项**不新造第三套**；
  - 与 `fix-worktree-archive-branch-merge` 的关系是**互斥/先后**，不是互相成就：lightweight 一旦普及，`openspec_tracked=false × worktree` 这个组合变少，那一项的收益面反而缩小 ⇒ 两项应明确先后顺序（本项的诚实化部分先行；那项针对的是仍走 worktree 的项目）。

## 审稿记录

metis 1 轮（2026-11-17）。逐条处置：

- **采纳 P0-1（事实修正 + 三方一致性）**：原草稿称「全仓 `openspec_tracked` 只在 `_lib/archive.sh` 被读」是**错的** —— `_lib/ship_execution_mode.sh:87` 也读（→ `serial`），且有测试钉住。已修正，并把「schema 一致性」扩成**三方一致性**（schema + 代码 + `complete-project-yaml-config-gaps` 的 normative Requirement `guide-ship-phase-1-detect-lightweight`，其 scenario 断言的 `RDDF_EXECUTION_MODE` 全仓 0 读取 ⇒ 只删 schema 描述会留下未实现 spec）⇒ 标为需 architect 签批。
- **采纳 P0-2（「不改阈值」使收益归零）**：原草稿称「判据本身没问题」不成立 —— **ADR-0024 的阈值是三段梯度**（`≤2/≤3` → lightweight；`≤5/≤6` → **也** lightweight），与现实现 `files>2 OR tasks>3 ⇒ worktree` **直接矛盾**；且本批 change 实际 4 条 task ⇒ 即便修准输入，仍 `tasks=4>3` ⇒ worktree。已把「阈值是否对齐 ADR-0024」从「Out Scope 里的不言」提升为**必须决策项**（写进 Impact 与「备选方案」）。
- **采纳 P0-3（`file_count` 的唯一可行来源）**：原草稿在三个候选里选了一个不可靠的。已改为：唯一可行来源是 `.rddf/plans/<change>.md` 的 `**Files:**` 段；**明确否掉** design.md（v4 归档里不存在 ⇒ ADR-0024 的来源已死）与 proposal 的路径估算（时有时无 ⇒ 伪造精度）；plan 缺失 ⇒ `files=unknown` 且该输入不参与判定。
- **采纳 P0-4（输入失败必须 fail-closed）**：原草稿写「tasks.md 缺失 ⇒ 计数 0」—— 而 0 会判 lightweight ⇒ **fail-open**。已改为「缺失/0 ⇒ worktree + `tasks=unknown`」，并把 `phase1_plan.sh:50` 抽 `^### Task ` 而真实 plan 用 `## Task N:`（21 个 plan ⇒ 生成空 tasks.md）的真实反例写进 AC 夹具。
- **采纳 P0-5（lightweight 的真实缺口）**：原草稿说 lightweight 也有「分支未合入」问题 —— **不成立**（`phase2_execute.sh:117-119` 不建分支）。真实缺口是 `phase3_archive.sh:135-145` 缺 `post_archive_cleanup` + `mark_iteration_archived`（后者是 `_lib/archive.sh:626` 的独立函数，lightweight 可直接调）。已改写该条，并**同步修正 `fix-worktree-archive-branch-merge` 里对 lightweight 的交叉引用**。
- **采纳 P1-1（补更小的备选方案）**：已新增「备选方案：Option A（删伪梯度 + reason 诚实化）」，并把成本对比（1/3）与其取舍写明。
- **采纳 P1-2（删掉文本扫描）**：原草稿「扫 proposal/tasks 找 RISK_KEYWORDS」噪声最大：英文四词在本仓主要命中**文件名**与 **frontmatter**，中文对应词主要命中**否定式 Out Scope**（「不重构」「无 API 破坏」）⇒ 越认真声明不改风险面越被判高风险。已改为读 `roadmap-meta.yaml` 的 `risk: normal|high`（该文件 P1.5 已在读）。
- **采纳 P1-3（输入计算抽成可测函数）**：原草稿的「接线级测试」在现状下做不出来（cwd 相对路径 + `sys.path.insert` 牵扯）。已指定 `_lib/builder_deps.py::compute_mode_inputs(project_root, change_name)`（绝对路径）+ 测试主体放 pytest。
- **采纳 P1-4（`LEGACY_EXEC_MODE` 处置）**：已列入 What Changes（二选一 + 对应测试）。
- **采纳 P1-5（冲突/并发守卫）**：已列入 In Scope（ADR-0024 第 4 行从未实现；放开 lightweight 的安全前提）。
- **采纳 P2-1（同名函数防护）**：已加 AC（`inspect.signature` 断言或重命名 builder 版）。
- **采纳 P2-2（计数口径先定标准）**：已改为与 `fix-iteration-tasks-total` 共用同一标准，不新造第三套。
- **采纳 P2-3（新文件位置）**：已加 AC（不放 `skills/rdd-builder/scripts/phase*`）。
- **采纳 P2-4（回归门）**：已加 `./test.sh --full --regression`。
- **采纳（首要意图）**：原草稿把「让 change 走 lightweight」当主因；metis 指出**有实测证据的痛点是 reason 不可信**（handoff 原文 `"files=6>2 AND tasks=5>3"` vs 实际 4 条 task）⇒ 已把 Why 改为「首要意图是别再输出假话，lightweight 是推论」。
- **记录未采纳**：metis 提到「`fix-iteration-tasks-total` 在 `.rddf/improvements/` 下找不到」—— 实为该文件已存在（本次同批创建），依赖名无误。

## 立项核查（2026-11-17，planner）

**本项断言 100% 准确，逐条命中**：

| 断言 | 核实结果 |
|---|---|
| `task_count = 5` 硬编码 | ✅ `phase1_5_deps.sh:56` `task_count = 5` |
| `risk_keywords=[]` | ✅ `:60` `risk_keywords=[],` |
| `file_count` 数的是 change 目录文件数 | ✅ `:54` `files_changed = sum(1 for _ in glob.glob("openspec/changes/$CHANGE_NAME/**", recursive=True))` ⇒ 数的是 proposal/design/tasks/specs 等全部文件，**不是** plan 的 `Files:` 段 |
| `decide_execution_mode` 签名 `(file_count, task_count, risk_keywords)` | ✅ `_lib/builder_deps.py:16` |
| `_lib/subagent_strategy.py:44` 有同名不同签名函数 | ✅ `(task_type, quota_status)` ⇒ 立项要求的 `inspect.signature` 断言或重命名是必要的 |
| `LEGACY_EXEC_MODE` 覆盖仍在 | ✅ `phase1_5_deps.sh:25-34` 读 `.plan-handoff.json`；`:63-67` 覆盖 mode 并**改写 reason** |
| `ship_execution_mode.sh` 的 `serial` 与执行模式混用 | ✅ 该脚本的 `DEFAULT_MODE="serial"` 是**并发维度**（wave 调度），与 lightweight/worktree 不是一维 |
| 「恰好 6 个 phase 脚本」断言存在 | ✅ `tests/integration/test_rdd_builder_phases.bats:156` `[ "$count" -eq 6 ]` ⇒ 新增代码确实不能落 `phase*` |
| `config_schema.json` 承诺 `openspec_tracked=false ⇒ force lightweight` | ✅ `git.openspec_tracked` 的 description 原文 "If false, force lightweight mode (branch only, no worktree)"，而代码里无此实现 |

⇒ 立项诊断准确。**本项含「已签批 spec Requirement 的 retire-or-implement 决策」⇒ 实施前需 architect 签批**。

## 实施前咨询（oracle，2026-11-17，builder 阶段）

**结论：AC #1 的「lightweight」定义与本项 AC #4 都需 revise（plan_drift），不得按字面实施。**

### 新发现（有代码证据，立项时未覆盖）

**lightweight 模式今天不可归档 —— 它产出的是「幽灵分支」**：

| 环节 | 事实 |
|---|---|
| `phase2_execute.sh:117-119` | lightweight 分支只有 `EXEC_DIR="$PROJECT_ROOT"`，**不建任何分支**（全仓唯一建分支点是 `:84` 的 `git worktree add -b`） |
| `phase2_execute.sh:145` | 却把 `branch="openspec/<name>"` 写进 builder handoff —— **一个没有对应 ref 的声明** |
| `_lib/verifier/branch.py:17-27` | 取不到分支 ⇒ 返回 None（fail closed） |
| `rdd_verify_cmd.py:188-191` | ⇒ `halt_reason="openspec/<change> branch missing or detached"` |
| `archive_gate.py:259-264` | ⇒ `openspec/<change> branch missing`，**归档被拒** |
| 唯一出路 | `SKIP_RDD_VERIFIER=yes + RDDF_VERIFIER_BYPASS_REASON` ⇒ 每次 change 一条 bypass 审计（月度阈值 >3 WARNING / >6 CRITICAL） |

⇒ 若按 AC #4 让「tasks 2 条 + plan Files 2 个」走 lightweight，**本仓的小 change
将全部变成不可归档**（只能用审计旁路）⇒ 本项会把一个不可用的模式推给更多项目。

### 三处独立文本都指向「lightweight = 有分支、无 worktree」

- `_lib/schemas/config_schema.json:225`：`"force lightweight mode (**branch only**, no worktree)"`
- `complete-project-yaml-config-gaps/spec.md:211-212`：`"…proceed directly to lightweight **branch** execution"`
- `verifier-lifecycle/spec.md:120-125`（已采纳）：scenario「Lightweight current branch mismatch — GIVEN lightweight execution mode is active AND the current branch is not `openspec/<change>` THEN fail closed」⇒ **该 scenario 假定 lightweight 下当前分支就是 `openspec/<change>`**

⇒ **AC #1 的「无 worktree、无独立分支」是错的**（它把实现缺陷写成了契约）。正确契约是
「**有** `openspec/<change>` 分支、无 worktree」。修法：`phase2_execute.sh` 的 lightweight
分支补 `git checkout -b openspec/<change>`（必要时 `git branch` + 记录），并给
lightweight 归档路径补上「分支合入默认分支 + cleanup + iteration sync」——
否则提交停在分支上（那正是 `fix-worktree-archive-branch-merge` 描述的同类缺陷）。

### 另一处被立项漏掉的假陈述

`_lib/ship_execution_mode.sh:80` 的注释「Project.yaml git.openspec_tracked: false
**forces lightweight** (serial)」把两个维度粘在一句话里 —— 与 `config_schema.json:225`
是同型假陈述。行为（false ⇒ serial 波次）可以保留（该开关与「并发单位是否有分支隔离
凭据」事实相关），但**理由与措辞必须与 lightweight 解耦**。

### 退役面比立项列的多（4 处，非 1 处）

| 位置 | 内容 |
|---|---|
| `spec.md:202-217` | `guide-ship-phase-1-detect-lightweight`（立项已识别） |
| `spec.md:123-142` | `rddf-execution-mode-env-not-read-by-parse` 的 scenario「`guide-ship` Phase 1 SHALL `export RDDF_EXECUTION_MODE=serial`」 |
| `spec.md:299-302` | `zero-regression-backward-compat` 的 scenario「`guide-ship` Phase 1 SHALL proceed with normal worktree creation」 |
| `openspec/specs/archive-auto-commit/spec.md:85-95` | 「`guide-ship.md` Phase 3 lightweight mode MUST also call helper」 |

`skills/guide-ship/` 已被 v4 阶段合并硬删除（ADR-0043/0044/0048）⇒ 这些是**指向已删除
skill 的 normative 文本**。只退役一条会把病根留在原地。

**根因**：`skills/rdd-doctor/scripts/checks/v4_residue_check.py:46` 的扫描面是
`_SCAN_ROOTS = ("_lib", "skills")` ⇒ `openspec/specs/` 完全不在扫描面 ⇒ 已删除路径能在
已采纳 spec 里存活。建议把 `openspec/specs/`（**不含** `openspec/changes/archive/`）纳入
扫描并加一条「已删除路径出现在 normative 文本中」的规则。

### 工艺建议（oracle）

- retire 的做法是「**保留 Requirement header + 改写为负向断言**」
  （`git.openspec_tracked` SHALL NOT influence execution mode），**不是**真删：
  真删后未来读者 grep 不到约束，会把空白重新解读成「按 schema 应该是 lightweight」，
  同一个错误会以完全相同的方式复发。
- ADR 侧按本仓惯例给 ADR-0036 打补丁（状态行 `+ AMENDED (日期)` + `## Post-hoc Fix
  Record` 追加），**不改写原 Decision 9 正文**。
- spec delta 与 ADR amendment 必须在同一个 change 里。

### 需要 planner / architect 裁决的两点

1. **AC #1 定义**：改为「有 `openspec/<change>` 分支、无 worktree」。
2. **AC #4**：小 change 走 lightweight 的前提是 lightweight 可归档 ⇒ 需先立
   「lightweight 建分支 + 归档路径补齐（merge / cleanup / iteration sync）」的独立立项，
   或把该部分并入本项。**在它落地前，本项对「小改动」的诚实输出只能是
   fail-closed 到 worktree + reason 写明原因**。

---

## plan_drift 处置（2026-11-17，planner）

**来源**：builder 实施前的 oracle 咨询（记录见本文件「实施前咨询」节）暴露了两个**计划层**问题，按角色矩阵归 `plan_drift` ⇒ 由 planner 修订本立项，不在 builder 侧硬改。

### 问题 1：AC #1 的「lightweight」定义把实现缺陷当成了契约

原 AC 写「无 worktree、**无独立分支**、主仓当前分支实施」，但**五处既有文本**都说「有分支」：

| 出处 | 原文 |
|---|---|
| ADR-0024（Consequences） | 「小改动（≤2 文件，≤3 任务）直接在 **main repo 分支**工作，跳过 worktree 创建」 |
| ADR-0036（Decision 表） | 「false → 强制轻量模式（**branch-only**）」 |
| `_lib/schemas/config_schema.json` | 「force lightweight mode (**branch only**, no worktree)」 |
| `complete-project-yaml-config-gaps`（spec） | 「proceed directly to lightweight **branch** execution」 |
| `verifier-lifecycle`（已采纳 spec） | scenario「GIVEN lightweight is active AND the current branch is **not** `openspec/<change>` THEN fail closed」 |

⇒ 真正的契约是「**有分支、无 worktree**」；实现做成了「无分支」⇒ **幽灵分支**（handoff 写下 `branch="openspec/<name>"` 却没有对应 ref）⇒ lightwight 的 change 今天过不了归档门（`branch.py` 取不到分支 ⇒ fail closed ⇒ 只能靠审计旁路）。

⇒ **已修订**：AC #1 改为「有 `openspec/<change>` 分支、无 worktree」，并由 ADR-0036 的 2026-11-17 修订钉死（architect 签批）。

### 问题 2：AC #4 的「小改动 ⇒ lightweight」在当前实现下不安全

若按原 AC 让小改动走 lightweight ⇒ 本仓（本仓 `openspec_tracked: false` + P1.5 恒判 worktree）**所有小 change 会立刻变成不可归档**（幽灵分支 ⇒ 验证 fail closed ⇒ 只能走 `SKIP_RDD_VERIFIER` 审计旁路）。

⇒ **已修订**：AC #4 的第 1 条夹具断言**分段验收**：

| 阶段 | 条件 | `tasks.md` 2 条 + plan `Files:` 2 个 的判定 | `reason` |
|---|---|---|---|
| **现在** | `fix-lightweight-branch-and-archive` **未**落地 | `worktree` | 写明「lightweight 未落地（无实现分支 / 归档路径未补齐）」 |
| **之后** | 该立项落地 | `lightweight` | 真实输入值 |

⇒ 「诚实化」部分（AC #2/#3/#5/#6/#7/#8/#9/#12/#13）**不受此影响，可独立实施**；它们本来就是本项的首要意图（「P1.5 别再输出假话」）。

### 依赖与顺序

```
① fix-lightweight-branch-and-archive（新立项，本轮创建）
     └─ lightweight 建 openspec/<change> 分支 + 归档路径补齐（分支合入判定 / cleanup / iteration sync）
② fix-execution-mode-decision（本项）
     └─ 输入诚实化 + fail-closed（AC #2/#3/#5~#9/#12/#13）+ 三方一致性落地（AC #1/#10）
③ fix-worktree-archive-branch-merge（ADR-0061 的实现）
     └─ 合入门（worktree 路径）—— 与 ① 可并行（同改 _lib/archive.sh，建议串行落地）
```

⇒ **顺序约束**（architect 已写进 ADR-0036 的修订节）：② 的**语义部分**（spec 退役 + 描述修正）可先行；② 的**执行模式部分落地**（AC #4 第 1 条从「worktree」翻成「lightweight」）必须等 ①；而 ① 落地后本仓的执行模型才真正有 lightweight 可用。

### 立项状态

- 本项：AC #1 / #4 / #10 已按 architect 的签批结论修订；其余 AC 不变。**状态仍为 draft**（待实施）。
- 新立项：`fix-lightweight-branch-and-archive`（5 段草稿，metis 1 轮审稿）。
- 关联 architect 产物：`docs/adr/ADR-0036-rddf-project-yaml-config.md`（AMENDED）、`docs/adr/ADR-0061-archive-gate-refuses-unmerged-branch.md`（已采纳）。
