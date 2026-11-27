---
优先级: P0
来源: 2026-11-27 合并立项 —— U1（范围节解析）+ U2（spec delta 形态/语义），来源为 2026-11-26 CppTLM 立项会话（session ses_de7dcca7fffeOvO830nfolajk4）实测复现；oracle → critic → metis 三方审查（2026-11-26/27）
阶段: phase-3
分类: cli-tooling
类型: improvement
状态: 已归档（2026-11-27 · change `2026-11-27-fix-proposal-generator-output-fidelity` · 15/15 AC pass · 验收报告 `.rddf/reviews/fix-proposal-generator-output-fidelity-verify.md`）
主题: 生成器输出保真 —— proposal 范围节解析（纯表格 / 带注解标题 / 去逗号兜底）+ spec delta 的形态守卫与 MODIFIED 语义
---

**优先级**: P0 | **来源**: 2026-11-27 合并立项（U1+U2） | **阶段**: phase-3 | **分类**: cli-tooling | **类型**: improvement

**主题**: 生成器输出保真 —— proposal 范围节解析 + spec delta 的形态守卫与 MODIFIED 语义

> **合并说明**：本 improvement 由 `fix-proposal-generator-table-scope`（U1）与
> `fix-spec-delta-generator-shape-and-semantics`（U2）**合并**而成 —— 两者改**同一文件**
> （`skills/rdd-builder/scripts/generate_full_proposal.py`）⇒ 合成**一个** openspec change，
> 省一次立项与一次 P0/P1 编排开销（per objective `objective-proposal-lifecycle-truth` §9.4 W1 批次）。
> 两份源草稿的正文**逐字保留**（分轴标注 U1/U2），「验收标准」**重新编号**：
> U1 的 AC1–AC6 → 本文件 **AC1–AC6**；U2 的 AC1–AC8 → 本文件 **AC7–AC14**（编号引用已同步修正）。
>
> ⚠ **合并的已知代价（metis 2026-11-27）**：合并把「可立即 ship 的 parser 修复（U1）」与
> 「需 design 裁决的契约变更（U2）」捆在一起 ⇒ **内部落地序强制为 U1 → 语料快照 → U2**
> （见 §技术约束「内部落地序」）；U2 的载体类决策（放行载体 / `delta` 字段载体 / 版本探测）
> **在 change 的 design.md 落裁决**，本稿只固定**裁决的判据形态**（两种裁决都要可机判）。
>
> ⚠ **源草稿处置**：`fix-proposal-generator-table-scope` 与 `fix-spec-delta-generator-shape-and-semantics`
> 已标「已合并」并**移出提案池** ⇒ 不再被 planner 拾取；三份文件同时留在 `.rddf/improvements/`
> ⇒ 语料快照**必然包含**它们（正常，不是脏数据）。

## 架构依据

### 轴 1（U1）：proposal 的「范围节」解析 —— 纯表格形态被逗号兜底切碎

`skills/rdd-builder/scripts/generate_full_proposal.py` 把 improvement 的 `## 范围` 段转成 proposal 的
In/Out Scope。它有两条路径：① `_extract_scope_items()`（:112-150）认 bullet / 编号条目；② 兜底
`:238-243` 把整段按逗号切碎。**兜底是 footgun**：任何多行文本（含 markdown 表格）都会被切碎。

CppTLM 的 improvement `cep-ssp-cp-q1b-landing.md` 用**表格**写 In Scope（6 行 × 3 列），落进兜底 ⇒ 实测产出：

- In Scope 第 2 行的 `protocol_family.hh:43-53,56,79-89,106-113` 被切成 **4 个独立条目**（`56` / `79-89` / `106-113`…）；
- `**In Scope（6 项 · contract 面）**` 因标题带括号注解未被 `_SCOPE_HEADER_RE`（:28-30）识别 ⇒ 整行成为条目；
- **整段 Out of Scope 被重复输出两遍**（兜底把 Out 段整体吞成 in-scope 的一个条目，模板又单独渲染一次）。

⇒ 立项产物需人工重写才能用。同一缺陷已在 `fix-bats-per-file-timeout.md:411`「本次不做」第 3 条记过一次
（「未改生成器，工具缺陷另案」）⇒ **第 2 次复发**。

