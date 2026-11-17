---
优先级: P1
priority: P1
来源: 2026-11-17 第八批 5 项归档过程发现（follow-up H/I/J 的前置）+ `fix-execution-mode-decision`
  实施前的 oracle 咨询 —— **lightweight 执行模式今天产出的是「幽灵分支」**（不建任何分支，却在
  builder handoff 里写下 `branch="openspec/<name>"`），而归档门与验证器都按「实现分支 tip」取锚点
  ⇒ lightweight 的 change **过不了归档门**，只能用审计旁路
阶段: phase-2
分类: bugfix
类型: bugfix
状态: draft

生成时间: 2026-11-17
roadmap_ref:
---

# fix-lightweight-branch-and-archive

**主题**: 阶段步骤化执行

> ⚠ **本项是 `fix-execution-mode-decision` 的前置**：D 项的「输入诚实化」一旦让小改动判成
> `lightweight`，而 lightweight 仍不可归档 ⇒ 本仓所有小 change 会立刻变成不可归档。
> ⇒ 顺序必须是「本项先落地，D 项的执行模式部分再放开」。

## 架构依据

### 缺陷一：lightweight 产出「幽灵分支」—— 声明了分支，却没有分支

| 环节 | 事实 | 位置 |
|---|---|---|
| 建分支 | lightweight 分支**不建任何分支**（全仓唯一建分支点是 worktree 模式的 `git worktree add -b`） | `skills/rdd-builder/scripts/phase2_execute.sh` |
| 声明分支 | 却在 builder handoff 里写下 `branch="openspec/<name>"` ⇒ **一个没有对应 ref 的声明** | 同上（handoff 写入段） |
| 取锚点 | 取不到分支 ⇒ 返回 `None`（fail closed） | `_lib/verifier/branch.py` |
| 判失败 | ⇒ `halt_reason="openspec/<change> branch missing or detached"`，verification state = failed | `_lib/cli/rdd_verify_cmd.py` |
| 归档被拒 | ⇒ 「openspec/<change> branch missing」 | `_lib/verifier/archive_gate.py` / `_lib/archive.sh` |
| 唯一出路 | `SKIP_RDD_VERIFIER=yes` + `RDDF_VERIFIER_BYPASS_REASON` ⇒ 每次 change 一条 bypass 审计 | `_lib/archive.sh` |

⇒ **lightweight 不是一个「慢一点但能用」的模式，而是一个走不完 P3 的模式**。

### 缺陷二：契约早已说「有分支」，实现做成了「无分支」（四处既有文本）

| 出处 | 原文 |
|---|---|
| ADR-0024（Consequences） | 「小改动（≤2 文件，≤3 任务）直接在 **main repo 分支**工作，跳过 worktree 创建」 |
| ADR-0036（Decision 表，2026-11-17 修订后仍成立） | 「false → 强制轻量模式（**branch-only**）」 |
| `_lib/schemas/config_schema.json` | 「force lightweight mode (**branch only**, no worktree)」 |
| `verifier-lifecycle`（已采纳 spec） | scenario「GIVEN lightweight execution mode is active AND the current branch is **not** `openspec/<change>` THEN fail closed」 |

⇒ 契约 = **有 `openspec/<change>` 分支、无 worktree**（ADR-0036 的 2026-11-17 修订已把它钉死）。

### 缺陷三：lightweight 的归档路径缺四步（worktree 路径有的，它没有）

`skills/rdd-builder/scripts/phase3_archive.sh` 的 lightweight inline 分支（文件自认 KNOWN GAP）：

- ❌ 不做 `post_archive_cleanup`；
- ❌ 不调 `mark_iteration_archived` ⇒ `iteration.json` 永远停在非归档态；
- ❌ 不做**分支合入的判定** ⇒ 与 ADR-0061 的合入门不在同一处；
- ❌ 不做分支清理（lightweight 下的等价物）。

### 依赖与顺序（architect 已裁定，见 ADR-0036 修订节的「依赖顺序与过渡态」）

