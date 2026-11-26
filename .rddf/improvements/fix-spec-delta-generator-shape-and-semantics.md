---
优先级: P0
来源: 2026-11-26 CppTLM 立项会话（session ses_de7dcca7fffeOvO830nfolajk4）实测 —— delta 语义错 + 形态退化第 4 次复发 + oracle/critic 双审（2026-11-26）
阶段: phase-3
分类: cli-tooling
类型: improvement
状态: 已合并
主题: spec delta 生成器 —— 形态退化（acceptance-N / 恒真 WHEN）前移到生成时 + 语义轴（ADDED → MODIFIED）
---

**优先级**: P0 | **来源**: 2026-11-26 CppTLM 立项会话实测 | **阶段**: phase-3 | **分类**: cli-tooling | **类型**: improvement

## metis 结论（2026-11-27 · 本轮 1 轮覆盖 9 份草稿 · 载体=头部段）

> ⚠ **本稿已合并**（2026-11-27）⇒ 本单元并入 `fix-proposal-generator-output-fidelity`（轴 2（delta 形态/语义）），与另一轴合成**一个** openspec change（同文件 `generate_full_proposal.py`）⇒ 本稿**不再单独立项**；原文与结论全部保留，仅作历史留痕。

- **`<1.7.0` 分支在 CI 不会自然触发**（本仓 pin `openspec-cli >= 1.7.0`）⇒ 必须用**版本 mock / 分支注入**测，否则该分支腐烂；版本比较须语义化（`1.14.3 > 1.7.0`）。
- **AC3 的 fixture 来源未定**（本仓活规范是临时构造）⇒ 用测试内建 fixture。
- **「落点目录语义须 design 裁决」是条件性范围** ⇒ 必须写「裁决为不改 ⇒ AC3 缩减预案」，否则 AC 半失效。
- **AC5「含 delta 契约段」是存在即通过的假判据** ⇒ 改为断言**三个具体锚点**。
- 已改：AC3 增 fixture 来源 + 缩减预案；AC5 改三锚点；新增 AC7（版本分支有真实执行）；AC7→AC8 顺延。


**主题**: spec delta 生成器 —— 形态退化（`acceptance-N` / 恒真 WHEN）前移到生成时 + 语义轴（`ADDED` → `MODIFIED`）

## 架构依据

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

**In Scope**:

- **轴 A（形态）**：生成器在产出 delta 前**自检**形态 —— 出现 `acceptance-N` / `capability-N` 需求名或恒真 WHEN ⇒
  **拒绝生成并报错**（exit ≠ 0），要求 improvement 提供可转写的语义需求名；
  判据**抽共享模块**（`tests/unit/test_spec_requirement_form.py` 的三条正则）⇒ 生成器与测试**同源**，禁复制第二份；
- **轴 B（语义）**：improvement **头部字段**声明 delta 目标（如 `delta: modified <capability>`，沿 ADR-0025 D6 的头部元数据机制）；
  生成器据此输出 `## MODIFIED Requirements` + 目录落 `specs/<target-capability>/`；
  MODIFIED 块**逐字复制** main spec 中该 requirement 的全部 Scenario（缺失 ⇒ 拒绝生成）；
- `skills/rdd-builder/SKILL.md`：补 delta 契约文档（当前 454 行**零次**提到 MODIFIED/ADDED/delta），
  含「声明载体在 improvement 头部」「MODIFIED 必须保留既有 Scenario」「按项目 openspec 版本选择守卫实现」；
- 守卫接线：优先复用既有 `_lib/validate_delta_targets.py`（只校验 MODIFIED/RENAMED 目标存在性），**不新造第二套**。
- **版本分支的可测性**：本仓 pin `openspec-cli >= 1.7.0` ⇒ CI 永远走原生检查路径；`<1.7.0` 分支**必须**用
  **版本 mock / 分支注入**测（禁靠真实旧版本），否则该分支长期无执行 ⇒ 腐烂；版本比较必须**语义化**
  （`1.14.3 > 1.7.0` 成立，字符串比较会错）。

**Out of Scope**:

- 不改 ADR-0025 D2/D3 的段映射契约（只新增**头部字段**这一入口，不扩固定段落映射）；
- 不改 openspec 自身（外部工具）；不改 `openspec/specs/**` 既有活规范；
- 不做「自动把 improvement 的 AC 改写成语义 requirement 名」⇒ 那是 improvement 作者的职责（生成器只做拒绝与放行）；
- 不改 `validate_delta_targets.py` 的既有语义（只接线）。

## 关键场景

1. improvement 无 `delta:` 声明 ⇒ 生成 `## ADDED Requirements`（现状不变），且形态自检通过 ⇒ 正常落盘。
2. improvement 声明 `delta: modified cep-core-contracts` ⇒ 生成 `## MODIFIED Requirements`，
   目录 `specs/cep-core-contracts/`，requirement 名与 main spec **精确同名**。