**边界（不要重复已修的部分）**：归档 change `2026-08-14-fix-generator-scope-extraction`（commit `68623a4`）
已修 bullet / 编号 / 子项归并 / `- **Out Scope**:` 拼写 ⇒ 本提案**只**处理仍破的形态：
**范围节是纯表格（无任何 bullet）** 与 **标题带尾部括号注解**。⚠ **语料计数必须动态**（review 时实测 **304** 份且仍在增长）⇒ 快照文件写入「生成时点 + glob 计数」，**禁止在 AC 里写死份数**。

### 轴 2（U2）：spec delta —— 形态退化 + 语义错（改既有 capability 的 change 被写成新增能力）

rdd-builder P0 从 improvement 一次生成两份产物（`phase0_approval.sh:161-183`）：`proposal.md` 与
`openspec/changes/<name>/specs/<name>/spec.md`（D3 delta）。**delta 侧有两条独立缺陷轴**：

### 轴 A：形态退化（守卫已存在，生成器仍产出 ⇒ 每次归档手工重写）

`generate_full_proposal.py:311/339` 生成 `acceptance-N` / `capability-N` 需求名，`:318/346` 生成恒真 WHEN
（`- **WHEN** the change is applied`）。这正是 `tests/unit/test_spec_requirement_form.py:60-75` 判为退化并**拒绝**的形态
（无语义 Requirement 名 / 恒真 Scenario WHEN）⇒ **生成器仍在产出被守卫拒绝的形态**。

⇒ 该缺陷已被记录 **3 次**（`fix-spec-v3-naming-sync.md:192`「第三次撞上同一堵墙…根因确在 `generate_spec_delta()`，
**另案立项**」——**至今没有对应 improvement 文件**）⇒ 本提案就是那个「另案」，并补上「另案必须落载体」的机制缺口。

### 轴 B：语义错（改既有 capability 的 change 被写成新增能力）

`generate_spec_delta()`（:302）**无条件**输出 `## ADDED Requirements`；`phase0_approval.sh:175` 恒落
`specs/<change-name>/`。而 CppTLM 的 change 改的是**既有** capability `cep-core-contracts` ⇒ 产出语义错
（新增 `acceptance-N` 能力），且 `openspec validate --strict` **照样绿**（结构合法 ⇒ 结构校验抓不到语义错）。

CppTLM 会话里 agent 只能手工整段重写为 `## MODIFIED Requirements` + 逐字复制既有 requirement
（openspec 的 MODIFIED 语义要求**既有 Scenario 不得缺失**，否则 archive 报错 —— `specs-apply.js:392-394`，1.14.3；
该检查 1.7.0 起存在，**1.4.1 无**）。

## 范围

### In Scope

**轴 1（U1）**：

- `generate_full_proposal.py`：① `_SCOPE_HEADER_RE` 容忍标题尾部括号/方括号注解（`**In Scope（6 项）**`）；
  ② `_extract_scope_items` 识别 markdown 表格行（`| a | b |`）⇒ 每行成一个条目（去掉对齐行 `|:--|--:|`）；
  ③ **删除逗号兜底**（`:238-243`）—— 解析不出条目时**保留原文**并在 stderr 提示，**不猜**；
- **表格归属判别规则**（metis 裁决）：**纯表格节**（该节内**无任何** bullet / 编号条目）⇒ 表格行**各自成条目**；
  **bullet 下方的表格** ⇒ 仍**归该 bullet**（沿既有 spec `generator-scope-extraction` 的既有语义，**不改**）；
- **标题优先级**（design 裁决项，AC6 锁定）：`## 范围` 与 `## What Changes` **并存**时 ⇒ 取候选序靠前者
  （现状候选序：`范围` → `What Changes` → `Scope`）并**加用例锁定 + 文档写明**；
  （`fix-bats-per-file-timeout.md:411` 记录的「`## What Changes` 被 `## 范围` 顶掉」是**同源现象的参考**，不是裁决依据）
- 回归用例（新增）：纯表格节 / 表格+bullet 混排 / 标题带括号注解 / 表格内含逗号 / Out 段重复 5 组；
- 语料回归：**golden snapshot**（期望输出入库）而非「差异白名单」—— 见 §验收标准 AC4。

**轴 2（U2）**：