```
① 本项（lightweight 建分支 + 归档路径补齐）
② fix-execution-mode-decision 的执行模式部分（小改动 ⇒ lightweight 才可放开）
③ fix-worktree-archive-branch-merge（ADR-0061 的合入门，worktree 路径）
```

⇒ ① 与 ③ 都改 `_lib/archive.sh` ⇒ **建议同批串行落地**（或明确 rebase 顺序：先 ③ 后 ①）。
⇒ ① 落地前，D 项对「小改动」的诚实输出是 **fail-closed 到 worktree** + reason 写明原因。

## 范围

- **In Scope**：
  1. `phase2_execute.sh` 的 lightweight 分支**建 `openspec/<change>` 分支**（主仓，不建 worktree）并在该分支上执行；起点显式取默认分支 tip；分支已存在时的政策见 What Changes §1；
  2. builder handoff 的 `execution_mode_decision` 必须与**真实模式**一致（mode + reason 同步写），fail-closed 时不得留下「mode=lightweight / 实际 worktree」的矛盾；
  3. `phase3_archive.sh` 的 lightweight inline 归档路径补齐：**分支提交归属检查** → **合入门判定** → `openspec archive` → **分支清理** → `mark_iteration_archived`（带真实 commit sha）→ `post_archive_cleanup`；
  4. **2×2 矩阵**：`{lightweight, worktree} × {openspec_tracked: true, false}` 四格的行为都要被钉住（尤其 lightweight×true 必须调 `commit_archive_moves`，lightweight×false 必须不调）；
  5. `wt_path_for_branch == main_root` 的守卫（主仓不得被当 worktree 处理 ⇒ 不得对它执行 `git worktree remove`）；
  6. **对已采纳 spec 写 delta**（不是改已归档 change 的 AC —— 那在流程上不成立）：`archive-openspec-tracked-skip-commit`（false 分支的步骤顺序）与 `archive-auto-commit`（lightweight MUST 调 helper 的归属）；
  7. 测试：新增 `tests/integration/test_lightweight_branch_and_archive.bats`（含 e2e：P2 → 写 verdict cache → `rddf rdd-verify` → P3 → 断言 archived）。
- **Out Scope**：
  - 不改 `decide_execution_mode` 的阈值与签名（归 `fix-execution-mode-decision`）；
  - 不改**执行模式判定本身**（是否走 lightweight 归 D 项）；
  - 不改 worktree 路径的归档行为（归 `fix-worktree-archive-branch-merge` / ADR-0061）；
  - 不**委托** `archive_change`（它的 wt_path 前置检查要求 worktree 存在；`fix-worktree-archive-path` 已记录该方案未采纳）⇒ 只新增调用点，不改它的结构；
  - **不实现** `verifier-lifecycle` 的「current branch mismatch ⇒ fail closed」校验（那条 scenario 今天未实现，且在「归档前已切回默认分支」的时序下会反向失败）⇒ 列为独立缺口（见「顺带发现」）；
  - 不实现 `openspec_tracked=false ⇒ 强制 lightweight`（ADR-0036 修订已裁定该子句**退役**）；
  - 不删任何**已存在**的分支（失败残留分支允许被后续复用，但复用前必须校验 tip）。

## Why

**「lightweight」被四处承认为一等执行模式，却是一个走不完归档的模式。**

- 用户真正买到的是「小改动不必付 worktree 的开销」（ADR-0024 的核心目标）；
- 但今天付的代价不是开销，是**不可归档**（只能走审计旁路）⇒ 对 AC 验证这道门而言，「归档说成功、代码没进主干」这类静默失败比「慢一点」严重得多；
- 而 D 项（输入诚实化）**一旦**把小改动判成 lightweight，就会把这个不可用模式推广给**全部小 change** ⇒ 本项是 D 项的**安全前提**，不是可选优化。

