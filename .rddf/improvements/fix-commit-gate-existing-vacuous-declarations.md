---
优先级: P2
来源: 2026-11-28 metis 审稿 P2#11（`fix-commit-gate-generator-fake-green` 的 Out of Scope 尾项，按 add-deferral-registration-guard 升级为登记稿）
阶段: phase-3
分类: quality-gate
类型: improvement
状态: 待审查
主题: 存量恒绿声明（生成器修好后仍留在仓里的那批）的可复核面
---

**优先级**: P2 | **来源**: metis 审稿 P2#11 | **阶段**: phase-3 | **分类**: quality-gate | **类型**: improvement

**主题**: 存量恒绿声明（生成器修好后仍留在仓里的那批）的可复核面

## 架构依据

`fix-commit-gate-generator-fake-green` 只堵**新产出**：脚本类入口不再被自动推导。
修好后**既有**声明仍是恒绿 —— 作者手写的、或旧版生成器产出的 `[["./test.sh"]]` 之类。

本仓的存量已手工修正（`.rddf/commit-gate.json` = `./test.sh --gates` + `./test.sh --quick`，
commit `554c821a`）；**外部使用方仓（CppTLM 等）未知**，且今日无任何面能报出来
（`rddf doctor --category commit-gate` 的三面都不覆盖：①未声明 ②空壳枚举 `{true,echo,:,exit 0}` ③未 tracked）。

**为什么不能直接加一条 doctor 判据**（metis 已论证，本稿必须先解决它）：
「裸脚本入口是否真的执行验证」**不可静态判定**（空脚本 / `echo ok` / `--if-present` / 空配方 / 零测试件都形态各异）；
而工具链入口（`npm test` / `pytest` / `go test ./...` / `cargo test`）对多数仓**本身就是合法的全量验证**
⇒ 一条「裸入口就报警」的规则会大面积误报，把真信号淹掉。

## 范围

**In Scope**：

- **先裁决判据**（design 阶段），要求同时满足：
  - **可机判**（禁「读脚本源码猜行为」）；
  - **零误报于工具链全量入口**（`npm test` / `pytest` / `go test ./...` / `cargo test` 不得被报为可疑）；
  - **落点二选一并写明理由**：① `rdd doctor` 新面（若选它，必须与既有三面**互斥**且不改 `is_shell_declaration` 的枚举）
    ② 一次性审计 CLI（`rddf commit-gate audit` 之类，输出「待人工确认」清单，不写状态）；
- 实施裁决出的判据 + 测试（含**反例** fixture：合法的 `npm test` 声明不得被报）。

**Out of Scope**：

- 不自动改写任何存量声明（只报 / 只列）；
- 不动 `is_shell_declaration` 的枚举（`{true, echo, :, exit 0}`）；
- 不改 D3 / 三判据语义；
- 不扫代码库里的测试脚本内容（禁读行为）。

## 关键场景

1. 仓里有 `[["./test.sh"]]` 且 `test.sh` 无参只打印 help ⇒ 被列进「待确认」清单（人工判定后手改声明）。
2. 仓里声明 `[["npm","test"]]` 且 `package.json::scripts.test` 是真测试命令 ⇒ **不得**被报（零误报）。
3. 声明 `[["./test.sh","--gates"]]`（显式 argv）⇒ **不得**被报。

## 技术约束

- 判据必须**枚举**，禁「之类」；
- 只读：不改声明、不写状态、不代提交；
- 若做 doctor 面：advisory only（WARNING/INFO），不产生 CRITICAL、不阻断任何 gate（与既有 `commit-gate` 面同族）。

## 验收标准（骨架 —— design 落地判据后细化）

- [ ] AC1：判据可机判，且有**反例**用例（合法的工具链全量入口声明**不**被报）；
- [ ] AC2：`[["./test.sh"]]`（裸脚本入口）与 `[["./test.sh","--verify"]]`（显式 argv）在同一 fixture 下判定相反；
- [ ] AC3：变异 —— 关掉判据 ⇒ AC2 红（判别力）；
- [ ] AC4：只读（跑前跑后目标仓 `git status` 与声明字节不变）；
- [ ] AC5：`./test.sh --full --regression` 全绿；`openspec validate <change> --strict` valid。

## Capabilities

- MUST: 给出可复核的存量清单（人读即可判断真假绿的证据列）。
- MUST NOT: 误报工具链全量入口；读测试脚本内容；自动改写声明。

## Impact

| 面 | 影响 |
|---|---|
| `skills/rdd-doctor/`（若选 doctor 面）或 `_lib/cli/`（若选审计 CLI） | 新增判据 / 子命令 |
| 使用方仓的存量声明 | 只读列出，不改 |
| `fix-commit-gate-generator-fake-green` | 依赖关系：**先**修生成器（否则巡检刚清完又被生成器灌新的） |
