---
优先级: P1
来源: 2026-11-28 本仓启用门禁实测（commit 554c821a）+ metis 审稿（同轮，P0 6 条 / P1 4 条全部采纳）
阶段: phase-3
分类: quality-gate
类型: fix
状态: 待审查
主题: 生成器把「入口存在」当成「验证会执行」—— 恒绿（假绿）声明必须不可生成
---

**优先级**: P1 | **来源**: 2026-11-28 本仓启用门禁实测 + metis 审稿 | **阶段**: phase-3 | **分类**: quality-gate | **类型**: fix

## metis 结论（2026-11-28 · 本轮 1 轮覆盖本稿 + 其尾项的登记稿 · 载体=头部段）

- **真正的需求是「生成物必须有机会变红」（可证伪），不是「补强空壳枚举」**。任何"读脚本源码猜它会不会跑测试"的静态启发式都是第三份「只看形状不看行为」的判据，永远补不完。
  ⇒ **改为减法（能力边界）**：脚本类入口（`test.sh` / `package.json::scripts.test` / `Makefile::test:`）**默认不可自动推导**（除非仓内显式来源）；工具链类（pytest / go / cargo）保留推导但加**前置测试件存在**的静态判定。
- **「空转」缺定义** ⇒ 原稿把范围收窄到一个 help 分支；同型还有空脚本、`echo ok`、`--if-present`、`go test` 零测试件（rc=0）、`cargo test` 零测试、`make test` 空配方、pytest 零收集（rc=5，恒红）。
  ⇒ 候选表**逐条裁决**写进范围（见下表），不留自由裁量。
- **AC1 的「要么拒绝、要么 argv≥2」是析取空洞**：猜一个模式参数的实现也能过 ⇒ 违反「不猜」。⇒ **去析取，只留拒绝单臂**；另设 AC 覆盖「显式来源沿用」。
- **「显式来源」原是无载体的抽象名** ⇒ 钉死载体 = **既有 `.rddf/commit-gate.json` 里的合法 argv**（`--force` 时逐条沿用 + 提示「未重新推导」）；**禁**解析被测脚本内容、**禁**新造第二配置面（撞 ADR D3 与 U7a「不新增并行状态文件」）。
- **旧判据本身固化了 bug**（`tests/unit/test_commit_gate_declaration.py` 的两例、`test_commit_gate_bootstrap.bats` 三例、`openspec/specs/commit-gate-declaration-bootstrap/spec.md` 的 Scenario）⇒ 显式授权并**要求**改写，不留「非回归」假豁免。
- **Out of Scope 原有一条尾巴**（存量恒绿声明）⇒ 升级为**已登记**的另一稿 `fix-commit-gate-existing-vacuous-declarations`（per `add-deferral-registration-guard`：deferral 必须带注册目标）。
- 已改：delta 语义（加 MODIFIED + 拒绝契约 + 退出码）／AC1 去析取／AC3–AC9 新增／候选表逐条裁决／文案同步进 Impact。

**主题**: 生成器把「入口存在」当成「验证会执行」—— 恒绿（假绿）声明必须不可生成

## 架构依据

U7a（`add-commit-gate-declaration-bootstrap`，已归档）给使用方仓加了声明生成入口
`rddf commit-gate init`，其判据是**「仓内存在可推导的验证入口」**
（`_lib/commit_gate_declaration.py::CANDIDATES`，顺序即优先级，只取第一个命中者）。

实测（2026-11-28，本仓 `/workspace/main/rdd-workflow`）：

| 步骤 | 实测 |
|---|---|
| `rddf commit-gate init --dry-run` | `verify_commands = [["./test.sh"]]` |
| 裸 `./test.sh` | `rc=0`，输出 **40 行 help**，**执行 0 个用例**（`test.sh:485-488`：`if [ -z "$MODE" ]; then print_help; exit 0`） |
| 结论 | 生成的声明**恒绿**：门禁每次「通过」，但三判据里的验证一栏从未验证任何东西 |

危害**高于「未声明」**：未声明有留痕与提示（ADR D3 + U7b 的 `commit-gate-notices.jsonl`），
而恒绿声明**没有任何痕迹** —— agent 会据此宣称「验证已通过」。这正是
`ADR-commit-verification-gate` D9① 登记过的「声明被弱化」面，只是弱化不来自作者，而来自**生成器自己**。

**为什么现有守卫没拦住**（两处判据都只看形状，不看行为）：

- 生成器的候选判据是**文件存在性**（+ `package.json::scripts.test` 非空 / `Makefile` 有 `test:` 目标），
  没有一步判定「裸调用是否真的执行验证」；
- `is_shell_declaration` 只枚举「恰好 1 条命令且 ∈ `{true, echo, :, exit 0}`」
  ⇒ `[["./test.sh"]]` 不在枚举内 ⇒ `rddf doctor --category commit-gate` 判「非空壳」。

