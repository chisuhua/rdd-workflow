---
优先级: P2
priority: P2
来源: ADR-0036 的 2026-11-17 修订（architect 复核第 2~5 轮反复指出「退役面少算」）—— 该修订的
  「后续待办 → 全局残余清理」条目；实测口径见下方「架构依据」
阶段: phase-2
分类: bugfix
类型: bugfix
状态: draft

生成时间: 2026-11-18
roadmap_ref:
---

# fix-spec-residue-guard

**主题**: 让「已删除 stage 出现在规范里」从「只能靠人读」变成「机器可发现 + 可审计」

> ⚠ **本项是 ADR-0036 修订的 V-H（`v4_residue_check` 扫描面扩展到 `openspec/specs/`）的落地项**
> —— 修订本身只**决定**处置方式，守卫与普查是独立立项。
>
> ⚠ **本项只交付「守卫 + 分类规则 + 普查台账」（tracked）**；**逐 spec 的清理**是需要逐份
> delta 与签批的**另一件事**（见「Phase 1」）。理由见下方「架构依据 → 为什么守卫与清理要拆开」。

## 架构依据

### 现象：已采纳的 capability spec 仍在以 v4 阶段合并前就已删除的 skill 为主体

`skills/guide-ship/` 等目录在 v4 阶段合并中被硬删除（ADR-0043 / ADR-0044 / ADR-0048），v4 的对应物是
`skills/rdd-arch` / `rdd-planner` / `rdd-builder` / `rdd-verifier`。但**已采纳**的 spec 文本仍以旧 stage
为主体 ⇒ 变成「指向不存在的东西的规范」。

### 实测口径（可复算；口径版本见下）

扫描 `openspec/specs/*/spec.md` 的 **normative 段**（`### Requirement` / `#### Scenario` 及其正文），
命中 `guide-ship|guide-plan|guide-arch|guide-design|guide-spec`：

| 口径 | 数值 |
|---|---|
| normative 段命中 | **204 处 / 47 份 spec** |
| 行级全量（含 Purpose 等非 normative 行） | 232 行 / 48 份 spec |

