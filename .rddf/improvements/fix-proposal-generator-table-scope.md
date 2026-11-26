---
优先级: P0
来源: 2026-11-26 CppTLM 立项会话（session ses_de7dcca7fffeOvO830nfolajk4，change `cep-ssp-cp-q1b-landing`）实测复现 + oracle/critic 双审（治理面 batch，2026-11-26）
阶段: phase-3
分类: cli-tooling
类型: improvement
状态: 待审查
主题: proposal 生成器的「范围节」解析 —— 纯表格形态被逗号兜底切碎 + Out 段整段重复
---

**优先级**: P0 | **来源**: 2026-11-26 CppTLM 立项会话实测 | **阶段**: phase-3 | **分类**: cli-tooling | **类型**: improvement

## metis 结论（2026-11-27 · 本轮 1 轮覆盖 9 份草稿 · 载体=头部段）

- **计数写死是落地即过期**：草稿写「295 份」，实测 **304** 且仍在增长 ⇒ 改为**动态计数**（快照头写 `generated_at` + `corpus_count`）。
- **白名单若是文件清单 ⇒ 判别力为零**（实施者把新差异加进白名单即过）⇒ 白名单必须是「**修复形态枚举**」（纯表格 / 带注解标题），且白名单变更需单独审查。
- 快照入库后每新增一份 improvement 即过期 ⇒ 需漂移检出（快照头字段）。
- 已改：AC4 增「清空白名单 ⇒ 必须红」的判别力行；快照自带头；全文去掉写死份数。


**主题**: proposal 生成器的「范围节」解析 —— 纯表格形态被逗号兜底切碎 + Out 段整段重复

## 架构依据

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

## 范围

**In Scope**:

- `generate_full_proposal.py`：① `_SCOPE_HEADER_RE` 容忍标题尾部括号/方括号注解（`**In Scope（6 项）**`）；
  ② `_extract_scope_items` 识别 markdown 表格行（`| a | b |`）⇒ 每行成一个条目（去掉对齐行 `|:--|--:|`）；
  ③ **删除逗号兜底**（`:238-243`）—— 解析不出条目时**保留原文**并在 stderr 提示，**不猜**；
- `## 范围` → `## What Changes` 的标题优先级：`## 范围` 优先于 `## What Changes`（现由 `_extract_section` 的候选序决定，
  需显式固定并加用例，见 `fix-bats-per-file-timeout.md:411` 记录的同一现象）；
- 回归用例（新增）：纯表格节 / 表格+bullet 混排 / 标题带括号注解 / 表格内含逗号 / Out 段重复 5 组。

**Out of Scope**:

- 不改 `_extract_bullet_items`（技术约束 → Capabilities/Impact 的路径，已由 `fix-generator-scope-extraction` 覆盖）；
- 不改 `## What Changes` 的段落模板结构（除 In/Out Scope 块）；
- 不改 `_split_capabilities_impact`（`SHOULD` 混入 Capabilities 的既有偏差，`fix-generator-scope-extraction` 已登记为「未修」）；
- 不动既有 295 份 improvement 的**内容**（只读回归语料）。

## 关键场景

1. 范围节为纯表格 ⇒ In Scope 每行一个条目，条目内**不含** `|` 与换行碎片；Out Scope 只出现一次。
2. 范围节为表格 + bullet 混排 ⇒ 表格行与 bullet 各成条目，互不吞并。
3. 标题为 `**In Scope（6 项 · contract 面）**` ⇒ 识别为标题，不成为条目。
4. 表格单元格内含逗号 ⇒ 不被切碎（逗号兜底已删除 ⇒ 这类文本只会出现在表格行内）。
5. 范围节无法解析出任何条目 ⇒ proposal 的 `## What Changes` 保留原文 + stderr 一行提示，**不产出错乱条目**。

## 技术约束

- 语料回归：全量 improvement（**动态计数**）跑一遍生成器，**逐份 diff** 生成结果；
  ⚠ **白名单必须是「修复形态枚举」**（哪类形态允许变：纯表格 / 带注解标题），**不得**是文件清单
  （文件清单可随同一 PR 修改 ⇒ 判别力为零）；白名单**变更需单独审查**；
- 快照文件自带头：`generated_at` + `corpus_count`（glob 实测）+ 白名单形态枚举 ⇒ 快照漂移可检出；
- 判定「条目数不减」**不作为验收**（碎成渣也算不减）⇒ 验收改用「条目内不含 `|` / 换行碎片」+「逐份 diff 差异白名单」；
- 生成器不引入新依赖；纯 Python 3 stdlib；
- 兜底删除后，所有**依赖逗号切分**的历史 improvement 会改变输出 ⇒ 必须逐份 diff 并把差异登记在案（不得静默）。

## 验收标准

- [ ] **AC1（红→绿）** 新增 `tests/unit/test_generate_full_proposal_scope_table.py`：5 个用例
  （纯表格节 / 表格+bullet 混排 / 标题带括号注解 / 表格内含逗号 / Out 段重复）⇒ **先红**（当前实现产出碎条目与重复段），
      修复后 **全绿**；
- [ ] **AC2（红→绿）** 同文件新增用例：范围节无法解析出条目时 ⇒ 生成结果保留原文且 stderr 含提示，**不**出现逗号切碎片段
      ⇒ 修复前红（当前会切碎）⇒ 修复后绿；
- [ ] **AC3（回归）** `tests/unit/test_generate_full_proposal.py` 现有用例**零回归**（`python3 -m pytest tests/unit/test_generate_full_proposal.py -q` 全绿）；
- [ ] **AC4（语料）** 新增 `tests/unit/test_generate_full_proposal_corpus.py`：对 `../.rddf/improvements/*.md`
      全量生成并逐份与基线快照 diff，**差异形态集合 ⊆ 白名单形态枚举**（枚举的是**形态**不是文件名）；
      快照文件入库且自带 `generated_at` + `corpus_count`（**动态计数**，不写死份数）；
      ⚠ 判别力：把白名单形态清空 ⇒ 用例必须红（证明它不是「文件清单可随 PR 改」的假判据）；
- [ ] **AC5（变异）** 把 `_extract_scope_items` 的表格识别退回「只认 bullet」⇒ **AC1 的纯表格用例必须红**（证明用例有判别力）；
- [ ] **AC6（门）** `./test.sh --gates` 与 `./test.sh --unit` 全绿。

## Capabilities

- MUST: 纯表格 / 混排 / 带注解标题的「范围节」被正确解析成 In/Out Scope 条目，条目内无 `|` 与换行碎片。
- MUST: Out of Scope 段在任何形态下**只出现一次**。
- MUST NOT: 用逗号切分猜条目（兜底删除 ⇒ 猜不出来就保留原文 + 提示）。
- MUST NOT: 改动 `_extract_bullet_items` / `_split_capabilities_impact` / 既有 improvement 的内容。

## Impact

| 面 | 影响 |
|---|---|
| `skills/rdd-builder/scripts/generate_full_proposal.py` | 三处解析逻辑（header 正则 / item 解析 / 兜底删除） |
| `tests/unit/` | 新增 2 个测试文件 + 语料基线快照 |
| 既有 improvement（295 份） | 只读语料；输出差异逐份登记 |
| ADR / 契约 | 无（生成器内部行为修正，不改 D2 段映射契约） |