- **opt-in（design D-10，实施期发现）**：improvement **未声明** `**delta**` ⇒ **不生成 delta**（不算失败）——
  否则「总是生成、无载体即拒绝」会让存量 300+ 无载体的 improvement 的 P0 **全部被拒**（实测 18 个 bats 用例红）；
  而旧行为（总是生成）正是退化形态的来源 ⇒ 正确契约是「**声明了才生成**」。
- **轴 A（形态）**：生成器在产出 delta 前**自检**形态 —— 出现 `acceptance-N` / `capability-N` 需求名或恒真 WHEN ⇒
  **拒绝生成并报错**（exit ≠ 0），要求 improvement 提供**可转写的语义需求**；
  判据**抽共享模块**（`tests/unit/test_spec_requirement_form.py` 的三条正则）⇒ 生成器与测试**同源**，禁复制第二份；
- **轴 B（语义）**：improvement 用**粗体头行**声明 delta 目标与语义要求（载体裁决见 §技术约束「载体裁决」）⇒
  生成器据此输出 `## MODIFIED Requirements` + 目录落 `specs/<target-capability>/`；
  MODIFIED 块**逐字复制** main spec 中该 requirement 的全部 Scenario（缺失 ⇒ 拒绝生成）；
- **`phase0_approval.sh` 的半成品防护**（metis 指出）：现写法 `python3 … > "$DELTA_FILE"` 在拒绝时**留下空文件**
  ⇒ 重试时 `[ ! -f "$DELTA_FILE" ]` 为假 ⇒ **永久静默跳过 delta 生成** ⇒ 改为「**写临时文件 + 成功后 mv**」
  （proposal 同理），失败 ⇒ **不留空文件、不留半成品**；
- **openspec 版本探测机制**（metis 指出：仓内**零**检测代码）：新增纯 stdlib 的版本解析（`openspec --version` 语义化比较）
  —— 守卫按版本分流（≥1.7.0 复用原生 archive 检查 + 本地预检；<1.7.0 自实现 `missing == ∅`）；
- **守卫接线点**（metis 指出：`validate_delta_targets.py` 当前**仓内无可执行调用方**）：
  接线点 = **P0 生成时**（本地预检 MODIFIED 目标存在 + Scenario 守恒），P3 archive 前复用同一实现；
- `skills/rdd-builder/SKILL.md`：补 delta 契约文档（含载体、MODIFIED 保留既有 Scenario、版本口径），
  并由**新建**的 `tests/unit/test_rdd_builder_skill_contract.py` 断言（仓内无现成的 SKILL 内容锚点测试）。

### Out of Scope

**轴 1（U1）**：

- 不改 `_extract_bullet_items`（技术约束 → Capabilities/Impact 的路径，已由 `fix-generator-scope-extraction` 覆盖）；
- 不改 `## What Changes` 的段落模板结构（除 In/Out Scope 块）；
- 不改 `_split_capabilities_impact`（`SHOULD` 混入 Capabilities 的既有偏差，`fix-generator-scope-extraction` 已登记为「未修」）；
- 不动既有 improvement 的**内容**（只读回归语料）。

**轴 2（U2）**：

- 不改 ADR-0025 D2/D3 的段映射契约（只新增**粗体头行**这一入口，不扩固定段落映射）；
- 不改 openspec 自身（外部工具）；不改 `openspec/specs/**` 既有活规范；
- 不做「自动把 improvement 的 AC 改写成语义需求」⇒ 那是 improvement 作者的职责（生成器只做拒绝与放行）；
- 不改 `validate_delta_targets.py` 的既有语义（只接线 + 补默认 target 解析与新目录语义的互动）；
- **不改** 既有 change 的 delta 目录（老 change 已是 `specs/<change-name>/` ⇒ **新旧目录语义并存**，
  本次只保证**新生成**走新语义；归档侧的新旧混合处理另案）。

## 关键场景

### 轴 1（U1）

