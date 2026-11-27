---
优先级: P0
来源: 2026-11-26 CppTLM 立项会话实测（两仓均无 .rddf/commit-gate.json ⇒ 门禁实际未生效）+ ADR-commit-verification-gate D9② 的「事实性补登」先例
阶段: phase-3
分类: quality-gate
类型: improvement
状态: 已批准·待立项（planner 2026-11-27 · W6=U7a 独立 change（rdd-workflow 半边）· 8 条 AC 含 2 条变异腿）
主题: commit-gate 声明的生成入口 + 未声明时的可观测性（检测 ≠ 拦截）
---

**优先级**: P0 | **来源**: 2026-11-26 CppTLM 立项会话实测 | **阶段**: phase-3 | **分类**: quality-gate | **类型**: improvement

## metis 结论（2026-11-27 · 本轮 1 轮覆盖 9 份草稿 · 载体=头部段）

- **AC5（ADR 文本锚点）守护错对象且脆弱**（守护「文档不被改」而非「行为不变」，而行为已由 AC4 覆盖；改措辞不换语义即误红）⇒ **删**。
- **「非平凡」只给了一个例子（`["true"]`）⇒ 不可机判** ⇒ 枚举化：`true` / `echo` / `:` / `exit 0` 单命令即空壳。
- **生成入口三选一未裁决**（`rddf init` / `rdd-env-bootstrap` / `check_project_setup.sh`）⇒ design 阶段裁决并写进 AC。
- **跨仓门禁口径缺失**：治理仓侧 `.ts` 用例不在本仓 `./test.sh` 管辖内 ⇒ AC6 显式写「两仓各跑各的」。
- 已改：删 AC5（ADR 锚点）⇒ 改为 AC5（非平凡枚举）+ AC6（跨仓口径）；生成入口裁决入技术约束。


**主题**: commit-gate 声明的生成入口 + 未声明时的可观测性（检测 ≠ 拦截）

## 架构依据

`~/.config/opencode/plugins/commit-gate.ts` 的门禁三判据（暂存非空 / 写集内 / 验证命令全绿）**仅在仓库声明了**
`<workRoot>/.rddf/commit-gate.json` 时生效（`ADR-commit-verification-gate` D3:60 的**明文决策**，非 bug）。

实测（2026-11-26，CppTLM）：该仓**没有**声明 ⇒ 两次 `git commit` 实际只过了命令形态识别，
**暂存区 / 写集 / 验证命令一条都没跑** —— 而 agent 无法区分「验证通过」与「验证根本没跑」。
治理仓自己有声明（`~/.config/opencode/.rddf/commit-gate.json`），**两个使用方仓没有** ⇒
「想启用门禁也没有入口」。

**本提案只做两件低风险的事**（**不改 D3 决策**）：
① **生成入口**：让使用方仓能一键生成合法声明；
② **可观测性**：未声明时留下痕迹（检测 ≠ 拦截），照 ADR D9②「事实性补登」先例。

## 范围裁决（2026-11-27 · 拆两仓两 change）

本提案原文跨两仓（治理仓机制面 + rdd-workflow 引导）⇒ 按 objective §9.4b「跨仓治理机制」轴**拆开**：

| 半边 | 内容 | 归属 | 状态 |
|---|---|---|---|
| **本 change（U7a）** | ①**声明生成入口**（一条命令生成合法且非平凡的 `.rddf/commit-gate.json`）②**doctor 的三面检测**（空壳 / 未 tracked / 未声明） | **rdd-workflow**（builder） | **本次立项** |
| **另案（U7b）** | **未声明时的留痕**（检测 ≠ 拦截，照 ADR D9② 先例）—— 改 `plugins/commit-gate.ts` 接线 + 治理面登记 | 治理仓（architect 轨 + oracle→critic） | **原 AC4 移出**，在该 change 立项时带走 |