**判据本身被固化的证据**（不是"新发现"，是"旧断言要求的就是错的"）：

- `tests/unit/test_commit_gate_declaration.py::test_test_sh_wins`：fixture 是空脚本 `#!/bin/sh\n`，断言生成 `[["./test.sh"]]`；
- 同文件 `test_makefile_needs_test_target`：fixture 是 `test:\n\techo test`，断言生成 `make test`；
- `tests/integration/test_commit_gate_bootstrap.bats` 三例（`test.sh 存在 ⇒ 生成` / `--dry-run` / `--force 覆盖`）同型；
- `openspec/specs/commit-gate-declaration-bootstrap/spec.md` 的
  `Scenario: A project with a test entry point gets a declaration` 明文 `THEN ... entry pointing at ./test.sh`。

**本仓现状**：`.rddf/commit-gate.json` 已手工改为 `./test.sh --gates` + `./test.sh --quick`
（两条实测全绿，commit `554c821a`）—— 那是**绕过**生成器，不是修好生成器。

## delta 载体（P0 生成输入）

**delta**: modified commit-gate-declaration-bootstrap
**语义要求**: A generated commit-gate declaration MUST NOT be vacuously green | `rddf commit-gate init` SHALL NOT auto-derive a `verify_commands` entry from a **script-type** entry point (`./test.sh`, `package.json::scripts.test`, `Makefile::test:`) because whether such an entry verifies anything when invoked without arguments is not statically decidable; such an entry SHALL be taken only from an explicit source, namely a valid existing `.rddf/commit-gate.json` whose `verify_commands` are not shell declarations, and without one the command SHALL refuse. **Toolchain-type** entries (pytest / go / cargo) SHALL remain derivable but only when the repository contains test files per each tool's convention. Refusal SHALL exit non-zero with a dedicated code distinct from "no derivable entry point", SHALL NOT write or modify the declaration, SHALL NOT stage or commit anything, and SHALL print a copy-pasteable explicit-argv template. | A script entry point is no longer auto-derived | a repository has a `test.sh` whose argument-less run prints help and exits 0, carries no declaration, and `rddf commit-gate init` runs | the command exits with the dedicated refusal code, `.rddf/commit-gate.json` is not written, and the output contains the explicit-argv template ;; An existing valid declaration is kept | the repository already declares `[["./test.sh","--verify"]]` and `rddf commit-gate init --force` runs | the declaration keeps that argv verbatim and the output states that it was not re-derived

## 范围

### 候选表逐条裁决（**禁止 design 阶段自由裁量**）

| 候选 | 裁决 | 理由（可机判） |
|---|---|---|
| `test.sh` → `./test.sh` | **不再自动推导**（脚本类） | 裸调用是否执行验证不可静态判定：本仓 rc=0 / 40 行 help / 0 用例 |
| `package.json::scripts.test` → `npm test` | **不再自动推导**（脚本类） | `"test": "echo ok"` / `exit 0` / `npm run test --workspaces --if-present`（全 workspace 无 test 时 rc=0） |
| `Makefile::test:` → `make test` | **不再自动推导**（脚本类） | 空配方（`Nothing to be done`，rc=0）/ `@echo no tests` |
| `pyproject.toml` / `pytest.ini` / `setup.cfg` → `python3 -m pytest` | **保留推导** + 前置「仓内存在测试件」（`test_*.py` / `*_test.py`） | 零收集 rc=5（恒红，与恒绿反向但同样无意义）⇒ 前置拦掉 |
| `go.mod` → `go test ./...` | **保留推导** + 前置「仓内存在 `*_test.go`」 | 零测试件时 `no test files` 且 **rc=0** ⇒ 恒绿 |
| `Cargo.toml` → `cargo test` | **保留推导** + 前置「仓内存在测试件（`tests/**` 或含 `#[test]` 的 `*.rs`）」 | 零测试时 `0 passed` 且 **rc=0** ⇒ 恒绿 |

> ⚠ **本机未安装 go / cargo**（`which go cargo` 均无）：上表 go/cargo 的零测试 rc 按工具**书面行为**，
> 实施时须在能跑这两个工具链的环境**实跑确认**（写进 change 的 design，不得只凭本表）。

### 拒绝契约（钉死，design 可改但必须写明理由）

- 退出码 **3**（与「找不到可推导入口」的 **1** 区分 ⇒ `rdd-env-bootstrap` / CI 可分辨两种失败）；
- stderr 含固定关键字 **`需要显式 argv`** + **可复制模板**（与 `manual_template()` 同源，禁第二份实现）；
- **不写 / 不改** `.rddf/commit-gate.json`；不代 `git add` / `git commit`；
- `--dry-run` 与真实路径**同判**（拒绝也在 dry-run 下报 rc=3，不写盘）。