1. 范围节为纯表格 ⇒ In Scope 每行一个条目，条目内**不含** `|` 与换行碎片；Out Scope 只出现一次。
2. 范围节为表格 + bullet 混排 ⇒ **bullet 下方的表格归该 bullet**；**无 bullet 的纯表格节**里每行一个条目。
3. 标题为 `**In Scope（6 项 · contract 面）**` ⇒ 识别为标题，不成为条目。
4. 表格单元格内含逗号 ⇒ 不被切碎（逗号兜底已删除 ⇒ 这类文本只会出现在表格行内）。
5. 范围节无法解析出任何条目 ⇒ proposal 的 `## What Changes` 保留原文 + stderr 一行提示，**不产出错乱条目**。
6. `## 范围` 与 `## What Changes` 并存 ⇒ 取候选序靠前者（`## 范围`）+ 一行 stderr 提示（现状语义锁定）。

### 轴 2（U2）

1. improvement 无 `delta` 头行 ⇒ 生成 `## ADDED Requirements`（现状不变），且形态自检通过 ⇒ 正常落盘。
2. improvement 声明 `delta: modified cep-core-contracts` ⇒ 生成 `## MODIFIED Requirements`，
   目录 `specs/cep-core-contracts/`，requirement 名与 main spec **精确同名**。
3. MODIFIED 块缺 main spec 中任一既有 Scenario ⇒ **拒绝生成**（stderr 指名缺哪个），**不留空文件**、**不留半成品 proposal**。
4. improvement 的 AC 只能转写成 `acceptance-N` ⇒ **拒绝生成**（形态退化守卫），报「请提供语义需求」。
5. improvement 提供了**语义要求**（载体见 §技术约束）⇒ 正常生成：Requirement 名语义化、Scenario 的 WHEN 用作者文本
   （**不是**恒真 WHEN）。
6. 项目 openspec 版本 < 1.7.0（无原生场景守恒检查）⇒ 守卫**自实现** `missing == ∅`（允许新增场景），
   与 1.7.0+ 的原生检查**判据等价**。
7. **跨轴**：同一 improvement 同时命中两轴（范围节纯表格 + 声明 `delta: modified`）⇒ 一次 P0 跑出
   **两份都正确**的产物（proposal 的 Scope 无碎片 + delta 为 MODIFIED 且 Scenario 守恒）。

## 技术约束

**轴 1（U1）**：

- 语料回归：**golden snapshot**（期望输出入库，断言「当前生成结果 == 期望快照」）。
  ⚠ **不用「差异白名单」**（文件清单可随同一 PR 修改 ⇒ 判别力为零；metis 2026-11-27 裁决）。
  - 快照**自带** `generated_at` + `corpus_count`（**动态计数**，不写死份数）+ 形态标签表；
  - 语料增长口径：新增 improvement ⇒ **必须同 PR 刷新快照**（否则 CI 红 ⇒ 提醒）；
  - **快照基线 = 修复后**的输出（golden）⇒ 修复前后差异由 PR 描述 + 一次性比对脚本说明，**不入库为判据**；
  - 形态标签（机判）：按**行首形态**打标（`table_row` / `bullet` / `numbered` / `other`）⇒ 差异可按标签归类，
    不依赖人眼分类；
  - 语料路径**仓根相对**：`.rddf/improvements/*.md`（测试从仓根解析，**不是** `../.rddf/...`）；
- 生成器不引入新依赖；纯 Python 3 stdlib；
- 兜底删除后，所有**依赖逗号切分**的历史 improvement 会改变输出 ⇒ 必须逐份比对并把差异登记在案（不得静默）。

**轴 2（U2）**：

- **载体裁决**（本稿固定**判据形态**，具体载体在 change 的 design.md 落定；**两种裁决都必须可机判**）：
  - `delta` 目标声明：候选 = **YAML frontmatter** 或 **粗体头行**（`**delta**: modified <cap>`）。
    ⚠ 约束：生成器**纯 stdlib** ⇒ 选 frontmatter 就必须自己写最小解析器（禁引入 PyYAML）；
    D6 时代的「头部」= **粗体头行**（`_HEAD_RE` 已认）⇒ 与 D6 对齐的默认候选是**粗体头行**；
  - 语义要求载体：**粗体头行**（D-1 已落定，纯 stdlib；形态
    `**语义要求**: requirement | body | scenario | WHEN | THEN`，多条以 `;;` 分隔）；
    **缺载体 / 缺字段时生成器必须拒绝并指名缺什么**（不得静默产出 `acceptance-N`）；
  - 判据形态固定：**两种裁决都要有可机判的 AC**（AC7 / AC8 / AC9 写成「依裁决取值」的形式，不预设答案）。