⚠ **metis 预算**：本稿已过 metis 1 轮（2026-11-27，9 份草稿批量，结论见头部段）。本次修订**只缩小范围**
（AC4 移出、AC6 的跨仓口径随之收敛为「本仓一侧」），**不新增任何判据** ⇒ 不另起 metis 轮。

## delta 载体（P0 生成输入）

**delta**: added commit-gate-declaration-bootstrap
**语义要求**: A project SHALL be able to generate a non-trivial commit-gate declaration | `rddf commit-gate init` SHALL write `.rddf/commit-gate.json` whose `verify_commands` are argv arrays pointing at entry points that **already exist** in the repository; when no such entry point is found it SHALL refuse and explain (never guess), the result SHALL be non-trivial (a single `true` / `echo` / `:` / `exit 0` command is not a declaration), and the command SHALL NOT `git add` or commit anything on the caller's behalf. | A project with a test entry point gets a declaration | a repository has `./test.sh` and no declaration, and `rddf commit-gate init` runs | `.rddf/commit-gate.json` is written with a `verify_commands` entry pointing at `./test.sh`, and nothing is staged or committed ;; rdd doctor SHALL report unusable commit-gate declarations | `rddf doctor --category commit-gate` SHALL report a WARNING for each of three faces: a declaration that is a **shell** (a single `true` / `echo` / `:` / `exit 0` command), a declaration that is **not git-tracked** (so a worktree has no gate), and a repository with **no declaration at all** (the gate is silently absent). Shell and untracked declarations SHALL name the file; a missing declaration SHALL name the expected path. | A shell declaration is reported | `.rddf/commit-gate.json` declares a single `true` command and `rddf doctor --category commit-gate` runs | a WARNING names the file and calls the declaration a shell

## 范围

**In Scope**:

- `rddf init` / `rdd-env-bootstrap`（或既有 `check_project_setup.sh`）：**生成入口** ——
  扫描仓库既有验证入口（测试命令 / lint / 闸脚本），生成 `.rddf/commit-gate.json`（`verify_commands` 为 argv 数组）；
- 生成物必须**非平凡**：`verify_commands` 不得是 `["true"]` 之类空壳（ADR D9① 已登记「声明被弱化」面）⇒
  配 doctor 空壳检测（与「未声明可观测」同批）；
- 生成物必须 **git-tracked**（D3 硬要求）⇒ 生成后提示 `git add`（**不自动提交**）；
- **未声明可观测**：未声明仓发生 commit ⇒ 留痕（ledger / doctor 面）+ 提示，**不拦截**
  （照 D9② 先例：检测 ≠ 拦截）；
- 使用方仓的验证命令选型**依赖** baseline 能力（存量红的仓无法声明）⇒ 与
  `add-commit-gate-baseline-known-failures` 联动；本提案先支持「只声明绿的命令」。

**Out of Scope**:

- **不改** `ADR-commit-verification-gate` D3 的「未声明 ⇒ 不设门禁」决策（那是 SU 议题，另案）；
- 不改三判据的判定逻辑（拆判据属另案 `OC-1b`）；
- 不实现 baseline 机制（另案 `add-commit-gate-baseline-known-failures`）；
- 不自动 `git add` / `git commit` 生成物；
- 不在 rdd-workflow 仓造构建缓存机制（属 RW-7 降级项，另案）。

## 关键场景

1. 一个无声明的仓跑 `rddf init`（或 bootstrap）⇒ 生成 `.rddf/commit-gate.json`，`verify_commands` 指向仓内**真实存在**的验证命令；
2. 生成后跑 `rddf doctor --category commit-gate` ⇒ 绿（声明合法 + 命令非平凡）；
3. 声明为 `[["true"]]` 之类空壳 ⇒ doctor 报 WARNING（弱化声明检测）；
4. 无声明的仓发生 commit ⇒ 留下痕迹（可查），**但 commit 不被拦截**；
5. 生成物未 `git add` ⇒ doctor 提示「声明未 tracked ⇒ worktree 内无门禁」。