> ⚠ **metis 指出的更重的一条**：若只把「建分支 + 补归档路径」做掉而不管**提交归属**，本项会把「不可归档」换成「**假归档**」—— 因为 `execute` 阶段默认不 commit（`skills/execute/SKILL.md`），轻量分支会是一个**空壳 ref** ⇒ 验证锚点指向不含本次改动的提交（可能假通过）⇒ 合入门判「内容等价」放行 ⇒ 归档把**未提交的实现文件**留在主干工作区 ⇒ 归档报成功、代码从未 commit ⇒ **ADR-0061 要消灭的静默失败在轻量路径上原地复活**。⇒ 本项必须先定「提交归属」政策（见 What Changes §2）。

## What Changes

1. **建分支**（`phase2_execute.sh` 的 lightweight 分支）：
   - **时点**：P2 起始、任何执行动作之前（锚点应在执行前确定）；
   - **起点**：显式取默认分支 tip（`git checkout -b openspec/<change> <default_branch>`）⇒ 不用裸 `checkout -b`（否则基点可能是上一个 change 的分支或 detached HEAD ⇒ 锚点/`merge-base`/`cherry` 全部失真）；
   - **分支已存在的三档政策**（写死，不含糊）：
     - `ref 存在` 且 `tip == 默认分支 tip` ⇒ **允许复用**（上一轮建了但没提交的空壳）；
     - `ref 存在` 且 `tip != 默认分支 tip` ⇒ **fail-closed**：退回 worktree 模式 + reason 写明「同名分支已存在且指向其它提交」；
     - `ref 不存在` ⇒ 正常创建；
   - `checkout` 失败（分支被别的 worktree 占用等）⇒ 退回 worktree；**worktree 也建不起来** ⇒ 退出码 3 + 明确文案，**不得静默继续**。
2. **提交归属政策**（本项的核心，缺了它就只是把缺陷换了个形状）：
   - lightweight 的 P2 结束时，实现必须**已提交到 `openspec/<change>` 分支**；
   - 判据（与 worktree 路径的 `check_worktree_commits` 同语义、但**基于分支**而非 worktree）：`git rev-list --count <default>..openspec/<change> > 0`；
   - 为 0 ⇒ **拒绝归档** + 给出「在主仓上 commit 到该分支」的命令（**不引入 auto-commit** —— 自动 `git add -A` 会把 agent 的其它改动一起提交）；
   - 验收断言：归档前断言「分支 tip 的父提交 = 默认分支 tip」（防止基点错位）。
3. **归档路径补齐**（`phase3_archive.sh` 的 lightweight inline 分支）：
   - 顺序：`switch_to_default_branch`（**在拒绝之前不改用户的 HEAD** ⇒ 拒绝路径不得留下副作用）→ **提交归属检查** → **合入门判定** → `openspec archive` → **分支清理** → `mark_iteration_archived`（带真实 sha）→ `post_archive_cleanup`；
   - **合入门判定**：**语义同源、判据按模式分叉** —— 复用 ADR-0061 的 `archive_premerge_check`，但**lightweight 下 `wt_path` 为空**，其 ①「worktree 内未提交改动」判据**不适用**（lightweight 没有 worktree；用主仓的 `git status --porcelain` 会把**别的 change 的脏文件**误判成本 change 的未提交改动 ⇒ 假拒绝，且其指引文案会诱导用户把别人的改动 commit 进来）⇒ lightweight 的对应判据是 §2 的**分支提交归属检查**；主仓的脏文件**只警告不拒绝**。⓪（ref 缺失）/②（已合入）/③（内容等价 patch-id）/④（无法判定）四项原样复用。
   - **分支清理**：`wt_path` 传空（**不得对主仓执行 `git worktree remove`**）；未合入时 `git branch -d` 会失败 ⇒ 与 ADR-0061 一致：**只警告、归档仍成功**（返回码语义对齐）；`FORCE_BRANCH_DELETE` 的语义不变。
   - **`commit_archive_moves`**：lightweight × `openspec_tracked: true` ⇒ **必须调用**（`archive-auto-commit` 的 MUST，见 §范围 6）；lightweight × `false` ⇒ **必须不调用**。
   - **步骤清单（枚举）**：本项补的是「提交归属检查 / 合入门判定 / 分支清理 / `mark_iteration_archived`（带 sha）/ `post_archive_cleanup` / `commit_archive_moves`（条件）」。
   - **步骤清单（显式不补，理由见 ADR-0061 的 Consequences）**：issue 关闭（`close_issues_for_change_hook`）、tasks 完成度门（`check_tasks_completion`）、L2 采集（`collect_l2_count_wrapper`）、tasks sidecar。
