# ADR-0036: .rddf/project.yaml 项目级配置源

> **状态**: 已采纳 (2026-09-02) + AMENDED (2026-11-17)
> **日期**: 2026-09-02
> **决策者**: rdd-workflow maintainers
> **关联**: [proposal rfc-rddf-project-yaml-config-i10](../../.rddf/improvements/rfc-rddf-project-yaml-config-i10.md) · [issue #10](https://github.com/chisuhua/rdd-workflow/issues/10)
> **审稿报告**: `.rddf/reviews/adr-0036-amendment-2026-11-17.md`（2026-11-17 修订的 oracle + critic 双审）· `.rddf/reviews/adr-0036-amendment-2026-11-18.md`（2026-11-18 事实追注的 oracle + critic 双审）

## Context

rdd-workflow 当前 5 优先级配置链 `runtime > loop.yaml > .rddf.json > env vars > defaults` 缺少一个**项目级持久化层**，导致 4 类硬编码假设阻碍异构项目接入：

1. ADR 编号固定 4 位 (`_lib/adr_catalog.py:13`)
2. openspec/ 强制 git-tracked（worktree/archive 流程前提）
3. AC 验证强制 LLM（无 API key 或硬件项目无法复用）
4. 配置只支持 env var（每次 shell 手动 export，CI 注入繁琐）

首个受影响项目是 **ChipForge**（CppTLM+CppHDL 硬件验证平台），它使用 3 位 ADR 编号（`ADR-040`）且 commit 3e8fdbf 显式 untrack `openspec/`。

## Decision

引入 **`.rddf/project.yaml`** 作为单一权威项目级配置源，统一上述可配项。完整向后兼容（缺失时行为 = 现状）。

**优先级链扩展**：

```
runtime_overrides > project.yaml > loop.yaml > env vars > .rddf.json > defaults
```

**核心字段**：

| 字段 | 默认 | 作用 |
|------|------|------|
| `adr.pattern` | `^ADR-(\d{4})-.*\.md$` | ADR 编号正则（支持 3 位/4 位） |
| `adr.glob` | `ADR-*.md` | Shell glob（与 pattern 语义等价） |
| `git.openspec_tracked` | `true` | false → 强制轻量模式（branch-only）<br>（2026-11-17 修订：本行的语义已被下方「修订 2026-11-17」节取代 —— 该开关只属于**归档路径**维度，不再强制执行模式；以该节为准。） |
| `verification.provider` | `llm` | hook → 调外部 `tools/verify_change.sh` |

**加载机制**：

- Python 端：`ConfigParser.project_yaml` + `_load_project_yaml()` 集成到 `parse()` merge 链
- Bash 端：`_lib/project_config.sh::project_yaml_get` 通过 env-var 模式调用 Python subprocess（Oracle C1 防注入）
- Schema：`_lib/schemas/config_schema.json` 新增 `project` 节，jsonschema 强校验（fail-closed）

**防御式约束**：

- project.yaml 缺失时**零影响**（`_load_project_yaml` 返回 `{}`）
- 字段类型错误 raise `ConfigError`（不静默 fallback）
- 保留 env var 覆盖能力（CI 临时注入仍可用）
- 不强制现有项目迁移

### 修订 2026-11-17（`git.openspec_tracked` 的维度归属 + `lightweight` 的定义）

**触发**：2026-11-17 的实施前审查发现该开关在**三方**说法不一致 —— schema 描述、已采纳 spec 的 normative Requirement、以及实现 —— 三方各说各话，且实现里 P1.5 写进 handoff 的 `reason` 是**占位常量**编出来的（`task_count = 5` 硬编码 ⇒ `tasks > 3` 恒真 ⇒ `lightweight` 分支不可达）。审查同时发现一处更硬的矛盾：**`lightweight` 模式今天产出的是「幽灵分支」**（不建任何分支，却在 handoff 里写下 `branch="openspec/<name>"`），而归档门与验证器都按「分支 tip」取锚点 ⇒ **lightweight 模式的 change 不可归档**。

**决策**（修订本 ADR 的 Decision 表中 `git.openspec_tracked` 那一行与 Decision 4）：

1. **`lightweight` 的定义钉死为「主仓的 `openspec/<change>` 分支 + 无 worktree」。**
   五处既有文本本就一致 —— ADR-0024「小改动（≤2 文件，≤3 任务）直接在 **main repo 分支**工作，跳过 worktree 创建」、本 ADR Decision 表「false → 强制轻量模式（**branch-only**）」、`config_schema.json`「force lightweight mode (**branch only**, no worktree)」、spec「proceed directly to lightweight **branch** execution」、以及已采纳 spec `verifier-lifecycle` 的 scenario「GIVEN lightweight execution mode is active AND the current branch is **not** `openspec/<change>` THEN fail closed」（该 scenario 只有在 lightweight 下当前分支**就是** `openspec/<change>` 时才可能被满足）—— 而**实现**做成了「无分支、无 worktree」。⇒ 本次修订把「有分支」写进契约：**实现的现状是缺陷，不是契约**。

2. **`git.openspec_tracked` 只属于「归档路径」维度，不再属于「执行模式」维度。**
   - 保留：false ⇒ 归档不执行 `git merge` 与 `commit_archive_moves`（openspec/ 未跟踪 ⇒ 没有东西可 commit；这条与开关的**事实**义直接相关）。
   - 撤销：false ⇒ 强制 lightweight。**理由**：该子句的原始动机是「openspec/ 未被跟踪 ⇒ worktree 里拿不到 `openspec/changes/<name>/` ⇒ worktree 模式不可用」；而 v4 阶段的 artifact 复制（`phase2_execute.sh` 把 `openspec/changes/<name>` 与 `.rddf/plans/<name>.md` 带进 worktree）**已经消除了这个机械动机**（须打折：复制只覆盖 change 自身的 artifacts，worktree 内仍没有 `openspec/specs/**` 等已采纳 capability spec —— 这不影响「worktree 能不能跑一个 change」的判断，但不要写成「worktree 不可用问题已完全消除」）⇒ 该子句在实现上从未落地（M3 的实施记录只覆盖了归档路径那半），在 v4 阶段合并删除 `skills/guide-ship/` 时连同它的实现一起消失 ⇒ 继续保留它等于让配置面承诺一件**技术上已无必要**的事。
   - **跨 ADR 的依赖（必须写明）**：撤销该子句也是 **ADR-0061 的合入门在本仓仍然生效的前提** —— 本仓 `openspec_tracked: false`，若改为强制 lightweight，全部 change 会离开 worktree 路径，而 ADR-0061 的门恰好只存在于 worktree 路径（`archive_change`）⇒ 撤销子句 = 保住门的覆盖面。
   - **依赖顺序与过渡态**：撤销子句的**收益**（合入门能生效）要等到 ADR-0061 落地；**在 ADR-0061 落地之前**，本仓既没有 lightweight、也**仍无任何合入判定**（即 ADR-0061 Context 描述的静默失败原样保留）⇒ 因此实施顺序必须是「ADR-0061 先落地（或至少先 Accepted 并进入实施）」，本修订的**语义部分**（spec 退役 + 描述修正）可先行，**执行模式部分的落地**（V-G 解除）必须等 ADR-0061。
   - 保留并改写理由：`openspec_tracked=false ⇒ 波次模式默认 serial` —— 这是**波次并发维度**的判断（并发单位缺少分支隔离凭据 ⇒ 保守串行），与执行模式无关；`_lib/ship_execution_mode.sh` 的注释措辞必须随之改写（它把两个维度粘在一句话里，是与 schema 描述同型的假陈述）。
   - ⇒ 执行模式**只**由 ADR-0024 的输入维度 + fail-closed 规则决定（输入不可得 ⇒ worktree），与本开关无关。

3. **退役指向已删除 skill 的 normative 文本（按残留类型分型，不一刀切）。**
   `skills/guide-ship/` 已随 v4 阶段合并被硬删除（ADR-0043 / ADR-0044 / ADR-0048），而下列已采纳 spec 文本仍以它为主体 ⇒ 变成「指向不存在的东西的规范」：

   | 残留 | 位置 | 性质 | 处置 |
|---|---|---|---|
| R1 | `complete-project-yaml-config-gaps/spec.md` **:202-:217**（标题 :202（**豁免**）、正文 :204、Scenario 1 `:206-:212`、Scenario 2 `:214-:217`） | **假义务**（承诺一个从无必要的强制行为） | **标题保留**（历史标识，供 grep 定位）+ **正文与 2 个 Scenario 一并改写为负向断言**：「`git.openspec_tracked` SHALL NOT determine the execution mode（worktree vs lightweight）」—— ⚠ 断言**必须带维度限定**：同文件未被改写的 Requirement `ship-execution-mode-project-yaml-priority`（`:219-:245`）把 “execution mode” 用于 serial/parallel **波次**维度并断言该开关参与其优先级 ⇒ 不加限定则两句对同一开关给出字面相反的约束。该 spec 侧的术语归 `fix-execution-mode-decision` 的 AC「`ship_execution_mode.sh` 的 `serial` 被改名为波次维度」一并收敛（spec 侧未列该 AC，实施时须补）⇒ 被撤销的断言**全部退役**：强制轻量提示（:209）、`RDDF_EXECUTION_MODE=lightweight`（:210）、跳过 worktree 创建（:211）、直走 lightweight branch（:212）、Scenario 2 的「SHALL NOT modify `RDDF_EXECUTION_MODE`」（:216，引用已退役变量）与「SHALL proceed with normal worktree creation flow」（:217，把「开关 ⇒ 走 worktree」写成义务） |
| R2 | `complete-project-yaml-config-gaps/spec.md` **:125**（Requirement 正文「The env var (when set by `guide-ship` Phase 1) is a downstream signal only」= Decision 9 的「输出」定位）+ **:139-:142**（Scenario「Phase 1 SHALL `export RDDF_EXECUTION_MODE=serial`」及其第 4 行「the env var SHALL NOT be read by `parse_execution_mode` (per Decision 9)」） | **僵尸变量**（该 env 全仓 0 个读取点） | **退役该变量**（连同 ADR-0036 的 Decision 9 的「输出」定位一并退役），而不是把「SHALL NOT export」写进契约 —— 那会把僵尸变量钉进规范。⇒ **:125 与 :139-:142 全部处置**：Requirement 正文与 Scenario 的断言一并退役 |
| R3 | `complete-project-yaml-config-gaps/spec.md` **:301**（Scenario「Phase 1 SHALL proceed with normal worktree creation」） | **假义务**（指向已删除 skill 的 Phase 1） | 随 R1 一并改写 |
| R4 | `archive-auto-commit/spec.md` **:85**（Requirement 标题）、**:88**（正文） | **仍然活着的义务**（今天仍然红：`phase3_archive.sh` 的 lightweight inline 分支确实没调 `commit_archive_moves`） | **标题与正文一并正向重指向**为「`rdd-builder` P3 lightweight 路径 MUST 调用 `commit_archive_moves`」—— **不得**改成负向断言：把一条红着的义务改成「不需要做」就是免掉它。**主责在 ADR-0061**（它带该 spec 的 delta 与测试改造）；本修订只登记处置方向，不重复写 delta |
| R5 | `archive-gate-verification/spec.md` **:8,:10,:13,:16,:17,:21,:78,:85,:135** | **owner 归属**（把 merge/archive/cleanup 的归属写在 guide-ship 名下） | **标题与正文一并重指向**为 `rdd-builder` |
| R6 | `worktree-context-persistence/spec.md` **:8**（Requirement 1 正文）**及其 3 个 Scenario :14 / :20 / :25** | **指向已删除路径的 MUST** | **整体收窄为 execute-only**：目标只剩 `skills/execute/SKILL.md`、**删除「Phase 1 / Phase 2 段」限定词**、3 个 Scenario 的断言同步收窄（**保留 Scenario 结构** —— openspec 要求每个 Requirement 至少 1 个 `#### Scenario:`）；**Scenario 3 的 WHEN 重指向** `tests/integration/test_worktree_context_persistence.bats` |
| R7 | `verifier-lifecycle/spec.md` **:163**（路由 Requirement 正文）、**:151 / :157**（owner 场景）、**:169 / :175**（路由断言） | **指向已退役 stage 的路由名 / owner** | **正文与断言一并重指向**为 `rdd-builder` / `rdd-planner`（v4 的对应 stage） |
| R8 | `archive-iteration-sync/spec.md` **:8** | **指向已删除路径的 MUST** | 重指向为 `_lib/archive.sh::mark_iteration_archived`（实际实现所在） |
| R9 | `spec-validation-gates/spec.md` **:172**（Requirement 标题）、**:174**（正文）、**:183 / :191**（Scenario） | **指向已删除路径的 MUST** | **标题与正文一并重指向**为 `skills/rdd-builder/scripts/phase3_archive.sh` |
| R10 | `skill-role-model/spec.md` **:10**、`docs-v4-sync-scope-followup/spec.md` **:42** | **次级引用**（非 owner 声明） | 随所属 spec 的同步一并处理；列入 V-C 判定范围 |

   **R6 的取舍（必须写明，否则重指向会造出一条假的红 MUST）**：`Worktree Context Rule` 这段文字今天**只存在于** `skills/execute/SKILL.md:84`（`skills/rdd-builder/SKILL.md` 里没有）⇒ 若把 MUST 的两半都重指向到 `rdd-builder`，该 MUST 立即为假且无人验证。⇒ **收窄为仅 `skills/execute/SKILL.md`，并删除「Phase 1 / Phase 2 段」限定词**（`skills/execute/SKILL.md` 没有 Phase 1/Phase 2 分段 —— 规则在 `:84` 的 `### Worktree Context Rule` 标题下，其后是 `## 执行步骤`（h2）/ `### Step 1…`；保留段落限定词会让收窄后的 MUST 仍为假）。收窄后的 Requirement = 「`skills/execute/SKILL.md` 含一段 Worktree Context Rule（**不限段落**）」—— 该形态今天为真，且有既存 green 测试守着（`tests/integration/test_worktree_context_persistence.bats:24-27` 断言标题串）。
   **R6 的处置必须覆盖 Requirement 1 的 3 个 Scenario**（`:14`「`guide-ship/SKILL.md` 含锚点」、`:20`「两个 SKILL.md 均含 `跨 worktree 切换显式 cd` 锚点」、`:25`「2 个 SKILL.md 锚点全部匹配」）—— 只改正文会残留 3 条指向已删除路径的假 MUST；而整体替换又会让 Requirement 不含任何 `#### Scenario:`（openspec 校验要求每个 Requirement 至少一个 Scenario）⇒ **做法：正文与 3 个 Scenario 一并收窄为 execute-only，Scenario 结构保留**。
   **builder 侧的散文义务为何不需要**：v4 的 worktree 上下文由**代码通道**承接 —— `phase2_execute.sh` 把 `worktree_path` / `branch` 写进 builder handoff，`skills/execute/scripts/select_worktree.sh` 解析工作区（其 `RDDF_EXECUTION_ROOT` 输入**今天没有生产者**，v4 合并时随 `setup_execution_workspace` 一起消失 ⇒ 实际走的是它自己的 worktree 探测分支）⇒ builder 不需要再写一段规则文本，execute 侧的注入点保留原文即可。

   **退役写法（R1/R3）**：保留 Requirement 标题，改写正文为负向断言。**不采用真删** —— 删掉后未来读者 grep 不到任何约束，会把「空白」重新解读成「按 schema 应该是 lightweight」，同一个错误会以完全相同的方式复发；一句可测试的 `SHALL NOT` 是可证伪的，空白不是。
   **R4 不适用该写法**（见表格）。

4. **前置条件：lightweight 必须能走完归档。**
   本次修订把 lightweight 定义为「有分支」，但**当前实现不建分支** ⇒ lightweight 的 change 无法通过验证锚点与归档门。⇒ 「lightweight 建 `openspec/<change>` 分支 + 归档路径补齐（分支合入 / cleanup / iteration sync）」**单独立项**，且作为「P1.5 输入诚实化」的前置 —— 在它落地前，执行模式判定对小改动的诚实输出只能是 **fail-closed 到 worktree + reason 写明原因**。

**影响范围**：`config_schema.json` 的 `git.openspec_tracked` 描述；**`README.md:87` 与 `README.md:100`**（用户可见面：「强制轻量模式（无 worktree）」「false → 强制轻量模式 + archive 不产生 git commit」两行与撤销后的决策直接矛盾）；上表 R1~R10 的 spec 文本；**`docs/architecture/gates-and-quality.md`**（门清单需区分「AC 归档门」与「合入门」）；`_lib/ship_execution_mode.sh` 的注释与函数命名（波次维度与执行模式维度解耦）；`_lib/builder_deps.py` 的输入计算与 `phase1_5_deps.sh` 的接线；`skills/rdd-builder/SKILL.md` 与 `docs/architecture/workflow-phases.md` 的执行模式契约段落；**`docs/adr/README.md`（ADR 索引）** —— 本 ADR 的 Status 行变更与新增 ADR-0061 都会改动索引，必须用 `_lib/adr_index_generator.py --write docs/adr/README.md` 重建并跑 `tests/unit/test_adr_index_gate.py`。

**机器证据（供三方一致性核对）**：`git.openspec_tracked` 的**读者全部落在三个维度**上 —— `_lib/archive.sh`（**归档路径**）、`_lib/ship_execution_mode.sh`（**波次维度**）、`_lib/env_checks.sh` + `skills/rdd-doctor/scripts/checks/gitignore_check.py`（**gitignore 一致性**）；**执行模式判定路径（`_lib/builder_deps.py` / `phase1_5_deps.sh`）上没有任何读者** ⇒ 「该开关不进入执行模式维度」与实现一致，可作为「三方一致性」的机器可读依据。

#### 备选方案

| 备选 | 结论 | 理由 |
|---|---|---|
| A. 补实现「false ⇒ 强制 lightweight」（即按本 ADR 原 Decision 表执行） | **拒绝** | 硬证据链：`phase3_archive.sh` 的 lightweight inline 分支**无 cleanup、无 iteration 同步**（文件自认 KNOWN GAP）+ `_lib/verifier/branch.py` 取不到分支即 fail closed ⇒ **lightweight 产出的 change 今天过不了归档门**。对本仓（`openspec_tracked: false`）实现 A ⇒ 全部 change 走 lightweight ⇒ 全部 change 都需要「审计旁路 + 手工 merge + 手工 cleanup」⇒ 把一个缺陷推广到全部 change；且本仓会离开 ADR-0061 的门唯一存在的路径（worktree 模式）⇒ 覆盖面同时归零 |
| B. 保留子句但只打印提示（不改变行为） | **拒绝** | 用文案伪造状态，比不写更坏：下一个审计会以为已实现（本次病灶正是「勾了就算做了」） |
| C. 退役子句并把 `lightweight` 定义钉死为「有分支、无 worktree」（本次决策） | **接受** | 让契约与四处既有文本一致；把执行模式的决定权交还给 ADR-0024 的输入维度 + fail-closed；负向断言可被机器与 reviewer 检验 |
| D. 把 `git.openspec_tracked` 拆成两个独立开关（`archive` / `execution_mode`） | **拒绝（当前）** | 技术上可行，但新开关能选到的 lightweight 仍不可归档 ⇒ 只是把同一个坑包装得更好看；等 lightweight 真正可归档后再评估 |
| E. 保持现状不动 | **拒绝** | 三方不一致持续；P1.5 继续输出编造的 `reason`；轻量路径的幽灵分支缺陷继续隐藏 |

**AC 映射**：`fix-execution-mode-decision` 的 AC「三方一致性」「`lightweight` 的定义被写成一份契约」「`ship_execution_mode.sh` 的 `serial` 被改名为波次维度」「输入不可得 ⇒ fail-closed」由本修订承接；该立项的「输入计算 / reason 诚实化 / 冲突维度 / `LEGACY_EXEC_MODE`」等实施类 AC 由 `fix-execution-mode-decision` 的实施阶段承接。本修订的 V-G（lightweight 未落地前不得输出 lightweight）对应立项 AC「夹具断言」的前置条件。

**后果 / 代价（本次修订）**：

- **正面**：配置面与规范面不再承诺「false ⇒ 强制 lightweight」这件技术上已无必要的事；执行模式的决定权回到 ADR-0024 的输入维度 + fail-closed；`lightweight` 的定义与四处既有文本对齐（实现可据此对齐，而不是各写各的）；指向已删除 skill 的规范文本被清掉（否则下一个按规范施工的人会在**完全合规**的前提下重新引入旧行为）。
- **负面 / 代价**：
  - **本仓（`openspec_tracked: false`）此后全部 change 走 worktree 模式** —— 撤销子句的直接运行后果：worktree 的开销（小改动也要建 worktree + 复制 artifacts）回来。⇒ 这是**用开销换诚实**：在 lightweight 具备可归档性之前，「便宜的模式」是一个不可用的模式。
  - **spec 退役对外部读者的兼容影响**：R1~R10 涉及的 9 份已采纳 capability spec 需要各自的 delta 与签批（不是一次批量改写）；本次只**决定**处置方式，不代替实施。
  - **V-C 允许清单的长期维护成本**：分类允许清单（历史枚举值 / 提案名 / 反漂移守卫自身 / 归档历史）需要随新的残留类型扩充 ⇒ 靠 `v4_residue_check` 的扫描面扩展（V-H）持续维护，否则分类清单会腐化。
  - **形态债不在本修订范围**：本 ADR 正文仍带 `## Implementation` 与 `## Post-hoc Fix Record` 两个标题（ADR-0060 同日修订点名的「越界成实施细节 / 过程日志」标题族）—— 按 ADR-0060 的「存量不追溯」原则**不在本次改动**（避免在一次语义修订里顺手重排一份已签批 ADR 的骨架）。
- **回滚路径**：本次修订只改**规范文本与描述**（不改代码行为）⇒ 回滚 = 恢复 Decision 表那一行与 R1~R10 的原文 + 回退 spec delta；无数据迁移、无状态格式变化。

**后续待办（本次修订之外）**：

- [ ] **backlog（独立立项，量化口径已测）**：`openspec/specs/**` 的**全局**退役 stage 残余清理。**实测口径**：normative 段（`### Requirement` / `#### Scenario` 及其正文）对 `guide-ship|guide-plan|guide-arch|guide-design|guide-spec` 的引用共 **204 处 / 47 份 spec**。**分类规则**（命中即算合法、不需处置）：① 退役 stage 的历史枚举值；② 提案名；③ 反漂移守卫自身；④ 归档历史。**其余为待处置残余**，需要逐 spec 的 delta 与签批 ⇒ 不在本修订范围内（V-C 的判定对象已明确收窄为 R1~R10 的位置级枚举集合）。
  - **已被点名、必须在该 backlog 里逐条处置的位置**（示例，非全集；**不含** R 表已覆盖的位置）：`worktree-context-persistence/spec.md` **:46 / :51 / :57**（Requirement 3 —— 断言一个**不存在的**测试文件 `tests/unit/test_worktree_context_rule_docs.py` 与错误的用例数（说 4 个、实际 3 个）⇒ 今天为假）、`skill-role-model/spec.md` **:157**（「All 4 phase SKILL.md files (`guide-arch`,`guide-design`,`guide-plan`,`guide-ship`) MUST have the same `role:` field」= 指向 4 个已删除路径的假 MUST）、`spec-validation-gates/spec.md` **:149 / :151 / :158 / :167**（`guide-plan` Requirement）、`ship-done-orphan-cleanup/spec.md`、`rfc-rddf-project-yaml-config-i10/spec.md`、`doc-truth-sync/spec.md`、`iterative-plan-fill/spec.md`、`skeleton-planning/spec.md`、`post-archive-cleanup-hook/spec.md`、`inline-ac-verifier-into-rdd-verifier/spec.md`、`workflow-design-phase/spec.md`。
  - **可复算口径**（让上面的数字可被第三方复验）：`python3 - <<'PY'` 扫描 `openspec/specs/*/spec.md`，取 `### Requirement` / `#### Scenario` 及其正文，统计命中 `guide-ship|guide-plan|guide-arch|guide-design|guide-spec` 的行数与文件数 ⇒ 实测 **204 处 / 47 份 spec**（行级全量口径为 232 行 / 48 份，含 Purpose 等非 normative 行）。
- [ ] **backlog**：`skills/execute/SKILL.md:57-59` 的假陈述（「执行环境由 rdd-builder 通过 `$RDDF_EXECUTION_ROOT` 决定 … execute 仅消费该环境变量,不再自行探测工作区」）—— `RDDF_EXECUTION_ROOT` 今天**没有生产者**（`setup_execution_workspace` **无存活实现**，仅存于 `.rddf/plans/**` 与 `docs/superpowers/plans/**` 的历史计划文档），而同文件 `:64-76` 的 `auto_detect_worktree_context` 证明 execute 自己探测 ⇒ 该陈述与事实相反。
- [ ] **backlog**：`README.md:129` 仍写「`rdd-builder::setup_execution_workspace` 通过 `$RDDF_EXECULATION_ROOT` …」（该函数全仓零命中）—— 文档漂移，**超出本次修订声明的 `README.md:87/:100` 范围**，只记不改。

**验证判据**：见下方 `## Verification` 章（h2 级，前瞻方法，非实测日志）。

### 修订 2026-11-18（事实追注：lightweight 已可归档 —— 决策未变）

**本节只纠正事实前提，不改任何决策。** 上文（2026-11-17 修订）以「lightweight 不可用」为前提；该前提已由
`fix-lightweight-branch-and-archive`（2026-11-18 实施并验收：实施记录见
`.rddf/improvements/fix-lightweight-branch-and-archive.md`，取证见
`.rddf/reviews/fix-lightweight-branch-and-archive-verify.md`）改变。

**前提已失效的陈述**（原文一律保留作历史论证，读者以本节为准；位置列是当时的行号）：

| # | 位置 | 原文要点 | 2026-11-18 的事实 |
|---|---|---|---|
| 1 | Decision §4 前置条件（`:93`） | 「**当前实现不建分支** ⇒ lightweight 的 change 无法通过验证锚点与归档门」 | P2 现建 `openspec/<change>`（起点 = 默认分支 tip，三档政策：建 / 复用 / fail-closed）；P3 走 9 步枚举式归档 |
| 2 | 备选方案 A 行（`:103`） | 拒绝 A 的证据链末句「**lightweight 产出的 change 今天过不了归档门**」 | 证据链**两半均已消失**：① `phase3_archive.sh` 不再缺 cleanup / iteration 同步（九步齐全）；② 分支真的存在 ⇒ `_lib/verifier/branch.py` 能取到锚点 |
| 3 | 备选方案 D 行（`:106`） | 「**等 lightweight 真正可归档后再评估**」 | 条件已满足 ⇒ D **可重新评估**（本次不评估，见下） |
| 4 | Consequences（`:115`） | 「本仓（`openspec_tracked: false`）**此后全部 change 走 worktree 模式**」/「用开销换诚实」 | 不再由本 ADR 强制：`openspec_tracked` 仍**不驱动**执行模式，但执行模式判定已能按 ADR-0024 的输入正常输出 `lightweight` |
| 5 | 修订 2026-11-17 · 决策 2「跨 ADR 的依赖」bullet（`:64`） | 「ADR-0061 的门**恰好只存在于 worktree 路径**（`archive_change`）」 | 门现在有两个调用点：lightweight 在 `phase3_archive.sh:236` 复用同一 `archive_premerge_check`（`wt_path` 传空）⇒ 该 bullet 的**结论**（撤销子句保住覆盖面）反而更强，但「只存在于 worktree」已不成立 |
| 6 | 修订 2026-11-17 · 决策 2「依赖顺序与过渡态」bullet（`:65`） | 「**在 ADR-0061 落地之前**，本仓既没有 lightweight、也仍无任何合入判定」 | 该 bullet 是**过渡态**描述，条件已满足（ADR-0061 已采纳 + lightweight 已可归档）⇒ 读者不应再把它当作当前状态 |
| 7 | `## Verification` 的 **V-G** 条目括注 | 「（ADR-0061 的门**只存在于 worktree 路径**）」 | 与第 5 行同一句失效断言，出现在**验收章**里（只读 Verification 章、不读本节的 reviewer 会读到它）⇒ 门的调用点现在有两个；V-G 的其余内容（两件事未落地前不得输出 lightweight）由本节「V-G 状态」段处理 |

**V-G 状态**：V-G（`## Verification` 的 V-G 条目：「两件事都落地前不得输出 `lightweight`」）的前提**已满足**
⇒ 义务**解除**。机器证据：`_lib/builder_deps.py::LIGHTWEIGHT_EXECUTION_READY = True`（回滚 = 改回
`False`）。条目文本保留、**不加勾** —— 它是**过渡期闸门**而非持久验收项，`- [x]` 会把过渡义务误标成
「已验收」，而该章自身声明是「前瞻方法，非实测日志」。

**决策未变（逐条）**：

1. `git.openspec_tracked` **仍不进入**执行模式维度（本 ADR 的核心决策）；`RDDF_EXECUTION_MODE` 仍退役；
2. **备选 A 仍被拒绝** —— 拒绝理由独立于 lightweight 的可用性（依据见修订 2026-11-17 · 决策 2：机械
   动机已被 v4 的 artifact 复制消除、该子句在实现上从未落地、继续保留等于让配置面承诺一件技术上已无
   必要的事）：该开关的语义只属于**归档路径**与**波次并发维度**（后者即保留的「`false` ⇒ 波次默认
   serial」子句），「三方一致性」的目标不是「让 `false` 驱动执行模式」；
3. **备选 D 仍被拒绝（当前）** —— 拆分开关的技术前提虽已具备，但**本次不评估**：它是一个新决策，
   需独立立项 + 双审；本节只登记「前提已具备」；
4. **B / E 仍被拒绝**，**C（2026-11-17 的接受项）不变**。

**范围（可数）**：本节是**增补** —— 不改 Decision 表、不改选项对比表任何一行、不改 `## Consequences`
正文、不改 Status 行（避免元数据头膨胀）。要**改写**上表七处原文，须另立一次带双审的修订
（**尚未立项**：立项与 AC 由 planner 承接）。`AC 映射` 句（`:109`）对 V-G 的转述不单列 —— 它不是
事实断言，且已由「V-G 状态」段覆盖。

## Consequences

**正面**：

- 异构项目（硬件验证、嵌入式、文档驱动）原生接入
- ADR 编号灵活（3 位/4 位/混合）
- 工作区可不被 git 追踪（轻量模式）
- 外部验证 hook 可与 CTest 等测试框架组合
- 配置可团队共享（git tracked，schema 校验）

**负面 / 风险**：

- `_lib/config.py` merge 顺序全局影响（M1 标为 🔴 高风险）— 需保留 17 个 schema 文件顶层 version const v1，破坏兼容性即触发全量回归门
- `archive.sh::archive_change()` 新增分支（`openspec_tracked=false` 跳过 git 操作）— 任何错误会破坏现有归档路径
- hook runner path-traversal 风险— 必须强制路径白名单 `{project_root}/tools/`
- 文档可能漂移（README/USAGE 与新字段同步）

## Implementation

按提案分 5 个里程碑实施（详见 `.rddf/plans/rfc-rddf-project-yaml-config-i10.md`）：

| M | 内容 | 状态 |
|---|------|------|
| M1 | 配置基础设施（project_config.sh + config.py merge + schema + defaults） | ✅ 已实施 |
| M2 | ADR 发现可配置（pattern 参数化） | ✅ 部分实施（2/6 task） |
| M3 | openspec_tracked / 轻量模式（archive.sh 分支 + commit_archive_moves 守卫） | ✅ 已实施（per `fix-archive-openspec-tracked-commit`, 2026-09-10）—— ⚠ 2026-11-17 修订：**只有归档路径那半落地**；「强制轻量模式」那半从未实施（见「修订 2026-11-17」节） |
| M4 | verification hook（hook_runner.py） | ✅ 已实施 |
| M5 | 文档 + 全量测试 + ADR（本 ADR） | ✅ 已实施 |

## Verification

> 本次修订（2026-11-17）的**前瞻**判据；不是实测日志。

- [ ] **V-A** `config_schema.json` 的 `git.openspec_tracked` 描述**不含** `lightweight` 子串，且只描述归档路径语义；`README.md:87` / `README.md:100` 的同义表述同步修正（用户可见面与 schema 不得各说各话）。
- [ ] **V-B** 固定三输入下，`project.yaml` 的 `openspec_tracked` 取 `true` 与 `false` 时，`decide_execution_mode` 的输出**逐字节相同**（含 `reason`）⇒ 机器可读地证明「该开关不进入执行模式维度」。
- [ ] **V-C** **R 表「位置」列所列的每一处**都已被处置（改写 / 重指向 / 收窄），且这些位置的**正文 / 断言文本**中不再有以 guide-ship / guide-plan 为当前 owner 或当前路径的表述。
  - **判定对象是「位置」而不是「spec」**：R 表的「位置」列是有限的位置级集合 ⇒ 实施方逐条核对即可判定通过与否，不存在「这份 spec 里还有没有别处」的歧义。
  - **历史标识豁免**：R1 按上表**保留**的 Requirement 标题（`guide-ship-phase-1-detect-lightweight`）属供 `grep` 定位的历史标识，**不计入本条判定**；判定对象是该位置的**正文 / 断言文本**。R4 / R5 / R9 的**标题与正文一并改写**（它们不是历史标识，而是对当前 owner 的断言）；R2 的处置是**退役变量**（其 Requirement 正文 :125 与 Scenario :139-:142 一并退役，标题无须改写）。
  - **判定宽度 = 处置宽度**（按行分两类，避免实施方二义）：
    - 对**点名 Requirement 的行**（R1 / R2 / R4）：判定范围 = 该 Requirement 的**全部 normative 行**（正文 + 全部 Scenario）⇒ 只改正文而把 Scenario 留在已采纳 spec 里**不能**算作已处置（否则「R1 已处置」可被平凡满足，而被撤销的断言仍留在规范里）。
    - 对**只点名单个位置的行**（R3 / R8 / R10）：判定范围 = 枚举位置本身。
    - **R2 的范围裁定**：`rddf-execution-mode-env-not-read-by-parse` 的其余 Scenario（`:127-:132`、`:134-:137`）虽点名 `RDDF_EXECUTION_MODE`，但断言的是「`parse_execution_mode` **不读**该变量」这一**负向保证**，今天仍然为真 ⇒ **不是假义务，不在处置范围内**（处置只针对「Phase 1 导出该变量」这一侧的 `:125` + `:139-:142`）。
  - **`openspec/specs/**` 的全局残余面不属于本 ADR 的验收范围**：实测 normative 段（`### Requirement` / `#### Scenario` 及其正文）里对退役 stage 的引用共 **204 处 / 47 份 spec**，其中合法引用有 4 类（退役 stage 的历史枚举值、提案名、反漂移守卫自身、归档历史），其余是待处置残余 ⇒ 全局清理需要逐 spec 的 delta 与签批，作为**独立 backlog 项**（见「后续待办」，附实测口径与分类规则），不在本 ADR 里冒充验收项。
  - 判据的机器形态 = 「对**枚举清单逐条核对**」，**不是** `grep` 命中数归零（`grep` 口径永远红）。
- [ ] **V-D** R4（`archive-auto-commit` 的 lightweight MUST）被**正向重指向**为 `rdd-builder` P3，而不是被改成负向断言。
- [ ] **V-E** `skills/rdd-builder/SKILL.md` 与 `docs/architecture/workflow-phases.md` 写明执行模式契约：`lightweight` = 主仓 `openspec/<change>` 分支 + 无 worktree；`worktree` = 独立 worktree + 同名分支。
- [ ] **V-F** `_lib/ship_execution_mode.sh` 的注释不再出现「forces lightweight」措辞；`false ⇒ serial` 的行为与其既有测试不变。
- [ ] **V-G** **在「lightweight 建 `openspec/<change>` 分支」与「lightweight 归档路径补齐（含分支合入 / cleanup / iteration sync）」两件事都落地前**，`decide_execution_mode` **不得**输出 `mode=lightweight`（有对应单测：占位常量 `task_count = 5` 被替换成真实输入后，该断言仍成立）⇒ 否则「幽灵分支」缺陷会当场复活，且被合法化的模式上没有任何合入判定（ADR-0061 的门只存在于 worktree 路径）。
- [ ] **V-H** `v4_residue_check` 的扫描面包含 `openspec/specs/`（**不含** `openspec/changes/archive/`），且能按 backlog 第 1 项的 4 类分类规则报出「已删除路径出现在 normative 文本中」。
- [ ] **V-I** `docs/adr/README.md` 已用 `_lib/adr_index_generator.py --write docs/adr/README.md` 重建，`tests/unit/test_adr_index_gate.py` 通过（Status 行变更与新增 ADR 都会改动索引）。

## References

- ADR-0016 (发现契约) — `_lib/discover-arch-artifacts.sh` Path 1.5 接入 project.yaml
- ADR-0025 (design 阶段独立化) — 本提案从 arch 阶段迁移到 design 阶段审批
- ADR-0029 (issue-driven proposal) — 本提案通过 `add-improve --from-issue #10` 创建
- ADR-0030 (Hub-Spoke 联邦) — `verification.provider=hook` 不影响 Hub 上行通道
- ADR-0033 (submodule-aware) — `project.yaml` 在 submodule 内独立管理（per `_lib/skill_root.sh` 解析）
- ADR-0034 (rdd-verifier) — `verification.provider=hook` 是 LLM 的等价替代，verifier 仍走 `ac-verify` 框架
- ADR-0035 (verifier-archive-gate boundary) — archive gate 不区分 LLM/hook provider

## Compliance Notes

- 提案追踪：`openspec/changes/rfc-rddf-project-yaml-config-i10/`
- 实施计划：`.rddf/plans/rfc-rddf-project-yaml-config-i10.md`
- Branch：`openspec/rfc-rddf-project-yaml-config-i10`
- Approval: `proposal-approved.md` (2026-09-01, guide-design)
- 上游 RFC: https://github.com/chisuhua/rdd-workflow/issues/10

## Open Questions

- M2 剩余 4 个 task（populate 透传）延后到独立 PR，本提案仅实施 M2 核心（参数化 + discover）
- M5 全量回归门 `./test.sh --full --regression` 在 archive 前必须全绿（per AGENTS.md 硬性要求）

## Post-hoc Fix Record (2026-09-02)

`complete-project-yaml-config-gaps` change 审计 i10 archive 后发现 8 项 task 标记完成但代码未实际落地,通过本 change 补齐:

| i10 Task | 缺口 | 修复 commit |
|----------|------|------------|
| 1.1 schema 4 节 | `_lib/schemas/config_schema.json` 缺 `project`/`adr`/`git`/`verification` 节 | `0b04081` (M1 feat) + `f136b01` |
| 1.5 defaults project 默认 | `_lib/core/defaults.py::DEFAULTS` 缺 `project` 键 | `ca40d51` |
| 3.1 guide-ship Phase 1 Step 1.5 | `skills/guide-ship/SKILL.md` 不读 project.yaml | `7be7ab6` |
| 3.2 ship_execution_mode project.yaml 分支 | `_lib/ship_execution_mode.sh::parse_execution_mode` 不读 project.yaml | `1b42454` |
| 3.4 guide_ship_execution_mode 集成测试 | `tests/integration/` 缺 openspec_tracked 场景 | `1b42454` (内嵌) |
| 3.5 ship_execution_mode priority bats | 缺独立 bats | `1b42454` (内嵌) |
| 4.1 catalog_sources adr_pattern 参数 | populate_lib 路径缺失 (但 `_lib/adr_catalog.py::scan_adr_catalog` 已有) | 已存在,`b6e1a35` 锁测试 |
| 4.2 populate_lib 透传 | `_lib/adr_catalog.py` 不从 arch-handoff 读 pattern | `6722ec9` (新增 `_resolve_adr_pattern_for_caller`) |
| 4.3 discover_arch_artifacts 集成测试 | 缺独立 bats | `156f49d` |
| 4.4 catalog_sources project.yaml fallback | arch-handoff 缺失时无 fallback | `b6e1a35` (`_read_project_yaml_adr_pattern`) |
| 4.5 arch_handoff_schema v2 adr_regex | schema 缺 adr_regex 字段 | `0b04081` |
| 4.6 write_arch_handoff 写 adr_regex | 不读 project.yaml | `f136b01` |
| archive.sh YAML bool bug | `[ "false" = "false" ]` 不匹配 Python bool `False` | `9098a73` (M3 修复) |

**PR 系列**: `openspec/complete-project-yaml-config-gaps-{m1,m2,m3,m4,x}` 共 5 个分支,经 `./test.sh --quick` 全量回归(2457 pytest + 28+ bats cases)验证。

**关键决策 (design.md)**:

- Decision 1: schema 根级 `additionalProperties: true`,新节内部 strict (根级 extras 不破坏)
- Decision 2: hook runner + 退出码映射 0/1/2+ → passed/failed/error
- Decision 3: `cache_key()` 4-step 优先级链 (explicit > arch-handoff > project.yaml > default)
- Decision 4: Phase 1 Step 1.5 在 worktree 创建前检测（2026-11-17 修订：该检测只保留在**归档路径**与**波次维度**；执行模式不再由该开关决定 —— 见「修订 2026-11-17」节）
- Decision 8: explicit runner > provider 自动检测
- Decision 9: `RDDF_EXECUTION_MODE` env var 是 Phase 1 输出,非 `parse_execution_mode` 输入（2026-11-17 修订：该变量全仓 0 个读取点 ⇒ **一并退役**，见「修订 2026-11-17」节 R2）
- Decision 10: 本节("Post-hoc Fix Record")作为 ADR 后续 fix 记录惯例(替代 append 到 Consequences)
- Decision 11: schema strict 范围 (根 loose, 新节 strict)

**根本原因预防 (Task X.6)**:

`tests/integration/test_archive_gate_tasks_checklist_match.bats` 在 `openspec archive` 前验证 `tasks.md` 中每个 `- [x]` 任务都有对应文件变更。若未来 change 再次出现 checkbox-as-done 漂移,该 bats 测试会失败。

Refs: `openspec/changes/2026-09-02-complete-project-yaml-config-gaps/` + `openspec/changes/archive/2026-09-02-rfc-rddf-project-yaml-config-i10/`
