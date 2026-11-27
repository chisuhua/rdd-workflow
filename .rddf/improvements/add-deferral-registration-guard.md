---
优先级: P1
来源: 2026-11-26 oracle 审查（「另案立项」第 3 次记录却从未立项）+ 2026-11-27 critic 复审（SHOULD_FIX 8）
阶段: phase-3
分类: quality-gate
类型: improvement
状态: 已批准·待立项（planner 2026-11-27 · W4 = U6 · 独立 change · 约定先行 + doctor category · 7 条 AC 含 TDD 三段）
主题: 「另案立项」的登记载体 —— deferral 必须写清目标 slug 或 backlog 占位，否则不算立项
---

**优先级**: P1 | **来源**: 2026-11-26 oracle 审查 | **阶段**: phase-3 | **分类**: quality-gate | **类型**: improvement

## metis 结论（2026-11-27 · 本轮 1 轮覆盖 9 份草稿 · 载体=头部段）

- **AC3「约定文本存在」是假判据**（写一句空话也过）⇒ 改为断言**两个可 grep 锚点**：措辞清单 + 豁免格式。
- **AC4 语义写反**（「同一文件同时命中两者 ⇒ 用例红」）⇒ 改为「**同一条 deferral 不被两个 category 重复报告**」，并与既有 `add-proposal-defer-support.md`（**推迟状态字段**）划界（禁共用措辞集）。
- **第一步（约定）没有自己的收口判据**（AC 全压在第二步）⇒ 约定段的两个锚点即第一交付物的收口判据。
- **豁免清单漂移未处理**（条目不再命中 ⇒ 清单腐坏）⇒ 新增 AC6：豁免未命中 ⇒ 提示清理。
- 已改：AC3 两锚点；AC4 语义与划界；新增 AC6；AC6→AC7 顺延。


**主题**: 「另案立项」的登记载体 —— deferral 必须写清目标 slug 或 backlog 占位

## 架构依据

rdd-workflow 里「本次不做 / 另案立项」是**高频**的合法收口方式，但**没有载体要求** ⇒
被 deferral 的缺陷可以无限期悬空。实证：

- `fix-spec-v3-naming-sync.md:192` 记「第三次撞上同一堵墙…根因确在 `generate_spec_delta()`，**另案立项**」——
  **至今没有对应的 improvement 文件** ⇒ 该缺陷在 2026-11-26 的第 4 次复发（`fix-spec-delta-generator-shape-and-semantics`）；
- `fix-bats-per-file-timeout.md:411` 同样以「工具缺陷另案」收口 ⇒ 同一缺陷在 2026-11-26 第 2 次出现。

⇒ **「另案」没有登记载体 = 缺陷没有欠账条目** ⇒ 复发不可见、优先级不可排。

## delta 载体（P0 生成输入）

**delta**: added deferral-registration
**语义要求**: Deferral statements SHALL carry a registration target | Every deferral statement in improvement or review documents (`另案` / `另立` / `另行立项` / `后续另案`) SHALL immediately name a registration target: `另案（已登记：<improvement-slug>）` or `另案（backlog：<topic>）`. `rddf doctor` SHALL report one warning naming the file and the line when a deferral carries no target, and SHALL stay silent for registered deferrals and for the recorded exemption list. | An unregistered deferral is reported | an improvement document contains a deferral statement without a registration target | `rddf doctor` runs | it reports one warning naming the file and the line

## 范围

**In Scope**:

- **先立命名约定**（本提案的第一交付物，先于任何扫描实现；**它自己也要有收口判据** ⇒ 见 AC3 的两个锚点）：
  任何「另案 / 另立 / 另行立项 / 后续另案」措辞处，**必须**紧跟目标标识：
  `另案（已登记：<improvement-slug>）` 或 `另案（backlog：<一句话主题>）`；二者都没有 ⇒ 视为**未登记**；
- `rdd-doctor` 新 category（`deferral-registration`）：扫 improvement / review 文档里的 deferral 措辞，
  无目标标识 ⇒ WARNING；措辞清单与**豁免格式**随约定一并登记；