## 技术约束

- 生成入口**不猜**验证命令：只从仓内**已存在**的脚本/配置推导（找不到 ⇒ 不生成，给提示）；
- **生成入口三选一需在 design 阶段裁决**（`rddf init` / `rdd-env-bootstrap` / `check_project_setup.sh`）⇒ 裁决后写进 AC；
- 生成物内容必须过 schema（`verify_commands` 为 argv 数组的数组）+ 非平凡检测；
- 「未声明可观测」的落点：ledger（`.rddf/state/`）+ doctor 面；**不新增并行状态文件**；
- 一切**只读或写生成物**，不改用户仓的既有文件。

## 验收标准

> **范围**：只判本仓（rdd-workflow）半边。**「未声明留痕」= 另案 U7b（治理仓）**，本 change 不判。

- [ ] **AC1（红→绿 · 生成入口）** 新增 `tests/integration/test_commit_gate_bootstrap.bats`：临时项目根（有 `./test.sh`、
      无声明）跑生成入口 ⇒ `.rddf/commit-gate.json` 存在，且 `verify_commands` 每条 argv 的**可执行/目标文件**在仓内**确实存在**
      ⇒ 修复前红（无该入口）⇒ 修复后绿；
- [ ] **AC2（红→绿 · 不猜）** 同文件：临时项目根**没有任何**可推导的验证入口 ⇒ **不生成**文件 + 给出「找不到入口」提示（含怎么手工写）⇒ 修复前红；
- [ ] **AC3（红→绿 · 空壳检测）** `tests/unit/test_commit_gate_doctor.py`（或复用既有 doctor 测试）：声明为单条
      `true` / `echo` / `:` / `exit 0` ⇒ doctor **WARNING**（点名文件 + 「空壳」）⇒ 修复前红；
- [ ] **AC4（红→绿 · 未 tracked 检测）** 同上：声明存在但**未 git-tracked** ⇒ doctor **WARNING**（「worktree 内无门禁」）⇒ 修复前红；
- [ ] **AC5（红→绿 · 未声明检测）** 同上：**完全没有**声明 ⇒ doctor **WARNING**（点名期望路径，说「门禁静默不存在」）⇒ 修复前红；
- [ ] **AC6（非平凡枚举，禁模糊）** 断言空壳判据是**枚举**：`verify_commands` 仅 1 条且其命令 ∈
      `{true, echo, :, exit 0}` ⇒ 判空壳（禁「之类」的表述；`--help` 里与代码里同一份枚举）；
- [ ] **AC7（变异）** 把「非平凡检测」关掉 ⇒ AC3 必须红；把「未 tracked」检查关掉 ⇒ AC4 必须红（判别力证明）；
- [ ] **AC8（门）** `./test.sh --gates` 与 `./test.sh --unit` 全绿；`openspec validate <change> --strict` ⇒ valid。

## Capabilities

- MUST: 使用方仓能通过一个命令生成**合法且非平凡**的门禁声明。
- MUST: 生成物必须 git-tracked 才被 doctor 认可。
- MUST: 未声明仓的 commit **留痕可见**，但**不被拦截**（不改 D3 决策）。
- MUST NOT: 猜测验证命令（只从仓内已存在的脚本推导）。
- MUST NOT: 自动提交生成物。

## Impact

| 面 | 影响 |
|---|---|
| `rddf init` / `rdd-env-bootstrap` / `check_project_setup.sh` | 生成入口 |
| `skills/rdd-doctor/` | 空壳检测 + 未 tracked 检测 + 未声明痕迹的巡检面 |
| `.rddf/commit-gate.json`（使用方仓） | 生成物（各仓自行生成） |
| 治理仓 `plugins/commit-gate.ts` | 未声明时的留痕（**不改**三判据决策） |
| ADR | D3 决策**不变**；D9② 事实性补登先例适用 |