4. **2×2 矩阵**：四格都要有断言 —— `{lightweight, worktree} × {openspec_tracked: true, false}`；特别地 **lightweight×true 必须调 `commit_archive_moves`、lightweight×false 必须不调**（用 stub 记录调用）。
5. **守卫**：`wt_path_for_branch` 会把主仓也列出来（`git worktree list --porcelain` 含主 worktree）⇒ `wt_path == main_root` 时**不得**按 worktree 处理（不执行 `git worktree remove`）；`discover_ship_changes` / `select_worktree` 会把主仓登记成 worktree ⇒ 在本立项的「顺带发现」里登记为 known behavior（不在本项修）。
6. **abort / 清理语义**：P2 失败或 P3 前用户放弃 ⇒ 主仓 HEAD 回到默认分支（不留 `openspec/<change>`）；失败残留的分支**允许被后续复用**，但复用前必须校验 tip ∈ {默认分支 tip}（§1 的三档政策）⇒ 残留分支不会成为下一次「分支已存在」的陷阱。
7. **spec delta**（对**已采纳** spec 写 delta；已归档 change 的 AC 不可 MODIFIED —— 那是历史记录）：
   - `archive-openspec-tracked-skip-commit`：false 分支的步骤顺序增加「提交归属检查 + 合入门判定」两步；
   - `archive-auto-commit`：lightweight MUST 调 helper 的归属写清（由 ADR-0061 主责的 delta 落地）；
   - 在本立项的「审稿记录」里**登记推翻** `fix-worktree-archive-path` 的 acceptance-8（「lightweight 模式行为不变」⇒ 本项有意变更）。

## Acceptance