- 判据单一真源：形态三条正则抽到共享模块（如 `_lib/spec_requirement_form.py`），生成器与
  `tests/unit/test_spec_requirement_form.py` **同源导入**；禁在生成器内另写一份（两处实现 ⇒ 漂移）；
- 版本口径：守卫实现按项目实际 openspec 版本选择（≥1.7.0 复用原生 archive 检查 + 本地预检；<1.7.0 自实现）；
  版本比较**必须语义化**（`1.14.3 > 1.7.0` 成立，字符串比较会错）⇒ **变异腿**：退化为字符串比较 ⇒ 必须红；
- 落点目录语义变更（`specs/<change-name>/` → `specs/<target-capability>/`）属**契约面** ⇒ design 阶段显式裁决，
  并同步 `phase0_approval.sh` 与 `validate_delta_targets.py` 的目标解析（**新旧目录语义并存**：既有 change 不迁）；
- 生成器不引入新依赖；纯 stdlib。

**跨轴（合并的内部落地序，强制）**：

1. **U1**（范围节解析 + 兜底删除 + 标题优先级）⇒ 先落地；
2. **语料 golden snapshot**（在 U1 落地后生成，含本 improvement 自身）⇒ 再落地；
3. **U2**（形态守卫 + 载体 + MODIFIED 语义 + 版本探测 + 半成品防护）⇒ 最后落地。

**TDD 三段口径**（metis 2026-11-27 订正）：**功能类 AC** 必须三段（先红 → 修复后绿 → 变异后红）；
**回归类 / 门类 AC** 豁免变异腿，但**必须**写明红态来源或「现状已绿 · 防回归」；
**载体类 AC**（AC7/AC8/AC9）豁免「先红」（依赖 design 裁决），但**必须**给出两种裁决各自的可机判判据。

## 验收标准

> **功能类 AC 三段**（先红 → 绿 → 变异后红）；**回归/门类** 豁免变异腿（注明理由）；**载体类** 豁免先红（注明依赖 design 裁决）。

### 轴 1（U1）· proposal 范围节解析

- [ ] **AC1（功能类 · 红→绿）** 新增 `tests/unit/test_generate_full_proposal_scope_table.py`：5 个用例
  （纯表格节 / 表格+bullet 混排（bullet 下表格归 bullet）/ 标题带括号注解 / 表格内含逗号 / Out 段重复）
  ⇒ **先红**（当前实现产出碎条目与重复段）⇒ 修复后 **全绿**；
- [ ] **AC2（功能类 · 红→绿）** 同文件用例：范围节无法解析出任何条目时 ⇒ 生成结果保留原文且 stderr 含提示，
  **不**出现逗号切碎片段 ⇒ 修复前红 ⇒ 修复后绿；
- [ ] **AC3（回归类 · 现状已绿，防回归）** `tests/unit/test_generate_full_proposal.py` 现有用例**零回归**
  （`python3 -m pytest tests/unit/test_generate_full_proposal.py -q` 全绿）⇒ 变红即本次引入回归；
- [ ] **AC4（功能类 · 红→绿+变异）** 新增 `tests/unit/test_generate_full_proposal_corpus.py`：**golden snapshot** 断言
  （当前生成结果 == 入库期望快照）；快照自带 `generated_at` + `corpus_count`（**动态计数**）+ **行首形态标签表**
  （`table_row` / `bullet` / `numbered` / `other`）⇒ 语料路径**仓根相对** `.rddf/improvements/*.md`；
  ⚠ **变异腿**：改动形态标签分类器（如把 `table_row` 归成 `other`）⇒ 必须红（证明标签表参与判别）；
- [ ] **AC5（功能类 · 变异）** 把 `_extract_scope_items` 的表格识别退回「只认 bullet」⇒ **本轴 AC1** 的纯表格用例必须红
  （判别力证明；引用写明「本轴 AC1」以免与轴 2 的 AC7 撞号）；
- [ ] **AC6（功能类 · 红→绿）** 新增用例：**`## 范围` 与 `## What Changes` 并存** ⇒ 取 `## 范围`（现状候选序）
  + stderr 一行提示；**仅有 `## What Changes`** ⇒ 取它 ⇒ 两用例先红后绿（现状无锁定用例 ⇒ 锁死语义）。