### 显式来源的载体（钉死）

**唯一载体 = 既有 `.rddf/commit-gate.json` 里的合法 `verify_commands`**（`--force` 时逐条沿用 + stdout 提示「未重新推导」）。
- **禁止**解析被测脚本内容（那是「读源码猜行为」，metis 已论证不可判定）；
- **禁止**新造项目级 verify 配置键 / 第二配置面（撞 `ADR-commit-verification-gate` D3 的「声明文件是唯一入口」与 U7a 的「不新增并行状态文件」）；
- 既有声明本身是 shell（`true/echo/:/exit 0`）⇒ **不算显式来源**，走拒绝分支。

**In Scope**：

- `_lib/commit_gate_declaration.py`：候选表裁决落地（脚本类移除自动推导；工具链类加测试件前置）+ 显式来源读取（判据单一真源不变）；
- `_lib/cli/commit_gate_cmd.py`：拒绝分支（rc=3 / stderr 关键字 / 模板）与「沿用既有 argv」分支；
- 写入改用 `_lib/core/atomic_write.py`（现状 `commit_gate_cmd.py:96` 是 `write_text`，半截 JSON ⇒ D6 fail-closed ⇒ 静默无门禁）；
- 旧判据改写：`tests/unit/test_commit_gate_declaration.py`（两例）、`tests/integration/test_commit_gate_bootstrap.bats`（三例）；
- spec 侧 `## MODIFIED Requirements`（替代 `commit-gate-declaration-bootstrap` 里那条 Scenario）；
- 文案同步：`rddf commit-gate --help`、`_lib/cli/__init__.py` 的一行摘要。

**Out of Scope**：

- **不改** `ADR-commit-verification-gate` D3（未声明 ⇒ 不设门禁）与三判据（暂存 / 写集 / 验证）语义；
- **不改** `is_shell_declaration` 的空壳枚举（`{true, echo, :, exit 0}`）—— 它是**不同判据**；
- **存量恒绿声明的巡检** ⇒ 已登记另稿 `fix-commit-gate-existing-vacuous-declarations`（per `add-deferral-registration-guard`）；
- 不引入「生成期执行任意仓内命令」的探针（本稿走**零执行**路线）；
- 不动 `render_declaration()` 的字节确定性形态（无时间戳）。

## 关键场景

1. **脚本类 + 无显式来源**：`test.sh` 无参即 help + `exit 0`、无声明 ⇒ `init` 退出 **3**、不写文件、输出含 `需要显式 argv` 模板。
2. **脚本类 + 有显式来源**：仓内已有 `[["./test.sh","--verify"]]` ⇒ `init --force` **逐字沿用** + 提示「未重新推导」。
3. **工具链类 + 有测试件**：`pyproject.toml` + `tests/test_x.py` ⇒ 生成 `python3 -m pytest`（与今日一致）。
4. **工具链类 + 零测试件**：`go.mod` 无 `*_test.go` ⇒ 拒绝（rc=3），不生成 `go test ./...`。
5. **既有声明是 shell**：`[["echo"]]` ⇒ 不算显式来源 ⇒ `--force` 走拒绝分支，文件**字节不变**。
6. **无任何候选**：`README.md` ⇒ 与今日一致（rc=1 + 手工模板）。

## 技术约束

- **不猜**：模式参数只能来自显式来源；生成期**不执行**任何仓内命令；
- 判据**单一真源**仍在 `_lib/commit_gate_declaration.py`（生成器 / `--help` 文案共用，禁第二份实现）；
- 测试件判定必须**枚举**（路径形态 / 文件后缀），禁「之类」表述；
- 静态读取仓内文件必须 catch `OSError` / `UnicodeDecodeError`（`_package_has_test_script` 有先例），不可读 ⇒ 视为「无测试件」而非抛栈；
- 拒绝路径**不得**破坏既有声明（先判后写，字节不变）；
- 写入用 `_lib/core/atomic_write`（不扩成议题）。

## 验收标准

- [ ] **AC1（红→绿 · 脚本类不再自动推导）** 新增 `tests/integration/test_commit_gate_bootstrap_noop.bats`：fixture 仓的
      `test.sh` 无参打印 help 并 `exit 0`（复刻 `test.sh:485-488` 形态）、无声明 ⇒
      `init` **rc=3**、`.rddf/commit-gate.json` **不存在**、stderr 含 `需要显式 argv` 与可复制模板。
      修复前 rc=0 且写出 `[["./test.sh"]]` ⇒ 红；