- [ ] lightweight 模式下 `openspec/<change>` 分支被创建，**起点为默认分支 tip**（断言：分支 tip 的父提交 == 默认分支 tip），且 P2 在该分支上执行（断言 `git branch --show-current`）
- [ ] 分支已存在的三档政策可判定：tip == 默认分支 tip ⇒ 复用；tip != 默认分支 tip ⇒ **fail-closed 退回 worktree**（断言 handoff 的 `execution_mode_decision.mode == "worktree"` 且 `reason` 非空）；`checkout` 失败且 worktree 也建不起来 ⇒ 退出码 3 + 明确文案
- [ ] **提交归属检查生效**：分支零提交 ⇒ 归档被拒 + stderr 含「在主仓上 commit 到 `openspec/<change>`」的命令；分支有提交 ⇒ 通过（断言 `git rev-list --count <default>..openspec/<change> > 0`）
- [ ] handoff 的 `execution_mode_decision.mode` 与 `reason` 与**真实模式**一致（fail-closed 时 mode 被改写为 `worktree` 且 reason 写明原因）—— 断言读 handoff 的 `mode`/`reason`/`worktree_path` 三者自洽
- [ ] lightweight 归档路径在 `openspec archive` **之前**跑合入门；未合入 ⇒ 拒绝 + stderr 含可复制的合并命令；**拒绝路径不得改变主仓 HEAD**（断言 `git branch --show-current` 仍为默认分支）
- [ ] **dirty 语义分叉生效**：主仓存在**与本 change 无关**的未提交文件 ⇒ 归档**不得**因此被拒（只警告）；本 change 的实现未提交 ⇒ 由「提交归属检查」拒绝（不是由主仓 dirty 拒绝）
- [ ] **2×2 矩阵**：lightweight×`openspec_tracked: true` ⇒ `commit_archive_moves` **被调用**；lightweight×`false` ⇒ **不被调用**；worktree 两格行为不变（stub 记录调用）
- [ ] lightweight 归档后：实现分支**已合入**默认分支、**已删除**、`iteration.json` 进入 `archived` 态且 `archive_commit_sha` == 默认分支 tip（**非空**）
- [ ] lightweight 归档路径调用 `post_archive_cleanup`；分支清理失败（未合入 / `git branch -d` 失败）⇒ **只警告、归档仍成功**（返回码语义与 worktree 路径一致）
- [ ] `wt_path_for_branch == main_root` 时**不执行** `git worktree remove`（断言：无 worktree remove 调用 / 主仓目录完好）
- [ ] abort 语义：P2 失败或放弃后主仓 HEAD 回到默认分支；残留分支可被后续复用但复用前校验 tip
- [ ] **e2e**：注入 `mode=lightweight` 的 handoff fixture → P2 → 写 verdict cache（`codebase_commit` = 分支 tip）→ `rddf rdd-verify`（断言 `state=passed` / `archive_ready=true`）→ P3 → 断言 `archived`。⚠ 测试**必须注入 handoff fixture**（本仓 `phase1_5_deps.sh` 的 `task_count = 5` 硬编码与 `LEGACY_EXEC_MODE` 覆盖两条路都**当下**不产出 lightweight ⇒ 不能依赖「跑 P1.5 自然产出 lightweight」）
- [ ] 两份已采纳 spec 的 delta 已写（`archive-openspec-tracked-skip-commit` 的步骤顺序；`archive-auto-commit` 的 helper 归属）；并在审稿记录里登记推翻 `fix-worktree-archive-path` 的 acceptance-8
- [ ] **既有测试的预期破坏面已处理**：`test_phase3_archive_delegation.bats`（`openspec archive` 恰好 1 处的源码守卫）、`test_rdd_builder_phase3_archive.bats`（12 个 fixture 会经过新步骤）、`test_phase2_commit_gate.bats`（lightweight fixture）—— 逐条改或明确记录为预期变更
- [ ] **反向守卫（归 D 项，本项只登记不证伪）**：本项落地前，D 项对「小改动」的判定必须仍为 `worktree`（ADR-0036 的 V-G）⇒ 本项**不**声称能证明这一点，只登记依赖
- [ ] `./test.sh --unit` + `./test.sh --full --regression` 全绿 + `bats tests/integration/test_rdd_builder_phase3_archive.bats` + `bats tests/integration/test_lightweight_branch_and_archive.bats` 全绿

## Capabilities

- lightweight 从「走不完 P3 的模式」变成**一等可用模式**：小改动可以真的省掉 worktree 的开销（ADR-0024 的核心目标兑现）
- 「幽灵分支」消失：handoff 声明的分支与真实 ref 一致 ⇒ 下游不再被假声明误导
- **不会把「不可归档」换成「假归档」**：提交归属检查把「代码从未 commit」变成一道**显式拒绝**（与 worktree 路径的 `check_worktree_commits` 同语义）
- 轻量路径与 worktree 路径**共用同一套合入判定语义**（⓪/②/③/④），而 dirty 判据按模式分叉（轻量路径用分支提交归属，不用主仓 dirty）
- `iteration.json` 在轻量路径上也进入归档态（状态不再停在半路）
- D 项的输入诚实化可以安全放开「小改动 ⇒ lightweight」（否则会把不可用模式推广给全部小 change）

## Impact