### 轴 2（U2）· spec delta 形态守卫 + MODIFIED 语义

- [ ] **AC7（功能类 · 红→绿）** 新增 `tests/unit/test_spec_delta_generator_shape.py`：3 个用例
  （`acceptance-N` 需求名被拒 / `capability-N` 被拒 / 恒真 WHEN 被拒）⇒ 修复前红（当前照常生成）⇒ 修复后绿；
- [ ] **AC8（载体类 · 依裁决可机判 · 豁免先红）** 用例：improvement 提供了**语义要求**（载体依 design 裁决：
  粗体头行 / 新增段 / AC 行内命名约定，三选一）⇒ delta 的 Requirement 名**语义化**且 Scenario 的 WHEN **等于作者文本**
  ⇒ 两种裁决各有一组可机判断言；⚠ 「合法输入长什么样」必须由 design 固定 ⇒ 否则本 AC 不可实施；
- [ ] **AC9（载体类 · 依裁决可机判 · 豁免先红）** 用例：improvement 声明 `delta: modified <cap>` ⇒ 首行
  `## MODIFIED Requirements` + 目录落 `specs/<cap>/`；MODIFIED 块缺既有 Scenario ⇒ **拒绝生成**；
  ⚠ **缩减预案**：若 design 裁决「落点目录语义**不改**」⇒ 本 AC 只保留「首行 `## MODIFIED` + Scenario 守恒」两断言；
  ⚠ **载体裁决**：声明放 YAML frontmatter 还是粗体头行（design 落定）⇒ 两种载体各有一组断言；
- [ ] **AC10（功能类 · 单一真源）** 断言形态判据来自共享模块：`tests/unit/test_spec_requirement_form.py` 与生成器
  **导入同一模块**（守卫用例断言两处引用同一常量）⇒ 不成立即红；
- [ ] **AC11（功能类 · 红→绿）** 新建 `tests/unit/test_rdd_builder_skill_contract.py`：断言
  `skills/rdd-builder/SKILL.md` 含 delta 契约段的**三个具体锚点**（① 载体 ② MODIFIED 保留既有 Scenario ③ 版本口径）
  ⇒ 缺任一锚点即红（禁「存在即通过」）；
- [ ] **AC12（功能类 · 变异）** 把共享模块的 `acceptance-N` 正则退回不匹配 ⇒ **本轴 AC7** 必须红（判别力证明）；
- [ ] **AC13（功能类 · 红→绿+变异）** 新增用例：版本探测（纯 stdlib，`openspec --version` 语义化解析）
  ⇒ `<1.7.0` 分支下 `missing == ∅` 守卫**同样生效**；⚠ **变异腿**：把版本比较退化为**字符串比较**
  （`1.14.3 < 1.7.0` 为真 ⇒ 走错分支）⇒ 必须红；⚠ 版本探测机制本身**当前仓内不存在** ⇒ 本 AC 含其**存在性**；
- [ ] **AC14（功能类 · 红→绿）** 新增用例：delta 拒绝生成 ⇒ **不留空文件**（`phase0_approval.sh` 的
  `> "$DELTA_FILE"` 重定向会留空文件 ⇒ 改为临时文件 + 成功后 `mv`）、**proposal 不落半成品**、
  **重试可再生成**（`[ ! -f "$DELTA_FILE" ]` 的幂等检查不得被空文件永久骗过）⇒ 修复前红 ⇒ 修复后绿。

### 跨轴（合并的集成面）

- [ ] **AC15（功能类 · 红→绿）** 新增集成用例：同一 improvement 同时命中两轴（范围节纯表格 + `delta: modified` 声明）
  ⇒ 一次 P0 跑出**两份都正确**的产物（proposal 的 Scope 无碎片 + delta 为 MODIFIED 且 Scenario 守恒）
  ⇒ 修复前红 ⇒ 修复后绿（14 条单轴单测**不覆盖**此面 ⇒ 本 AC 不可省）。

## Capabilities

**轴 1（U1）**：