⚠ **口径未锁定 ⇒ 数字不可复算**：`normative 段` 的三个边界必须先写死 ——
① **fenced code block** 算不算 normative？（`dashboard-verification-status:50` 的 route 枚举就在
```json 块里）；② **Requirement 标题**算不算命中位置？③ **跨行断句**（`general/spec.md:143-144` 的
`propose, guide-arch,\n guide-plan, ...`）按行还是按块归类？⇒ 本项必须先跑 4 个口径组合（4 个布尔
开关）各一次，把选定口径的**基线数字**写进普查台账的头部 ⇒ 否则「清零」不可复现。

### 合法引用的**五类**（命中即不算违规）

| 类别 | code | 例子 |
|---|---|---|
| ① 退役 stage 的**历史枚举值** | `enum` | `cross-container-event-bus` 的 intent 枚举、`dashboard-verification-status` 的 route 枚举；⚠ 前提是**该枚举值今天仍存在于 schema**（实证：`_lib/schemas/sessions_schema.json:65` 仍含 `guide-*`） |
| ② **提案名** | `proposal-name` | `add-rdd-quick-skill` 的 `guide-ship-quick-finish` |
| ③ **反漂移守卫自身** | `guard` | `doc-architecture-v4-sync` 的「MUST NOT reference guide-ship」类 Requirement、`v4-residue-contract` 把 guide-ship 当**示例数据**的叙述 |
| ④ **归档历史** | `history` | `openspec/changes/archive/**` |
| ⑤ **重命名 / 历史叙述**（normative 内的重命名说明） | `rename-history` | `doc-architecture-v4-sync:89-94` 的 `from guide-arch to rdd-arch`；⚠ 前四类**覆盖不到**这一类 —— 这是实测发现的**第五类** |

### 根因：机器发现不了

`skills/rdd-doctor/scripts/checks/v4_residue_check.py` 的扫描面只有 `_lib/` 与 `skills/` —— **不含
`openspec/specs/`** ⇒ 「已删除路径出现在 normative 文本中」**无法被机器发现** ⇒ 只能靠人读 spec 才发现
（ADR-0036 修订的 critic 第 2~5 轮反复因此少算）。

### 为什么守卫与清理要拆开（metis 的最高优先建议）

| | 守卫 + 普查（本项） | 逐 spec 清理（Phase 1） |
|---|---|---|
| 是否进版本库 | ✅ 进（脚本 + 台账 + 夹具） | ⚠ **本仓不进**（`openspec/` 被 gitignore） |
| 对其它项目是否生效 | ✅ 生效 | ❌ 需各项目各自做 |
| 交付形态 | 一次 | **48 份 spec × 各自的 delta + 签批** |
| 可验证性 | ✅ 可测（有断言） | ⚠ 本仓**无法用 git 验证**（没有 diff、没有 commit、没有可回滚对象） |

⇒ 清理若与守卫同处一个 change：① 48 份 spec 的签批塞不进一个 change 的 P3 收尾；② 清理类 AC 在
本仓**恒为真**（没有 baseline 可 diff）⇒ 「看起来严格、实则空真」的判据最危险。⇒ 拆开。

### ⚠ 一个必须写明的前提：本仓 `openspec/` 被 gitignore

本仓 `.rddf/project.yaml` = `git.openspec_tracked: false` ⇒ `openspec/` **不入版本库**（`.gitignore:45`）：

- 对**本仓**而言，spec 文本是本地工作副本 ⇒ 权威落点是已签批的 ADR + **本项的 tracked 台账**；
- 对**开启了 `openspec_tracked: true` 的项目**而言，这些 spec 是**入库的活契约** ⇒ 残留是**活的契约
  缺陷**（按规范施工的人会在**完全合规**的前提下重新引入旧行为）⇒ 守卫的收益最大。

⇒ 守卫层是**唯一跨项目生效、唯一被跟踪、唯一防止复发**的资产 ⇒ 它是本项的主体。

## 范围

- **In Scope**：
  1. **`skills/rdd-doctor/scripts/checks/v4_residue_check.py` 的扫描面扩展到 `openspec/specs/`** ——
     扫描根**恰为** `openspec/specs/*/spec.md`（**不递归**进子目录；**完全不扫** `openspec/changes/**`
     —— 未归档的 change 目录里引用旧 stage 属正常考古，扫了必然大面积失败）；
  2. **分类规则**（机器化，**禁止文件级 allowlist**）：规则为元组
     `(matched_token, category, condition, precedence)`，spec 内用**行内标注**声明豁免
     `<!-- v4-residue:allow=<code> -->`（code ∈ `enum` / `proposal-name` / `guard` / `history` /
     `rename-history`）；
  3. **stale allow 报错**：标注的行若**不再命中** ⇒ 报 `stale allow`（这是白名单不腐化的**唯一**机器
     保障 —— 没有它，豁免清单只增不减，几年后就是第二个 false pass）；
  4. **普查台账**（tracked）：`.rddf/audits/spec-residue-census-2026-11-18.md`（机器生成），每行 =
     `file / line / requirement_title / matched_token / category / disposition / owner / signoff / date`；
     头部记录**口径版本**与**基线数字**；
  5. **门控三步走**：spec 扫描首版 = **WARNING** + 开关 `doctor.v4_residue.scan_specs`（默认 `false`）
     → 本项目打开 → 下游文档公布。⇒ `.github/workflows/test.yml` 的 doctor gate 是
     `fail-on-CRITICAL` ⇒ 直接判 CRITICAL 等于要求「清理先于守卫落地」，与「守卫先做」冲突；
  6. **区分「checked 0」与「clean」**：干净 clone 上 `openspec/` 不存在 ⇒ 守卫静默通过 ⇒ 报告必须输出
     「扫描文件数」⇒ `checked 0` 与「扫过且干净」**不是同一件事**（否则守卫在本仓 CI 里是一个假通过）。
- **Out Scope**：
  - **逐 spec 的清理**（Phase 1，另立项；本项只交付台账 + 守卫）；
  - 不清理**非 normative 段**的历史叙述（Purpose / 变更历史 / 提案背景）—— 那些是**正确的历史记录**；
  - 不改退役 skill 的**替代物**的行为（`rdd-builder` / `rdd-planner` 等本仓 skill 不动）；
  - 不处理 `docs/architecture/**`、`README.md` 与 `skills/execute/SKILL.md:57-59` / `README.md:129` 的
    死机制陈述（ADR-0036 修订的 backlog 已点名，**本项不动**）；
  - 不改**已归档 change** 的 `proposal.md` / `tasks.md`（历史记录不可改）；
  - 不处理 **hub-managed** capability 的残留（`skills/sync-hub/scripts/sync_hub.py:42` 会把 Hub 契约
    写到 `openspec/specs/<contract>/spec.md` ⇒ 清理会被上游覆盖 ⇒ 本项只**报**不**修**，责任上行到 Hub）。

## Why

**规范面已经批准退役的 stage，而机器守卫看不见它。**

- 后果不是「文档不好看」：一个按规范施工的人（人或 agent）读到「`guide-ship` SHALL own merge」，
  会以为 `guide-ship` 仍然存在 ⇒ 要么去找一个不存在的 skill，要么照着实现一份**已经不存在的流程**；
- 而 `v4_residue_check` 的扫描面不含 `openspec/specs/` ⇒ 这类漂移**不会**被任何自动检查发现 ⇒
  上一个 ADR 修订之所以反复「少算退役面」，正是因为它只能靠人工清点；
- 这类漂移有一个特别恶劣的性质：**它长得像合规**。规范里的每一条 MUST 都在，但它们的主体已经不存在 ⇒
  遵守规范的人会做出与 v4 相反的行为，而没有任何检查会报错。

## What Changes

1. **扫描面 + 口径**：
   - 扫描根 = `openspec/specs/*/spec.md`（只这一层；不递归；不扫 `openspec/changes/**`）；
   - **normative 段**的定义写死并落进代码注释：包含 `### Requirement:` 标题行、其正文、其
     `#### Scenario:` 标题行与正文、以及**正文内的 fenced code block**（理由：代码块里的 route 枚举
     就是读者会照抄的契约文本 —— 只在散文里说「不要用旧名」而代码块里留着旧名，恰恰是最恶劣的形态）
     ；**不含** Purpose / 变更历史 / 散文段落；
   - 命中按**块**（句子/代码块）归类，不按行 ⇒ 跨行断句不漏。
2. **分类规则**（元组 + 标注 + stale 检查）：
   - 标注语法：`<!-- v4-residue:allow=<code> -->`（**行内**，紧跟被豁免的那一行）；
   - 豁免的单位 = **(命中实例 + 角色)**，**绝不是文件** ⇒ 同一 spec 内可以同时存在「合法枚举值」与
     「真实残留」；⚠ 任何文件级 allowlist 都会在「某文件既是守卫契约、又需要 delta」处爆炸
     （实证：`v4-residue-contract` 整篇 `guide-*` 都是夹具示例（③），而它恰恰是本项要正向增补的契约）；
   - **不靠句子形态猜类别**：启发式（「同句含 `MUST NOT` / `deprecated` / `不再`」）只能作**标注缺失时
     的降级提示**，不能作豁免依据 —— 实证 `doc-architecture-v4-sync:8`（反漂移断言）、`:89-94`
     （rename history）、与一条真实残留，句子形态几乎相同；
   - **角色敏感**：`enum` 只豁免**枚举字面量**；同句把旧名说成 `the existing` 之类（实证
     `cross-container-event-bus:182`）⇒ 属**过时但不是假**的规范 ⇒ 给 WARNING 而非豁免。
3. **普查台账**（tracked，机器生成）：
   - `.rddf/audits/spec-residue-census-2026-11-18.md`，每行一个命中实例；
   - 头部写**口径版本**（4 个布尔开关的取值）与**基线数字**；
   - 台账是**清理清单 + 签批台账 + 可复算基线 + ADR-0036 后续待办的证据**四合一；
   - 幂等：同一输入跑两次，findings 的**顺序与内容**稳定（供台账 diff）。
4. **门控三步走**（见范围 §5）+ **checked 0 ≠ clean**（见范围 §6）。
5. **既有测试的连带影响**（必须登记）：`tests/unit/test_doc_contracts.py:52-53` 明确断言
   `general/spec.md` **必须**含 `guide-arch` / `guide-plan` ⇒ 清理会破坏它；同文件 `:32-47` 的
   `test_general_spec_no_active_guide_spec_reference` 已经是一个**手写的分类器**（用正则判「消费方列表
   里是否把 guide-spec 当 active」）⇒ 它既是「清理会破坏测试」的证明，也是**「③ 类机器化」的现成参考
   实现** ⇒ 本项的规则实现应把它作为输入（而不是另造一套）。

## Acceptance

- [ ] 扫描根**恰为** `openspec/specs/*/spec.md`：断言 `_scan_roots` 不含 `openspec/changes`；并用
      fixture 造一个 `openspec/changes/archive/x/spec.md` ⇒ **不报**
- [ ] **normative 段口径已锁定并落进代码注释**：4 个口径组合（fenced code block ∈/∉ × Requirement 标题
      ∈/∉）各跑一次，**基线数字**写进台账头部 ⇒ 「清零」可复算
- [ ] 五类合法引用各有 **1 正例 + 1 反例**夹具（共 10 个）⇒ 正例不报、反例必报
- [ ] 标注 `<!-- v4-residue:allow=<code> -->` 生效；**标注但不再命中 ⇒ 报 `stale allow`**
- [ ] **禁止文件级 allowlist**：同一 spec 内「合法枚举值」与「真实残留」混合的 fixture ⇒ 只豁免前者
- [ ] `enum` 角色的**措辞敏感**：`cross-container-event-bus:182` 那种「the existing」形态 ⇒ 给 WARNING
      而非豁免
- [ ] 台账 `.rddf/audits/spec-residue-census-2026-11-18.md` 已生成：每行含
      `file / line / requirement_title / matched_token / category / disposition / owner / signoff / date`；
      头部含口径版本与基线数字
- [ ] 台账**幂等**：同一输入跑两次 ⇒ 内容与顺序不变
- [ ] 守卫在**改动前**对当前仓库报出**已知的**真实残余 ⇒ 夹具断言：**改动前第一条必须是红的**（把实测
      的「分类后仍报 N 处」写死为常数）
- [ ] 人为注入一处新残留 ⇒ 报出；撤掉 ⇒ 不报（变异验证）
- [ ] `openspec/` 不存在的项目**不报错**（沿用 `test_missing_schema_files_do_not_raise` 的模式）
- [ ] **`checked 0` 与 `clean` 分开**：报告输出扫描文件数；`checked 0` 时**不得**报「无残留」
- [ ] 门控：spec 扫描首版 = **WARNING** + `doctor.v4_residue.scan_specs` 默认 `false`；本项目打开；
      CI 的 `fail-on-CRITICAL` 不被本项拖红
- [ ] `tests/unit/test_doc_contracts.py:52-53` 的既有断言（`general/spec.md` 必须含 `guide-arch`）已被
      登记为**清理阶段的连带影响**（本项不改它，但台账里对应行标注了它）
- [ ] hub-managed capability 的命中**只报不修**（台账里标 `excluded(hub-managed)`）
- [ ] **异常 spec 目录**（实测存在 `openspec/specs/--help/`、`phase-20260829063800*/`、`test-change/`、
      `tests/` —— 目录名含 `--` 会被按参数处理）⇒ 已登记为**遗留问题**或剔除，判定有据
- [ ] `./test.sh --unit` + `./test.sh --full --regression` 全绿

## Capabilities

- 「已删除 stage 出现在规范里」从**只能靠人读**变成**机器可发现**（守卫层入版本库，对所有项目生效）
- 合法引用**不会被误报**，且豁免清单**会自己过期**（stale allow 报错）⇒ 白名单不会腐化成第二个假通过
- 清理清单由工具产出（file + line + Requirement 标题 + 角色）⇒ 逐 spec 的 delta 有可执行的输入
- 「checked 0」不再被读成「干净」⇒ 守卫不会在一个没有 `openspec/` 的 clone 里假装通过

## Impact

- **影响面**：`skills/rdd-doctor/scripts/checks/v4_residue_check.py`（扫描面 + 分类规则 + 标注解析 +
  stale 检查 + 定位输出）、`.rddf/audits/spec-residue-census-*.md`（新增，tracked）、
  `skills/rdd-doctor/` 的配置读取（新增开关）、doctor 的报告渲染（若要显示 Requirement 标题 ⇒
  `doctor_render.Finding` 只有 `severity/category/file/line/snippet/fix_hint`，**没有标题字段** ⇒
  二选一：扩 `Finding`（需评估渲染与快照测试的影响）或规定 `snippet` 前缀含 `[req:<title>]`）、
  `tests/unit/test_v4_residue_check.py`（夹具）。
- **风险**：
  - **白名单腐化** ⇒ 由 stale allow 兜底（必须有测试守着）；
  - **误报淹没真问题** ⇒ 豁免的**单位是命中实例**而非文件；分类规则逐类给出正反例；
  - **门控一次性放开会把下游项目拖红** ⇒ 首版 WARNING + 开关默认 false + 三步走；
  - **清理会破坏既有测试**（`test_doc_contracts.py:52-53`）⇒ 属 Phase 1 的连带影响，本项只登记；
  - **本仓的 spec 文本不进版本库** ⇒ 本项的产物（守卫 + 台账）**必须**进 tracked 文件，否则看起来像
    「什么都没做」。
- **兼容性**：新增 doctor 配置项（默认关闭）⇒ 不影响既有调用；扫描根变更**只增不减**（既有 `_lib/` 与
  `skills/` 扫描不变）。
- **依赖**：处置方式沿用 ADR-0036 修订（已签批）⇒ 本项**不新造决策**；若某处残余**无法**用已定的分型
  处置 ⇒ 回 planner / architect 裁定，不在实施层自造。

## Phase 1（另立项 —— 逐 spec 的清理）

**不在本项范围内**，但由本项的台账驱动：

- 逐 spec 的 delta + 签批（处置方式沿用 ADR-0036 修订的四种分型 + 本项补充的两种形态：
  **整份 capability 退役**（`three-phase-skills` 的 4 个 Requirement 全部以已删除 skill 为主体）与
  **Requirement 标题即旧名**（`iterative-plan-fill:6`、`roadmap-feature-fragment:81`、
  `roadmap-proposal-guidance:69/:103`、`project-setup-check:79`、`spec-validation-gates:149` 等 6 份以上）
  ⇒ ⚠ **改 Requirement 标题 = RENAMED 语义**（`_lib/validate_delta_targets.py:159` 校验 RENAMED 源必须
  存在于主 specs）⇒ 改标题**不是没有代价的**，需按 openspec 的 RENAMED 流程走；
- **归属**：ADR-0036 的 R1~R10 中，**R4 归 ADR-0061**、**R1~R3 归 `fix-execution-mode-decision`** ⇒
  本项**不重复计入**它们，只承接全局残余；
- 台账里 `category=unclassified` 且 `disposition=unset` 的行归零 ⇒ 即 Phase 1 的完成判据。

## 审稿记录

metis 1 轮（2026-11-18，planner 阶段 gap 分析）。逐条处置：见文末「metis 处置记录」。

### metis 处置记录（2026-11-18）

metis 的核心判断：**真正要交付的不是被清理后的 spec 文本，而是一份「机器可读的分类规则 + 一份 tracked 的
普查台账」** —— 因为本仓 `openspec/` 完全未被版本跟踪 ⇒ 清理层在本仓不产生任何可提交的 diff，新 clone
上 `openspec/` 根本不存在 ⇒ 清理出来的文本会在下一个开发者那里再次消失。

| # | metis finding | 处置 |
|---|---|---|
| P0-1 | **交付物错配**：本仓 `openspec/` 不跟踪 ⇒ 清理层不产生可提交 diff；「两层并列交付」掩盖了「守卫层才是唯一被跟踪、唯一跨项目生效、唯一防复发的资产」 | ✅ **采纳** ⇒ 立项改名 `fix-spec-residue-guard`；范围明确为「守卫 + 分类规则 + 普查台账」（tracked）；**逐 spec 清理移入「Phase 1（另立项）」**，并写明拆开的理由对照表（是否进版本库 / 是否跨项目生效 / 交付形态 / 可验证性） |
| P0-2 | **实施顺序被草案写反**：草案说「守卫先做（因为被跟踪）」—— 那是**交付价值**的排序，不是**实施顺序**。正确顺序是：先普查（机器枚举 204 处并逐条标注分类）→ 再抽规则与夹具 → 最后清理。理由：分类器的正确性只能由这 48 份 spec 的真实形态验证；从 4 个轶事例子反推分类器必然返工 | ✅ 采纳 ⇒ What Changes §2 写明「规则与夹具的形态由普查的真实样本决定」，且分类从 4 类扩到 **5 类**（补 `rename-history`，实测 `doc-architecture-v4-sync:89-94` 覆盖不到） |
| P0-3 | **豁免的机器化没有载体**（"机器化" 是不可判定的表述）；三个候选形态里「文件级白名单」是 slop；「启发式否定辖域」单独用不可判（`doc-architecture-v4-sync:8`、`:89-94` 与一条真实残留句子形态几乎相同） | ✅ 全部采纳 ⇒ 豁免 = **元组规则** `(matched_token, category, condition, precedence)` + **行内标注** `<!-- v4-residue:allow=<code> -->` + **启发式只作降级提示不作豁免依据**；明确**禁止文件级 allowlist** |
| P0-4 | **白名单腐化无机器保障** | ✅ 采纳 ⇒ 新增 **stale allow 报错**（「标注的行若不再命中 ⇒ 报」）+ 对应 AC + 风险段 |
| P0-5 | **豁免的单位必须是「命中实例 + 角色」**：实证同一 spec 内三种混合形态 —— `doc-architecture-v4-sync`（③ 断言 + ⑤ rename history + 可能的真实残留）、`v4-residue-contract`（整篇 ③ **但它恰恰是本项要正向增补的契约** ⇒ 文件级豁免与「该 spec 需要 delta」直接冲突）、`cross-container-event-bus:182`（① 枚举字面量合法，但同句把旧名说成 `the existing` ⇒ 过时但不是假） | ✅ 全部采纳 ⇒ 规则实现以**五元组**为粒度 `(file, requirement_title, matched_token, role, reason_code)`；AC 新增「禁止文件级 allowlist」「enum 角色的措辞敏感（`the existing` ⇒ WARNING 而非豁免）」 |
| P1-6 | **normative 段边界未定义**（fenced code block？Requirement 标题？跨行断句？）⇒ 「204 处」这个基线**不可复算** | ✅ 采纳 ⇒ AC 新增「4 个口径组合各跑一次 + 基线数字写进台账头部」；What Changes §1 写死口径（含代码块、不含散文）+ **按块归类**（跨行断句不漏） |
| P1-7 | **「逐 spec delta + 签批」在本仓无法验证** ⇒ AC 变成空壳；AC10（可独立回滚）与 AC9（非 normative 未被改动）**恒为真** | ✅ 采纳 ⇒ 清理移出本项（Phase 1）；AC 改为围绕**台账**写（`category=unclassified 且 disposition=unset` 的行归零）；AC9 改为「守卫**严禁报**非 normative 段」（可测） |
| P1-8 | **「排除 `openspec/changes/archive/`」与「类别 ④ 归档历史」是同一件事的两份表述，且前者是空操作**（扫描根若只有 `openspec/specs/` 本就命不中） | ✅ 采纳 ⇒ 范围改为「扫描根**恰为** `openspec/specs/*/spec.md`；`openspec/changes/**` **完全不扫**」+ AC 用 fixture 断言；并补上「为什么不扫**未归档** change」（那里允许自由引用旧名） |
| P1-9 | **门控策略未决** ⇒ `.github/workflows/test.yml` 的 doctor gate 是 `fail-on-CRITICAL` ⇒ 选 CRITICAL 等于要求「清理先于守卫落地」，与草案的「守卫先做」**直接冲突** | ✅ 采纳 ⇒ **门控三步走**：首版 WARNING + `doctor.v4_residue.scan_specs` 默认 `false` → 本项目打开 → 下游公布；AC 显式写「CI 的 `fail-on-CRITICAL` 不被本项拖红」 |
| P1-10 | **「checked 0」与「clean」不可区分** ⇒ 干净 clone 上 `openspec/` 不存在 ⇒ 守卫静默通过 ⇒ 本仓 CI 里是一个假通过 | ✅ 采纳 ⇒ 范围 §6 + AC「报告输出扫描文件数；`checked 0` 时**不得**报『无残留』」 |
| P1-11 | **既有测试的连带影响未登记**：`tests/unit/test_doc_contracts.py:52-53` 断言 `general/spec.md` **必须**含 `guide-arch`/`guide-plan` ⇒ 清理会破坏它；同文件 `:32-47` 的 `test_general_spec_no_active_guide_spec_reference` 是**现成的分类器参考实现** | ✅ 全部采纳 ⇒ What Changes §5 + AC + Impact 风险段；并在 Phase 1 里点明「改 Requirement 标题 = RENAMED 语义（`validate_delta_targets.py:159`）」 |
| P1-12 | **归属不清**：R1~R10 与 backlog 的 204 处可能重叠 ⇒ 允许「双方都声称完成 / 都不属于自己」 | ✅ 采纳 ⇒ Phase 1 写死归属：**R4 → ADR-0061**、**R1~R3 → `fix-execution-mode-decision`**、本项只承接全局残余；AC 不重复计入 |
| P1-13 | **词边界 / 别名变体**（`guide-plan` 前缀命中 `guide-planning`；`guide-ship-quick-finish`；`guide_ship` / `Guide-Ship` / `guide ship` / `rddf/guide-ship`）与**跨行断句** | ✅ 采纳 ⇒ 命中按**块**归类；词边界与大小写/分隔符变体列入范围 §1 的口径锁定项（4 个布尔开关之外再加「词边界」维度） |
| P1-14 | **Hub 覆盖风险**：`sync_hub.py:42` 把 Hub 契约写到 `openspec/specs/<contract>/spec.md` ⇒ 清理会被上游覆盖，收益为零 | ✅ 采纳 ⇒ Out Scope 明写「hub-managed 只报不修，责任上行到 Hub」+ AC |
| P1-15 | **异常 spec 目录**（`--help`、`phase-20260829063800*`、`test-change`、`tests/`）没有可签批的 owner ⇒ 清理层会产生无法处置的记录 | ✅ 采纳 ⇒ AC「异常目录已登记为遗留问题或剔除，判定有据」 |
| P2-16 | **缺若干机器可判的判据**：severity 与 CI 门控、空扫与干净、幂等、标注腐化、hub 只报不修、`openspec/` 缺失不报错 | ✅ 全部采纳 ⇒ 逐条转成 AC（见上） |
| P2-17 | 「在已签批 ADR 的『后续待办』里打勾」与 ADR-0060 的「存量不追溯」冲突，且把台账放进 ADR 使其变成活工件 | ✅ 采纳 ⇒ 台账独立成 tracked 文件 `.rddf/audits/spec-residue-census-*.md`；**不**在 ADR 里打勾（ADR 只留指针） |
| P2-18 | **两种未覆盖的处置形态**：整份 capability 退役（`three-phase-skills`）；Requirement 标题即旧名（6 份以上） | ✅ 采纳 ⇒ 移入「Phase 1（另立项）」，并写明改标题的 RENAMED 代价 |
| 隐含意图 | 「没有普查（census）」才是 ADR-0036 反复少算退役面的根本原因 —— 普查产物比守卫脚本更接近真实需要 | ✅ 采纳 ⇒ 普查台账升为**本项的主交付物之一**（清理清单 + 签批台账 + 可复算基线 + 证据 四合一） |