- **影响面**：`skills/rdd-builder/scripts/phase2_execute.sh`（建分支 + handoff 的 mode/reason 同步）、`skills/rdd-builder/scripts/phase3_archive.sh`（lightweight inline 分支补齐）、`_lib/archive.sh`（lightweight 路径的合入/清理调用点 + `wt_path == main_root` 守卫）、`openspec/specs/archive-openspec-tracked-skip-commit/spec.md` + `openspec/specs/archive-auto-commit/spec.md`（delta）、`tests/integration/test_lightweight_branch_and_archive.bats`（新增）。
- **风险**：
  - **行为变更**：lightweight 路径从此在分支上执行 ⇒ 「直接落在默认分支上的旧习惯」会变成「提交在 `openspec/<change>` 上、归档时合入」⇒ 需要迁移说明。
  - **提交归属是新的拒绝面**：轻量路径上「忘了 commit」会挡住归档（与 worktree 路径一致，但轻量路径的用户可能不习惯）⇒ 拒绝文案必须给出可复制的命令。
  - **与 worktree 路径共用 `_lib/archive.sh`** ⇒ 与 `fix-worktree-archive-branch-merge`（ADR-0061）争同一批行号 ⇒ 建议串行落地（先 ③ 后 ①，或同一次改动内先加 helper 再加调用点）。
  - **`archive_premerge_check` 的接口必须支持「无 worktree」**（`wt_path` 为空 + dirty 判据跳过）⇒ 这是对 ③ 的**接口契约要求**，需同步进 ③ 的 AC（见「顺带发现」）。
  - 建分支失败时的退回路径（worktree）会让「本次是 lightweight」的语义与实际模式不一致 ⇒ 必须写进 handoff 的 `execution_mode_decision.reason`（不静默）。
  - 分支清理失败时**不得**让「归档已成功」整体失败（与 ADR-0061 的 cleanup 契约一致）。
- **兼容性**：worktree 路径行为不变；本仓当前**不可达** lightweight（`task_count = 5` 硬编码 + `LEGACY_EXEC_MODE` 覆盖当前都不产出 lightweight —— ⚠ 这是**当下事实**不是结构保证）⇒ 本仓无行为变更；`iteration.json` 的 schema 不变（只是轻量路径开始写 `archive_commit_sha`）。
- **依赖**：**必须先于 `fix-execution-mode-decision` 的执行模式部分落地**（D 项 AC #4 的两段验收）；**依赖** `fix-worktree-archive-branch-merge`（ADR-0061 的 `archive_premerge_check`）先落地 —— 本项是它的第二个调用点。

## 顺带发现（登记，不在本项修）

- `verifier-lifecycle` 的 scenario「Lightweight current branch mismatch ⇒ fail closed」今天**未实现**（`rdd_verify_cmd.py` 只判 ref 存在性，无 current-branch 校验）⇒ 独立缺口；本项**不**实现它（若顺手实现，会在「归档前已切回默认分支」的时序下反向失败）。
- `wt_path_for_branch` 会把主仓列为 worktree ⇒ `discover_ship_changes` / `select_worktree` 会把主仓登记成 worktree（`rddf status` / dashboard 的展示效应）⇒ known behavior。
- `skills/execute/SKILL.md:57-59` 与 `README.md:129` 的 `RDDF_EXECUTION_ROOT` 死机制陈述（ADR-0036 修订的 backlog 已记）。

## 审稿记录

metis 1 轮（2026-11-17，planner 阶段 gap 分析）。逐条处置见下节。

### metis 处置记录（2026-11-17）

metis 判定：主目标**不是**「lightweight 能归档」，而是「让 D 项能安全放开小改动」；「让 handoff 不再说假话」几乎没有价值（全仓**无人**读 handoff 的 `branch` 字段 ⇒ 真正的缺陷是「ref 不存在」）。以下逐条处置。