- [ ] **AC2（红→绿 · 显式来源沿用）** 同文件：预置 `{"verify_commands":[["./test.sh","--verify"]]}`
      （`test.sh` 的 `--verify` 分支写一行标记并 rc=0）⇒ `init --force` 后声明**逐字不变**、
      stdout 含「未重新推导」；并**实跑**该 argv，断言标记出现（证明不是 help 分支）。
      修复前 `--force` 会用 `[["./test.sh"]]` 覆盖 ⇒ 红；
- [ ] **AC3（红→绿 · 工具链类零测试件不推导）** 参数化：`go.mod` 无 `*_test.go` / `Cargo.toml` 无测试件 /
      `pyproject.toml` 无 `test_*.py` ⇒ 全部 rc=3 + 不写文件；补上测试件后 ⇒ 正常生成（且 argv 与今日一致）。
      修复前均生成 ⇒ 红；
- [ ] **AC4（拒绝不破坏既有声明）** 预置 `{"verify_commands":[["echo"]]}`（shell，不算显式来源）⇒ `--force` 走拒绝分支，
      断言文件**字节相等**（`cmp`）；
- [ ] **AC5（spec 侧 MODIFIED）** change 的 delta 含 `## MODIFIED Requirements`，替代
      `openspec/specs/commit-gate-declaration-bootstrap/spec.md` 的
      `Scenario: A project with a test entry point gets a declaration`（THEN 改为「拒绝 + 模板」）；
      归档后该 spec **不得**同时断言「写 `./test.sh`」与「拒绝写 `./test.sh`」；
- [ ] **AC6（旧判据必须改，不是"非回归"）** `tests/unit/test_commit_gate_declaration.py::test_test_sh_wins` /
      `test_makefile_needs_test_target`、`tests/integration/test_commit_gate_bootstrap.bats` 三例
      —— 改为断言拒绝 / 沿用；并在 design 写明**旧断言为什么本身错**（固化了恒绿行为）；
- [ ] **AC7（文案同步）** `skills/rdd-doctor/scripts/checks/commit_gate_check.py` 的 `fix_hint` 与
      `skills/rdd-doctor/SKILL.md` 的 commit-gate 行不再把 `rddf commit-gate init` 当唯一出路
      （改为「init 生成 / 手写声明」两条，脚本类仓不再被送进死路）；`rddf commit-gate --help` 与新判据同源；
- [ ] **AC8（变异）** ① 关掉「脚本类不推导」⇒ AC1 红；② 关掉「工具链测试件前置」⇒ AC3 红；
      ③ 让生成器**猜**一个模式参数（如自动补 `--gates`）⇒ AC1 必须红（堵住析取缝）；
- [ ] **AC9（门）** `./test.sh --full --regression` 全绿（覆盖新增 bats；AGENTS.md 的 archive 回归门）；
      `openspec validate <change> --strict` ⇒ valid。

## Capabilities

- MUST: 脚本类入口（`test.sh` / `package.json::scripts.test` / `Makefile::test:`）不得被自动推导；只能来自显式来源。
- MUST: 工具链类入口（pytest / go / cargo）推导前必须判定仓内存在测试件（枚举，禁「之类」）。
- MUST: 拒绝 = 独立退出码（3）+ 固定关键字 `需要显式 argv` + 可复制模板 + 不写文件 + 不代 add/commit。
- MUST: 显式来源只认既有合法声明；shell 声明不算。
- MUST NOT: 在生成期执行仓内命令；解析被测脚本内容；新造第二配置面。
- MUST NOT: 改 D3 决策、三判据语义、`is_shell_declaration` 的枚举。

## Impact

| 面 | 影响 |
|---|---|
| `_lib/commit_gate_declaration.py` | 候选表裁决 + 测试件前置 + 显式来源读取（判据单一真源不变） |
| `_lib/cli/commit_gate_cmd.py` | 拒绝分支（rc=3）/ 沿用分支 / `atomic_write` |
| `tests/unit/test_commit_gate_declaration.py`（2 例）<br>`tests/integration/test_commit_gate_bootstrap.bats`（3 例） | **旧判据改写**（授权见 AC6） |
| `openspec/specs/commit-gate-declaration-bootstrap/spec.md` | 经 change 的 `## MODIFIED Requirements` 替代（AC5） |
| `skills/rdd-doctor/`（`commit_gate_check.py` + `SKILL.md`） | fix_hint 不再把脚本类仓送进死路（AC7） |
| `CHANGELOG.md` | 既有「本仓启用门禁」条目里「生成器假绿」那段改为指向本 change |
| `_lib/cli/__init__.py` | `commit-gate` 一行摘要同步 |
| 已生成声明的仓（本仓 / CppTLM 等） | 存量恒绿声明**不自动修正** ⇒ 另稿 `fix-commit-gate-existing-vacuous-declarations` |
| ADR | D3 决策不变；D9① 「声明被弱化」面由生成器侧收口 |