3. MODIFIED 块缺 main spec 中任一既有 Scenario ⇒ **拒绝生成**（stderr 指名缺哪个），不落半成品。
4. improvement 的 AC 只能转写成 `acceptance-N` ⇒ **拒绝生成**（形态退化守卫），报「请提供语义需求名」。
5. 项目 openspec 版本 < 1.7.0（无原生场景守恒检查）⇒ 守卫**自实现** `missing == ∅`（允许新增场景），
   与 1.7.0+ 的原生检查**判据等价**。

## 技术约束

- 判据单一真源：形态三条正则抽到共享模块（如 `_lib/spec_requirement_form.py`），生成器与
  `tests/unit/test_spec_requirement_form.py` **同源导入**；禁在生成器内另写一份（两处实现 ⇒ 漂移）；
- 版本口径：守卫实现按项目实际 openspec 版本选择（≥1.7.0 复用原生 archive 检查 + 本地预检；<1.7.0 自实现）；
  CppTLM 当前 pin `1.14.3`（`.openspec-cli-version`）⇒ 原生检查可用；
- 落点目录语义变更（`specs/<change-name>/` → `specs/<target-capability>/`）属**契约面** ⇒ 须在 design 阶段显式裁决，
  并同步 `phase0_approval.sh` 与 `validate_delta_targets.py` 的目标解析；
- 生成器不引入新依赖；纯 stdlib。

## 验收标准

- [ ] **AC1（红→绿）** 新增 `tests/unit/test_spec_delta_generator_shape.py`：3 个用例
  （`acceptance-N` 需求名被拒 / `capability-N` 被拒 / 恒真 WHEN 被拒）⇒ 修复前红（当前照常生成）⇒ 修复后绿；
- [ ] **AC2（红→绿）** 同文件用例：形态合法（语义需求名 + 真实 WHEN）⇒ 正常生成，无误拒（防过度拦截）；
- [ ] **AC3（红→绿）** 新增 `tests/unit/test_spec_delta_generator_modified.py`：3 个用例
  （声明 `delta: modified <cap>` ⇒ 首行 `## MODIFIED Requirements` + 目录落 `specs/<cap>/` /
      MODIFIED 块缺既有 Scenario ⇒ 拒绝生成）⇒ 修复前红 ⇒ 修复后绿；
      ⚠ **fixture 来源**：用测试内建 fixture（临时构造 capability），**不依赖**真实活规范；
      ⚠ **缩减预案**：若 design 裁决「落点目录语义**不改**」⇒ AC3 只保留「首行 `## MODIFIED` + Scenario 守恒」
      两断言，目录断言移出（**条件性范围必须显式**，否则 AC 半失效）；
- [ ] **AC4（单一真源）** 断言形态判据来自共享模块：`tests/unit/test_spec_requirement_form.py` 与生成器
      **导入同一模块**（守卫用例断言两处引用同一常量）⇒ 不成立即红；
- [ ] **AC5（文档）** `skills/rdd-builder/SKILL.md` 含 delta 契约段（含「声明载体 = improvement 头部」「MODIFIED 保留既有 Scenario」
      「版本口径」三锚点）⇒ 由 `tests/unit/test_skill_docs_contract.py`（或既有 SKILL 契约测试）断言，缺任一锚点即红；
- [ ] **AC6（变异）** 把共享模块的 `acceptance-N` 正则退回不匹配 ⇒ AC1 用例必须红（判别力证明）；
- [ ] **AC7（版本分支）** 用例：`<1.7.0` 分支（版本 mock / 分支注入）下 `missing == ∅` 守卫**同样生效**
      ⇒ 该分支有真实执行（防腐烂）；
- [ ] **AC8（门）** `./test.sh --gates` 与 `./test.sh --unit` 全绿。

## Capabilities

- MUST: 形态退化（无语义 Requirement 名 / 恒真 WHEN）在**生成时**被拒绝，不再流入归档期手工重写。
- MUST: 声明 `delta: modified <capability>` 的 change 生成 `## MODIFIED Requirements`，且**保留既有全部 Scenario**。
- MUST: 形态判据与守卫测试**同源**（单一实现）。
- MUST NOT: 用第二套判据实现形态检查；不得把「手工重写 delta」留给归档期。
- MUST NOT: 改 ADR-0025 的 D2 固定段映射契约；不得静默改写 improvement 的 AC 文本。

## Impact

| 面 | 影响 |
|---|---|
| `skills/rdd-builder/scripts/generate_full_proposal.py` | `generate_spec_delta()` 形态自检 + MODIFIED 生成 |
| `skills/rdd-builder/scripts/phase0_approval.sh` | delta 落点目录语义 + 拒绝时的非零退出 |
| `skills/rdd-builder/SKILL.md` | 新增 delta 契约段 |
| `_lib/spec_requirement_form.py`（新） + `tests/unit/test_spec_requirement_form.py` | 形态判据单一真源 |
| `openspec/changes/*/specs/` | 落点目录语义变更（契约面 ⇒ design 阶段显式裁决） |
| ADR / 契约 | 头部字段入口沿 ADR-0025 D6；落点目录语义变更需 ADR SU |