| # | metis finding | 处置 |
|---|---|---|
| P0-1 | **【最高危】execute 默认不 commit ⇒ 轻量分支是空壳 ref** ⇒ 验证锚点指向不含本次改动的提交（可能假通过）⇒ 合入门 ③ `git cherry` 判「内容等价」（两 tip 相同 ⇒ 等价恒真）⇒ 放行 ⇒ 归档把**未提交的实现文件**留在主干工作区 ⇒ **「不可归档」换成「假归档」**（ADR-0061 要消灭的静默失败原地复活） | ✅ **全部采纳** ⇒ 新增 What Changes §2「提交归属政策」+ 3 条 AC（零提交 ⇒ 拒绝 + 给 commit 命令；**不引入 auto-commit**（`git add -A` 会把别人的改动一起提交）；断言分支 tip 的父提交 = 默认分支 tip 防基点错位）⇒ Why 段加了这条更重的意图 |
| P0-2 | 「复用 ADR-0061 的合入门」不可判定（该函数今天不存在）；且 `archive_premerge_check` 的 `wt_path` 在 lightweight 下**无正确取值** —— `git -C <main_root> status --porcelain` 看到**整个主仓** ⇒ 别的 change 的脏文件被误判为本 change 的未提交改动 ⇒ 假拒绝，且指引文案会诱导用户把**别人的改动** commit 进来 | ✅ **全部采纳** ⇒ What Changes §3 改为「**语义同源、判据按模式分叉**」：⓪/②/③/④ 原样复用，①（worktree dirty）在 lightweight 下**不适用**（`wt_path` 传空）⇒ 改用 §2 的分支提交归属检查；主仓 dirty **只警告不拒绝** ⇒ 新增 AC「dirty 语义分叉生效」；并把「`archive_premerge_check` 由 ③ 新建、本项是第二个调用点」写成显式依赖；「不新造第二套判定」加了限定 |
| P0-3 | 「建分支」时点与起点二义（裸 `checkout -b` 的基点可能是上一个 change 的分支 / detached HEAD ⇒ 锚点、`merge-base`、`cherry` 全失真）；分支已存在的三档政策未写死 | ✅ **全部采纳** ⇒ What Changes §1 写死：P2 起始、显式起点 = 默认分支 tip；分支已存在三档（tip == 默认 tip ⇒ 复用 / tip != 默认 tip ⇒ fail-closed 退回 worktree / 不存在 ⇒ 创建）；`checkout` 失败且 worktree 也建不起来 ⇒ 退出码 3 + 明确文案 |
| P0-4 | fail-closed 时 handoff 的 `reason` 落不到具体字段（顶层无 `reason`；`execution_mode_decision.reason` 存在但 mode 不改会留下「mode=lightweight / 实际 worktree」的矛盾） | ✅ **全部采纳** ⇒ 范围 §2 + What Changes §1 + AC「handoff 的 `execution_mode_decision.mode` 与 `reason` 与真实模式一致」 |
| P0-5 | 「与 `fix-worktree-archive-path` 的 acceptance-8 做 MODIFIED 对齐」**流程上不成立**（已归档 change 的 proposal 是历史记录，不能 MODIFIED；能改的只有已采纳 spec 的 delta）；AC#9（`verifier-lifecycle` 场景「标注前提已成立」）是空操作且掩盖了一处 spec/实现漂移（该 scenario 今天**未实现**）；AC#11 不可由本项证伪 | ✅ **全部采纳** ⇒ 范围 §6 改为「对**已采纳** spec 写 delta」+「在审稿记录里登记推翻该 AC」；AC#9 改为「**不实现**该 scenario，只登记为独立缺口」（进「顺带发现」）；AC#11 改为「归 D 项，本项只登记不证伪」 |
| P1-6 | 2×2 矩阵缺失（`openspec_tracked: true` × lightweight 这一格完全没提，而 `archive-auto-commit` 的 MUST 要求它调 helper） | ✅ 采纳 ⇒ 范围 §4 + What Changes §3/§4 + AC「2×2 矩阵」 |
| P1-7 | 缺「内容真的在分支上」的前置校验（用户中途手工切分支时，归档会对着一个内容不在此分支的分支宣称成功） | ✅ 采纳（与 P0-1 的提交归属检查合并）⇒ 提交归属检查 + 「拒绝路径不得改变主仓 HEAD」进 AC |
| P1-8 | `wt_path_for_branch == main_root` 会被当 worktree（`git worktree list --porcelain` 含主 worktree）⇒ 任何「顺手复用 `archive_change`」的实现会对着主仓跑 `git worktree remove`，且 `:282` 的「✅ Worktree 已删除」无条件打印 | ✅ 采纳 ⇒ 范围 §5 + What Changes §3（`wt_path` 传空、不得对主仓执行 worktree remove）+ AC「`wt_path == main_root` 时不执行 `git worktree remove`」；`discover_ship_changes` / `select_worktree` 的展示效应登记为 known behavior（不修） |
| P1-9 | abort / 清理语义缺失（P2 失败后主仓 HEAD 留在 `openspec/<change>`、分支残留成为下一轮「分支已存在」的输入） | ✅ 采纳 ⇒ What Changes §6 + AC「abort 语义」 |
| P2-10 | 「补齐归档路径」要从「等价」改成**枚举 + 排除清单**；且不得委托 `archive_change`（其 wt_path 前置检查要求 worktree 存在 ⇒ 与 ③ 撞车） | ✅ 采纳 ⇒ What Changes §3 的步骤清单（枚举 6 步 + 显式不补 4 步 + 理由）+ Out Scope「不委托 `archive_change`」 |
| P2-11 | 既有测试的预期破坏面未写（`test_phase3_archive_delegation.bats` 的「`openspec archive` 恰好 1 处」源码守卫、`test_rdd_builder_phase3_archive.bats` 的 12 个 fixture、`test_phase2_commit_gate.bats`） | ✅ 采纳 ⇒ AC「既有测试的预期破坏面已处理」+ Impact「与 ③ 串行落地」 |
| P2-12 | 「本仓不可达 lightweight」只是**当下事实**不是结构保证（`LEGACY_EXEC_MODE` 覆盖也能产出 lightweight）⇒ 测试不能依赖「跑 P1.5 自然产出 lightweight」 | ✅ 采纳 ⇒ e2e AC 明确「**必须注入 handoff fixture**」+ 兼容性段加「⚠ 当下事实不是结构保证」 |
| 边界 3 | 分支存在但被既有 worktree 占用 ⇒ `git checkout openspec/<name>` 失败 ⇒ 「fallback 到 worktree」也不可行（worktree 也建不起来）⇒ 需要第三态兜底文案 | ✅ 采纳（并入 P0-3 的三档 + 退出码 3 文案） |
| 边界 5 | `rddf` 自身的判定会因「主仓在 `openspec/*` 上」而反转（`wt_path_for_branch` 返回主仓 ⇒ `archive_change` 的前置检查不再拒绝；`discover_ship_changes` / `select_worktree` 把主仓当 worktree） | ✅ 采纳（登记为 known behavior + 本项的 `wt_path == main_root` 守卫） |
| 边界 7 | 归档时默认分支已被别的 change 推进 ⇒ `git branch -d` 因非 ancestor 失败 ⇒ 只有 `FORCE_BRANCH_DELETE` 能删 ⇒ 「已删除」AC 在该情形不成立 | ✅ 采纳 ⇒ AC「分支清理失败 ⇒ 只警告、归档仍成功（返回码语义与 worktree 路径一致）」 |
| 边界 8/9 | `openspec_tracked: false` × lightweight ⇒ dirty 看不见 artifact 改动、`commit_archive_moves` 短路；`true` × lightweight ⇒ 归档产物是 tracked 文件，不 commit 就把脏树留给下一个 change | ✅ 采纳（2×2 矩阵 AC 覆盖两格） |
| 边界 10 | 重归档（上次归档已删分支）⇒ 合入门 ⓪ 拒绝 ⇒ 轻量路径需要同款 `ARCHIVE_ALLOW_UNMERGED` 出口，且不得与 `FORCE_BRANCH_DELETE` 同时生效 | ✅ 采纳（并入 ADR-0061 的既有语义：opt-in 覆盖全部拒绝态 + 与 FORCE 互斥） |
| 边界 12 | detached HEAD / submodule / 非 git 仓库 / 带脏树切默认分支失败 ⇒ 需要明确文案与退出码 | ✅ 采纳（并入 P0-3 的「退出码 3 + 明确文案」） |
| 隐含意图 | 「让 handoff 不再说假话」几乎没有价值（无人读该字段） | ✅ 采纳 ⇒ Capabilities 里的「下游不再被假声明误导」改为「**不留下与真实模式矛盾的声明**」，并把真正的主线（提交归属 + 合入判定）提到最前 |