- MUST: 纯表格 / 混排 / 带注解标题的「范围节」被正确解析成 In/Out Scope 条目，条目内无 `|` 与换行碎片。
- MUST: Out of Scope 段在任何形态下**只出现一次**。
- MUST: 语料回归以 **golden snapshot** 断言（期望输出入库 + 形态标签表 + 动态计数）。
- MUST NOT: 用逗号切分猜条目（兜底删除 ⇒ 猜不出来就保留原文 + 提示）。
- MUST NOT: 改动 `_extract_bullet_items` / `_split_capabilities_impact` / 既有 improvement 的内容。

**轴 2（U2）**：

- MUST: delta 为 **opt-in**（未声明不生成、不算失败）；声明后形态退化（无语义 Requirement 名 / 恒真 WHEN）在**生成时**被拒绝。
- MUST: 声明 `delta: modified <capability>` 的 change 生成 `## MODIFIED Requirements`，且**保留既有全部 Scenario**。
- MUST: 形态判据与守卫测试**同源**（单一实现）。
- MUST: delta 拒绝生成时**不留空文件、不留半成品**，且重试可再生成。
- MUST: openspec 版本按**语义化**比较分流守卫实现。
- MUST NOT: 用第二套判据实现形态检查；不得把「手工重写 delta」留给归档期。
- MUST NOT: 改 ADR-0025 的 D2 固定段映射契约；不得静默改写 improvement 的 AC 文本。

## Impact

| 面 | 影响 | 轴 |
|---|---|---|
| `skills/rdd-builder/scripts/generate_full_proposal.py` | 解析逻辑（header 正则 / item 解析 / 兜底删除）+ `generate_spec_delta()` 形态自检与 MODIFIED 生成 | U1+U2 |
| `skills/rdd-builder/scripts/phase0_approval.sh` | delta 落点目录语义 + 临时文件/mv 半成品防护 + 拒绝时的非零退出 | U2 |
| `skills/rdd-builder/SKILL.md` | 新增 delta 契约段（载体 / MODIFIED 守恒 / 版本口径） | U2 |
| `_lib/spec_requirement_form.py`（新）+ `tests/unit/test_spec_requirement_form.py` | 形态判据单一真源 | U2 |
| `tests/unit/` | 新增 `test_generate_full_proposal_scope_table.py` / `test_generate_full_proposal_corpus.py` / `test_spec_delta_generator_shape.py` / `test_spec_delta_generator_modified.py` / `test_rdd_builder_skill_contract.py` | U1+U2 |
| `openspec/changes/*/specs/` | 落点目录语义变更（**新旧并存**，既有 change 不迁） | U2 |
| ADR / 契约 | 载体入口沿 ADR-0025 D6 的「头部」定义；落点目录语义变更需 **ADR Status Update**（机制面） | U2 |

## metis 结论（2026-11-27 · 本轮 1 轮覆盖本稿（合并稿）· 载体=头部段）

> 本轮针对**合并稿**独立复核（此前两轮覆盖的是合并前的两份源草稿）。metis 给出 3 blocker + 10 项 high/medium，
> 逐条处置如下（**已改**= 本稿已改；**design 裁决**= 判据形态在本稿固定、答案在 change 的 design.md 落）。