- 与既有 doctor category 划界：`detect-suggestions-approved-inconsistency` 管「suggestions ↔ approved 一致性」，
  本 category 管「deferral 措辞 ↔ 目标载体」—— 两者**不重叠**；
- 回归用例：3 个 fixture（合规 deferral / 无标识 deferral / 豁免格式）。

**Out of Scope**:

- 不自动创建 improvement 文件（只报警，不代写）；
- 不改 improvement 的生命周期状态机；
- 不扫描代码注释里的 TODO（只扫文档里的 deferral 措辞）；
- 不改既有文档里已存在的无标识 deferral（存量只登记豁免清单，不回改）。

## 关键场景

1. 文档写「另案（已登记：fix-foo）」且 `improvements/fix-foo.md` 存在 ⇒ doctor 绿。
2. 文档写「另案」但无任何目标标识 ⇒ doctor 报 WARNING（指出文件 + 行号 + 缺什么）。
3. 文档写「另案（backlog：xxx）」⇒ doctor 绿（允许 backlog 占位）。
4. 存量文档里的历史无标识 deferral ⇒ 豁免（清单随本提案登记），不产生噪音。

## 技术约束

- **约定先行**：扫描实现必须排在约定之后 ⇒ 本提案的实现分两步，**第一步（约定）即可独立收口**；
- 扫描面**只限文档**（`.rddf/improvements/**` / `.rddf/reviews/**`），不含代码注释；
- 豁免清单入库（存量噪音一次性登记），不静默忽略；
- doctor category 的退出码与既有 category 一致（WARNING 不阻断）。

## 验收标准

- [ ] **AC1（红→绿）** 新增 `tests/unit/test_deferral_registration.py`：3 个 fixture
      （合规 deferral ⇒ 无 finding / 无标识 deferral ⇒ 1 条 WARNING 且含文件与行号 / backlog 占位 ⇒ 无 finding）
      ⇒ 修复前红（无扫描）⇒ 修复后绿；
- [ ] **AC2（红→绿）** 同一测试：存量豁免清单里的条目**不**产生 finding（噪音为零）；
- [ ] **AC3（约定落盘）** 断言约定文本含**两个可 grep 的具体锚点**（禁「存在即通过」）：
      ① deferral **措辞清单**（`另案` / `另立` / `另行立项` / `后续另案`）② **豁免格式**（`另案（已登记：<slug>）` /
      `另案（backlog：<主题>）`）⇒ 缺任一锚点即红（由既有 SKILL/文档契约测试断言）；
- [ ] **AC4（划界）** 断言**同一条 deferral 不被两个 category 重复报告**：
      本 category 命中「deferral 措辞」，`detect-suggestions-approved-inconsistency` 命中「suggestions ↔ approved 不一致」
      ⇒ 一条 deferral 若只命中其一 ⇒ 无重复报告；两处检测面**互斥**（用例红）；
      ⚠ 另需与既有 `add-proposal-defer-support.md`（**推迟状态字段**）划界：那是「状态字段推迟」，本条是「缺陷欠账登记」
      ⇒ 断言两者不共用措辞集；
- [ ] **AC5（变异）** 把扫描的措辞正则改窄 ⇒ AC1 的第 2 个 fixture 必须红（判别力证明）；
- [ ] **AC6（豁免漂移）** 断言豁免清单里的条目**已不再命中**时 doctor 给出「可清理」提示（清单不静默腐坏）；
- [ ] **AC7（门）** `./test.sh --gates` 与 `./test.sh --unit` 全绿。


## Capabilities

- MUST: deferral 措辞必须带目标标识（improvement slug 或 backlog 占位），否则被 doctor 检出。
- MUST: 约定文本独立可 grep（不只存在于代码注释里）。
- MUST NOT: 自动代替作者创建 improvement（只报警）。
- MUST NOT: 存量噪音反复出现（豁免清单一次性登记）。

## Impact

| 面 | 影响 |
|---|---|
| `docs/` 或 `skills/rdd-planner/SKILL.md` | 命名约定（本提案第一交付物） |
| `skills/rdd-doctor/` | 新 category `deferral-registration` |
| `tests/unit/` | 新增 1 个测试文件 + 3 个 fixture |
| 存量文档 | 豁免清单一次性登记 |