| # | metis 指出 | 处置 |
|---|---|---|
| B1 | **AC 编号未真正重排**（合并说明声称做了）⇒ 3 处引用悬空（轴2 AC3/AC6、轴1 AC5） | ✅ **已改**：轴 2 → **AC7–AC14** 真实重排；3 处引用改为「本轴 AC7」「本轴 AC1」等显式指代 |
| B2 | **轴 A「放行」载体未定义** ⇒ 形态守卫会拒绝 100% 输入，AC7/AC8 不可实施 | ✅ **已改**：§技术约束「载体裁决」把「语义要求载体」列为 design 裁决项并规定**判据形态**（缺载体 ⇒ 拒绝并指名）；AC8 改成「依裁决可机判 · 豁免先红」+ 明写「合法输入长什么样必须由 design 固定，否则本 AC 不可实施」 |
| B3 | **`delta:` 头部字段载体未裁决**（YAML frontmatter vs 粗体头行；生成器纯 stdlib；D6 的「头部」= 粗体头行） | ✅ **已改（design 裁决）**：§技术约束「载体裁决」列两候选 + stdlib 约束 + 与 D6 对齐的默认候选（粗体头行）；AC9 写成两种载体各一组断言 |
| H1 | **phase0 半成品陷阱**：`> "$DELTA_FILE"` 拒绝时留**空文件** ⇒ 重试 `[ ! -f ]` 永久跳过 delta 生成 | ✅ **已改**：范围 In Scope 新增「半成品防护（临时文件 + mv）」+ **AC14**（不留空文件 / proposal 不落半成品 / 重试可再生成） |
| H2 | **表格归属规则与既有 spec 冲突**（纯表格 vs bullet 下表格） | ✅ **已改**：范围 In Scope 写明判别规则（纯表格节 ⇒ 行成条目；bullet 下表格 ⇒ 归 bullet，**不改**既有 spec 语义）+ 场景 2 措辞修正 |
| H3 | **缺「标题优先级」AC**，且草稿把 bug 描述当 fix 依据引用 | ✅ **已改**：新增 **AC6**（并存取 `## 范围` + stderr 提示；仅有 What Changes 取它）+ 措辞改为「同源现象的参考，不是裁决依据」 |
| H4 | **AC4 是假门**（形态分类器不存在 + 语料路径错 + 快照基线时点倒置 + 自引用） | ✅ **已改**：改为 **golden snapshot**（期望输出入库）+ **行首形态标签表**（机判）+ 路径改**仓根相对** + 快照基线 = 修复后 + 语料增长口径（同 PR 刷新）+ 自引用说明（本稿在语料内，正常）；AC4 补变异腿（改标签分类器 ⇒ 红） |
| H5 | **版本探测机制不存在**（仓内零检测代码） | ✅ **已改**：范围新增「openspec 版本探测机制」项；AC13 明确含其**存在性** + 变异腿（版本比较退化为字符串比较 ⇒ 红） |
| H6 | **缺跨轴集成 AC** | ✅ **已改**：新增 **AC15**（同一 improvement 同触两轴 ⇒ 一次 P0 两份都正确）+ 关键场景 7 |
| M1 | 拼接痕迹（孤立 `:` 行 / Impact 重复行 / 「ADR SU」未定义） | ✅ **已改**：合并稿为**整体重写**（非拼接）⇒ 孤立行消失；Impact 表去重；「ADR SU」展开为 **ADR Status Update** |
| M2 | `validate_delta_targets.py` **仓内无可执行调用方**（「只接线」低估） | ✅ **已改**：范围写明接线点 = **P0 生成时**（本地预检目标存在 + Scenario 守恒）+ P3 复用；Out of Scope 注明「不改其既有语义」 |
| M3 | TDD 三段 blanket 声明与内容不符（回归/门类无红态） | ✅ **已改**：§验收标准抬头改为「功能类三段；回归/门类豁免变异腿（注明理由）；载体类豁免先红（注明依赖 design 裁决）」，并逐条归类（AC3/AC6/AC7/AC8/AC9 等已标注类别） |
| M4 | 两份源草稿处置未声明（语料三份并存 / 可能被重复拾取） | ✅ **已改**：合并说明新增「源草稿处置」段（已标「已合并」+ 移出提案池 ⇒ 不再被拾取；三份同在语料内属正常） |
| M5 | **内部落地序未声明** | ✅ **已改**：§技术约束「跨轴（合并的内部落地序，强制）」：U1 → 语料 golden snapshot → U2 |
| L1 | frontmatter 审查日期 | ✅ 已改（2026-11-27） |
| L2 | AC11 测试文件名二选一未定 | ✅ **已改**：落定 **新建** `tests/unit/test_rdd_builder_skill_contract.py`（仓内无现成 SKILL 内容锚点测试） |

⚠ **本稿仍未闭合、需在 change 的 design.md 落裁决的 4 项**（AC 判据形态已固定，**答案未定**）：
① 载体 = 粗体头行 vs YAML frontmatter；② 语义要求载体 = 新增段 vs AC 行内命名约定；
③ delta 落点目录语义 = 改 vs 不改（AC9 缩减预案已写）；④ `## 范围` vs `## What Changes` 并存语义（AC6 已锁现状候选序）。
⇒ 这 4 项**不阻塞**立项（AC 已写成「依裁决可机判」），但**必须在 P1 的 design.md 落定**，否则 AC8/AC9 不可实施。
