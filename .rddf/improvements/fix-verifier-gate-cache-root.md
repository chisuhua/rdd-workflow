---
优先级: P1
priority: P1
来源: 2026-11-17 第八批 5 项归档过程发现（follow-up E）——归档门内部与验证写端对「cache 在哪个根、
  用哪个 ref 作锚点」有三套互不一致的约定 ⇒ 同一份 cache 在不同路径下判 fresh 或 stale
阶段: phase-2
分类: bugfix
类型: bugfix
状态: implemented (2026-11-17)

生成时间: 2026-11-17
roadmap_ref:
---

# fix-verifier-gate-cache-root

**主题**: 阶段步骤化执行

## 架构依据

### 仓库已有的契约（先看它，因为它就是答案）

`skills/rdd-builder/scripts/phase3_archive.sh:55-66`（本批第 2 项写入的）已经**明文规定**：

> **CONTRACT**: the gate reads the verdict cache from `$TASKS_ROOT/.rddf/state/verifier/.ac-verdict-<change>.json` and compares its `codebase_commit` against `git -C $TASKS_ROOT rev-parse HEAD`. Verification must therefore run in the SAME root as `$TASKS_ROOT` — in worktree mode that means `RDDF_PROJECT_ROOT=<worktree>`, not the canonical (main-repo) state root the resolver picks by default; otherwise the cache and the sha anchor come from different roots and the gate reports "stale" even though nothing changed.

⇒ **契约是「单根 = tasks_root」**：tasks.md、verdict cache、sha 锚点三者同根，验证必须在同一个根里跑。
**本项要做的是让所有实现点遵守这条已存在的契约，而不是另立一套。**

### 缺陷：根与锚点各有两套写法

| 参与方 | 文件:行 | 根 | 锚点 ref |
|---|---|---|---|
| 门（bash 段） | `_lib/archive.sh:456` | `$tasks_root` | `:458` `git -C "$tasks_root" rev-parse **HEAD**` |
| 门（python 段） | `_lib/verifier/archive_gate.py:113` | **`_main_repo_root(cwd)`**（自己 `git rev-parse --git-common-dir` 推导） | `:201` `resolve_branch_tip` = **`openspec/<change>`** |
| 写端（代码路径） | `_lib/verifier/branch.py:15-28` `resolve_implementation_commit` | 调用方传入 | **`openspec/<change>`**（分支 tip） |
| 写端（文档路径） | `skills/rdd-verifier/SKILL.md:269` | agent 的 cwd（相对路径 `.rddf/state/verifier/...`） | **`<git rev-parse HEAD>`** |
| 写端（批量 CLI） | `_lib/cli/rdd_verify_cmd.py:39-40` → canonical resolver | **主仓** | 分支 tip |
| 写端（skill 脚本） | `skills/rdd-verifier/scripts/run_verification.sh:28` `git rev-parse --show-toplevel` | **worktree**（从 worktree 跑时） | 分支 tip |

⇒ **两处根不一致 + 两处锚点表达式不一致**：

1. **根**：门内部 python 段自行改用主仓根（`archive_gate.py:25-33` 的 docstring 把这个分裂写成「deliberately NOT unified with the caller's root」）⇒ 与 `phase3_archive.sh` 的 CONTRACT 相反。
   实测后果：走 skill 流程时 cache 落在 **worktree**（`run_verification.sh:28` 用 `--show-toplevel`），python 段却去**主仓**找 ⇒ 找不到 ⇒ 降级；而从主仓批量跑 `rddf rdd-verify` 时 cache 在主仓，bash 段却按 tasks_root（worktree 模式 = worktree）找 ⇒ 同样找不到。
   ⇒ **「必然误拒」只在特定写端成立**（本仓 `openspec_tracked: false` ⇒ tasks_root == main_root ⇒ 无症状，所以本批没撞上；而 `openspec_tracked` 默认 `true`）。
2. **锚点**：写端代码路径记**分支 tip**，SKILL.md 让 agent 记 **HEAD**；读端 bash 比 **HEAD**、python 比**分支 tip** ⇒ 同一份 cache 在不同路径下可能判 fresh 也可能判 stale。
   最尖锐的一例：**false 分支里 `switch_to_default_branch` 把主仓切到默认分支**（`_lib/archive.sh:609`）⇒ 此后 `git -C "$tasks_root" rev-parse HEAD` = **默认分支 tip**，而 cache 的 `codebase_commit` = **分支 tip** ⇒ 二者不等 ⇒ 门判 stale。
   ⇒ 只有当 cache 是按 SKILL.md 的「HEAD」写的（本批 5 项即如此）才碰巧相等 —— **靠巧合正确**。

3. **第三处根传递**：`archive.sh:488` 把 `RDDF_PROJECT_ROOT="$tasks_root"` 传给 integrity helper（`rdd_verify_cmd.py --validate-cache-for-archive`），而该 helper 用**同一个** `project_root` 既读 proposal.md 又读 cache ⇒ 若只改 `:456` 的 cache 路径，这一处仍会读错根 ⇒ 误拒从「no valid verdict cache」换成「cached verdict is incomplete」。

### 附带发现的两个既有缺陷

- `_lib/verifier/archive_gate.py:27-41` 的 `_main_repo_root` 用 `--git-common-dir` 推导 ⇒ 在**子模块**里指向 superproject 的 `.git/modules/<n>`，`.parent` 得到 `.git/modules`（错）。canonical 的 `resolve_project_root`（`_lib/cli/__main__.py:62-79`）明确先判 `--show-superproject-working-tree`（ADR-0033）。
- `_lib/archive.sh:485-487` 有一个**同名不同义**的局部变量 `main_root`，指的是 **pkg 安装目录**（用来定位 `_lib/cli/rdd_verify_cmd.py`），与 `:589` 的 `main_repo_root()`（仓库根）完全不是一回事。

## 范围

- **In Scope**：① 门内 python 段改用**调用方传入的根**，与 bash 段同根（= tasks_root，遵守既有 CONTRACT），不再自行 `_main_repo_root`；② 锚点表达式统一为**分支 tip**（`git rev-parse --verify --quiet openspec/<name>`），与写端代码路径 `resolve_implementation_commit` 一致，且**与根无关**；③ `SKILL.md:269` 的 `codebase_commit` 文案改为分支 tip；④ `archive.sh:488` 的 integrity helper 拆根（proposal 取 tasks_root、cache 取同根）；⑤ 写端收敛：`run_verification.sh:28` 改用 canonical resolver，`SKILL.md` 写明「cache 路径由 resolver 决定，不要在 worktree 里写相对路径」；⑥ `phase3_archive.sh:55-66` 的 CONTRACT 段同步为新的锚点表达式；⑦ 测试矩阵 2×2（见 AC）。
- **Out Scope**：不改 cache 文件的**格式**（`cache.py:200-205` 已把「双路读旧路径」定性为会让 bash 与 python 判据分裂的反模式 ⇒ 不引入双路 fallback）；不改 `decide_execution_mode` 等无关项；不追溯修复历史 cache 文件；不改 `SKIP_RDD_VERIFIER` / `FEATURE_ARCHIVE_GATE=hard` 的语义（只保证它们的顺序不被新代码打乱）；**不新造第三个根解析函数**（复用既有 `main_repo_root()` / `resolve_project_root()`）。

## Why

真正的用户问题不是「根解析不统一」，而是：**归档门声称「没验证过」，而验证明明做了** —— 用户于是不再相信这道门，转而去开 `SKIP_RDD_VERIFIER` 旁路。AC 验证是这套工作流的最后一层质量保证，把它变成「默认不跑」比「跑得慢」严重得多。

metis 指出的第二层：同类问题（门与写端对根的约定不一致）在本批**两天内出现两次**（本项 + `fix-worktree-archive-branch-merge`）⇒ 用户真正想买的是**防止复发的契约**，而不是「把这行改对」⇒ 因此本项把「契约表」本身当作交付物（AC 覆盖三张数据：cache 文件 / `iteration.json` 的 `verification` 字段 / `rdd-verify-context`）。

第三层：`skills/rdd-builder/SKILL.md` 让 agent 手写 cache 时用 `<git rev-parse HEAD>`，而代码写端用分支 tip —— **文档与实现的锚点表达式不同**，这正是「读文档的 agent 照做就判 stale」的来源。

## What Changes

1. **Task 0（事实基线，先测再改）**：实测三条写端路径的 cache 实际落点与锚点值，作为实施依据（命令写进 PR 描述）：
   - ①从 worktree 跑 `bash skills/rdd-verifier/scripts/run_verification.sh <name>`；
   - ②agent 按 SKILL.md 相对路径在 worktree 写；
   - ③从主仓跑 `rddf rdd-verify <name>`。
   ⇒ 结论写进 `phase3_archive.sh` 的 CONTRACT 段。
2. **python 段同根**（`_lib/verifier/archive_gate.py`）：`check_archive_readiness` 使用**调用方传入的 `project_root`**（= tasks_root），不再 `_main_repo_root(cwd)`；顺带消除子模块缺陷（canonical `resolve_project_root` 已处理 superproject）。docstring 改写为引用 `phase3_archive.sh` 的 CONTRACT（不再自述「deliberately NOT unified」）。
3. **锚点统一为分支 tip**：
   - `_lib/archive.sh:458` 的 `current_sha` 由 `git -C "$tasks_root" rev-parse HEAD` 改为 `git -C "$tasks_root" rev-parse --verify --quiet "openspec/<change>"`（与 `resolve_implementation_commit` 同语义、**与根无关**）⇒ 顺带消灭 false 分支切到默认分支后 HEAD ≠ 分支 tip 导致的必然 stale；
   - `skills/rdd-verifier/SKILL.md:269` 的 `"codebase_commit": "<git rev-parse HEAD>"` 改为 `<git rev-parse --verify --quiet openspec/<change>>`；
   - `skills/rdd-builder/scripts/phase3_archive.sh:55-66` 的 CONTRACT 段同步。
4. **integrity helper 拆根**（`_lib/archive.sh:488` + `_lib/cli/rdd_verify_cmd.py --validate-cache-for-archive`）：proposal.md 取 tasks_root、cache 取**同一根**（二者本就应同根 ⇒ 实际改动是「不要再用一个 env 变量承担两个根」⇒ 改成显式 CLI 参数）。
5. **写端收敛**：
   - `skills/rdd-verifier/scripts/run_verification.sh:28` 的根解析改用 canonical resolver（不再 `--show-toplevel`）；
   - `skills/rdd-verifier/SKILL.md` 写明「cache 路径由 resolver 决定；不要在 worktree 里写相对路径」。
6. **命名收敛**：`_lib/archive.sh:485-487` 的局部 `main_root`（pkg 目录）改名 `pkg_root`；不新造 `archive_state_root`，复用既有 `main_repo_root()` / `resolve_project_root()`。
7. **双 cache 并存策略**（写进 CONTRACT 段）：主仓与 worktree 同时存在 cache 时，**以 CONTRACT 规定的根为准**，另一侧存在只 warn、不 fallback（与「不引入双路 fallback」一致，但落到纸面）。
8. **测试矩阵（2×2，须有判别力）**：
   - 造**真** worktree（`git worktree add -b openspec/<name>`）+ worktree 内放 `proposal.md` / `tasks.md`；
   - cache 的 `codebase_commit` = 分支 tip；
   - 场景 A：cache 只在主仓 ⇒ 门 **READY**；
   - 场景 B：cache 只在 worktree ⇒ 门 **READY**（旧行为下也是 READY ⇒ 故必须**同时**断言 A 与 B 各自的「读的是哪一侧」，否则测试无判别力）；
   - 场景 C：cache 的 `codebase_commit` ≠ 分支 tip ⇒ 仍判 **stale**（不得放宽 freshness）；
   - 顺带修 `tests/integration/test_archive_gate.bats:39-50` 的**假绿灯**：该用例的伪 worktree **没有 `proposal.md`**，而 AC 门在 `_lib/archive.sh:455` 要求 proposal 存在 ⇒ 它根本没测到 AC 门。

## Acceptance

- [x] 门内 python 段使用**调用方传入的根**（= tasks_root），不再自行 `_main_repo_root`；子模块场景下解析正确（复用 canonical `resolve_project_root`）
- [x] 锚点表达式统一为**分支 tip**（`git rev-parse --verify --quiet openspec/<name>`）：bash 段、写端代码路径、SKILL.md 文案、`phase3_archive.sh` CONTRACT 段**四处一致**
- [x] false 分支在 `switch_to_default_branch` 之后跑门时**不再**必然判 stale（回归用例覆盖）
- [x] `skills/rdd-verifier/SKILL.md` 的 `codebase_commit` 文案改为分支 tip（不再写 `<git rev-parse HEAD>`）
- [x] `archive.sh:488` 的 integrity helper 不再用一个 env 变量承担两个根（proposal 与 cache 各取自明确的根）；worktree 模式下**不出现** `cached verdict is incomplete` 误拒
- [x] `run_verification.sh` 的根解析改用 canonical resolver；SKILL.md 写明「cache 路径由 resolver 决定」
- [x] `phase3_archive.sh:55-66` 的 CONTRACT 段与新锚点表达式一致；双 cache 并存策略写进该段（以 CONTRACT 根为准，另一侧只 warn）
- [x] `skills/rdd-verifier/SKILL.md` 列出三张数据的落点契约表：cache 文件 / `iteration.json` 的 `verification` 字段 / `rdd-verify-context` 各在哪个根
- [x] 测试矩阵 2×2 有判别力：场景 A（cache 只在主仓）与场景 B（cache 只在 worktree）各自断言「读到哪一侧」；场景 C（锚点不符）仍判 stale
- [x] `tests/integration/test_archive_gate.bats:39-50` 的假绿灯被修（补 `proposal.md`），不再产生「没测到 AC 门却绿」的用例
- [x] bypass 顺序：`state/tasks` 根解析失败时，`SKIP_RDD_VERIFIER=yes` + `RDDF_VERIFIER_BYPASS_REASON` **仍能放行并留审计**（不因新代码提前 return 而被跳过）
- [x] `FEATURE_ARCHIVE_GATE=hard` 的行为不变（与根无关）
- [x] 命名收敛：`_lib/archive.sh:485-487` 的局部 `main_root` 改名为 `pkg_root`；未新造第三个根解析函数
- [x] `./test.sh --unit` + `bats tests/integration/test_archive_gate.bats` + `bats tests/integration/test_rdd_verifier*.bats` 全绿

## Capabilities

- 「归档门说没验证过」与「验证确实做了」不再同时成立 ⇒ 用户不必靠旁路绕过 AC 验证
- 「哪个根放什么、用哪个 ref 作锚点」成为**写在仓库里的契约**，而非散落在 6 处实现里的隐含约定
- 写端与门对锚点表达式一致 ⇒ 文档与实现不再给出不同指令
- 同类漂移（门与写端各写各的）有了可复用的契约模板，降低复发概率

## Impact

- **影响面**：`_lib/archive.sh`（锚点表达式 + `:488` 的 helper 调用 + 局部变量改名）、`_lib/verifier/archive_gate.py`（根解析 + docstring）、`_lib/cli/rdd_verify_cmd.py`（integrity helper 的根参数）、`skills/rdd-verifier/scripts/run_verification.sh`（根解析）、`skills/rdd-verifier/SKILL.md`（锚点文案 + 落点契约表）、`skills/rdd-builder/scripts/phase3_archive.sh`（CONTRACT 段）、`tests/integration/test_archive_gate.bats`（修假绿灯）+ 新增矩阵用例。
- **风险**：
  - 锚点从 HEAD 改为分支 tip ⇒ **历史 cache 全部失效一次**（它们的 `codebase_commit` 记的是 HEAD）⇒ 需重跑一次验证。这是**一次性**代价，但必须在变更说明里写明。
  - 「写端收敛到 canonical resolver」会改变 `run_verification.sh` 的落点 ⇒ 若有别的代码依赖旧落点，需一并核对（实施时 grep）。
  - 本项与 `fix-worktree-archive-branch-merge` **改同一段代码**（`archive_gate_check` 的调用点与判定输入）⇒ 建议合并为一次改动，或明确 rebase 顺序（先本项、后该项）—— 原 Impact 里「本项只读解析、风险低、建议先落」的排序理由**不成立**（锚点一改就与它抢同一批行号）。
- **兼容性**：cache 文件格式不变（只改写入的 ref 表达式与落点）；`SKIP_RDD_VERIFIER` / `FEATURE_ARCHIVE_GATE` 语义不变；本仓（`openspec_tracked: false`）路径行为不变（tasks_root == main_root，且分支 tip 在 false 分支切到默认分支后仍能解析）。
- **依赖**：与 `fix-worktree-archive-branch-merge` 同批，建议连续实施；本项不依赖 `fix-execution-mode-decision`。

## 审稿记录

metis 1 轮（2026-11-17）。逐条处置：

- **采纳 P0-1（事实基线前置）**：原草稿把「cache 落在哪个根」写成「实施时须先实测」的风险注脚。已改为 What Changes 的 **Task 0**（先测三条写端路径的落点与锚点值，结论写进 CONTRACT 段）。
- **采纳 P0-2（锚点轴选错 ⇒ 改为分支 tip）**：原草稿把问题写成「HEAD 取主仓还是 worktree」—— **这是假问题**：写端代码路径记的是**分支 tip**（`resolve_implementation_commit` = `git rev-parse --verify --quiet openspec/<change>`），不是 HEAD。已把锚点统一为分支 tip（与根无关）⇒ 直接消灭该二选一，并顺带修掉 false 分支切到默认分支后 HEAD ≠ 分支 tip 的必然 stale。
- **采纳 P0-3（不能只改 reader）**：已加「写端收敛」条（`run_verification.sh` 改用 canonical resolver；SKILL.md 写明路径由 resolver 决定）。
- **采纳 P1-1（`phase3_archive.sh:55-66` 是权威文本）**：原草稿全篇未提它。已列为 In Scope 必改，并在「架构依据」开头引用它作为**已有契约**（本项的收敛目标是遵守它，而非另立一套）。
- **采纳 P1-2（`:488` 的第三处根传递）**：已加 What Changes 第 4 条 + AC。
- **采纳 P1-3（`_main_repo_root` 的 submodule 缺陷）**：原草稿把它判为「对的」是**事实错误**（`--git-common-dir` 在子模块指向 superproject）。已改为迁到 canonical `resolve_project_root`（ADR-0033）。
- **采纳 P1-4（测试矩阵要有判别力）**：已改为 2×2 场景 A/B/C，并要求顺带修 `test_archive_gate.bats:39-50` 的**假绿灯**（缺 `proposal.md` ⇒ AC 门根本没被测到）。
- **采纳 P2（命名收敛 / 双 cache 策略 / bypass 顺序）**：均已写入（不新造第三个根函数；`:485-487` 的 `main_root` → `pkg_root`；双 cache 以 CONTRACT 根为准；bypass 顺序 AC）。
- **采纳（Impact 排序理由修正）**：原草稿称本项「只读解析、风险低、建议先落」—— 锚点一改就与 `fix-worktree-archive-branch-merge` 抢同一批行号，已改为「建议合并为一次改动或明确 rebase 顺序」。
- **记录未采纳（草稿原稿的「state 在主仓 / tasks 在 worktree」框架）**：仓库既有 CONTRACT（`phase3_archive.sh:55-66`）规定的是**单根 = tasks_root**，且明确要求「verification must run in the SAME root as $TASKS_ROOT」。原草稿据此推出的「state 恒在主仓」与该 CONTRACT 冲突 ⇒ 整段框架已按 CONTRACT 重写。

## 立项核查（2026-11-17，planner）

逐条把立项里的 `file:line` 断言落到实际代码上验，**全部通过**：

| 断言 | 核实结果 |
|---|---|
| `archive.sh:483/488-489` 的局部 `main_root` 实为 `script_dir/..`（= pkg root） | ✅ 命名确实误导（拿 pkg root 叫 main_root） |
| `archive.sh:488` 的 integrity helper 用 `RDDF_PROJECT_ROOT="$tasks_root"` 传根 | ✅ 一根两用（pkg root 找脚本 + tasks root 传给 helper） |
| worktree 模式下出现 `cached verdict is incomplete` 文案 | ✅ 存在 |
| `phase3_archive.sh` 有 CONTRACT 段 | ✅ 存在 |
| `skills/rdd-verifier/SKILL.md` 的 `codebase_commit` 文案 | ✅ 存在 |
| `skills/rdd-verifier/scripts/run_verification.sh:28` 用 `git rev-parse --show-toplevel` | ✅ 逐字一致 |
| `tests/integration/test_archive_gate.bats` 存在 | ✅ |

> 核查中的一次自我纠正：首次查的是 `_lib/verifier/run_verification.sh`（不存在），
> 得出「AC 落点不存在」的错误结论；实际文件在 `skills/rdd-verifier/scripts/` 下。立项无误。

---

## 实施记录（2026-11-17）

### 根因复盘

三处各写各的约定（根 ×2 + 锚点 ×2），实测后果：

| 参与方 | 旧根 | 旧锚点 |
|---|---|---|
| 门（bash 段）`archive.sh:456/458` | `$tasks_root` | `HEAD` |
| 门（python 段）`archive_gate.py:113` | 自推导的 `_main_repo_root(cwd)` | 分支 tip |
| 写端（代码路径）`branch.py:15` | 调用方传入 | 分支 tip |
| 写端（文档路径）`SKILL.md:269` | agent 的 cwd | `HEAD` |
| 写端（批量 CLI）`rdd_verify_cmd.py:39` | canonical resolver（主仓） | 分支 tip |

⇒ 走 skill 流程时 cache 落在 worktree、python 段却去主仓找；从主仓批量跑
`rddf rdd-verify` 时 cache 在主仓、bash 段却按 tasks_root 找 —— **两侧都可能
互相看不见对方的 cache**，门于是报「没验证过」。

### 关键发现：旧锚点其实**违反已签批 spec**

`openspec/specs/verifier-lifecycle/spec.md:98-100`（已采纳的 capability spec）：

> The verifier SHALL use the `openspec/<change>` branch tip as the implementation
> commit. … **Archive gate SHALL compare against the same commit. Arbitrary
> execution root HEAD SHALL NEVER be used as an archive authorization commit.**

⇒ bash 段的 `git -C "$tasks_root" rev-parse HEAD` 是**spec 违规**，不是「另一套
约定」。本项把它改回合规，而不是新立一套。

### 改动

**1. 两个根，各司其职（`_lib/verifier/archive_gate.py` + `_lib/archive.sh`）**

| 根 | 装什么 | 谁读 |
|---|---|---|
| **gate root**（`$tasks_root`，调用方传入） | change 的 artifacts（tasks.md / proposal.md）+ verdict cache | bash 段 + python 段 |
| **state root**（canonical project root，`resolve_project_root()`，ADR-0033 子模块安全） | 项目级 registry（`.rddf/state/iteration.json`，被 gitignore ⇒ 链接 worktree 永远没有）+ 批量 CLI 写的 cache | python 段（registry）/ 门（cache 兜底） |

- python 段不再自行 `_main_repo_root`（它在子模块里指向 superproject 的
  `.git/modules/<n>`，`.parent` 得到 `.git/modules` —— 错）；改用 canonical
  `resolve_project_root`。
- **双 cache 策略**：门根优先，state root 兜底；两侧都有 ⇒ 用门根并**报告**
  另一侧（不合并、不静默优先）。写端落在哪一侧都不会让门失效 —— 这正是
  「写端收敛到 canonical resolver」能成立的前提。

**2. 锚点统一为分支 tip（四处一致）**

- `_lib/archive.sh`：`git -C "$tasks_root" rev-parse --verify --quiet "openspec/$change_name"`
  （门根解不出时回落到 state root；ref 在共享仓库里，两侧同值）。
- `_lib/verifier/archive_gate.py::resolve_branch_tip`（本来就是分支 tip，未改语义）。
- `skills/rdd-verifier/SKILL.md`：`codebase_commit` 文案 + Per-Change Flow 的
  SHA 语义（`git rev-parse HEAD` → 分支 tip）。
- `skills/rdd-builder/scripts/phase3_archive.sh`：两段 CONTRACT 同步。

**3. integrity helper 拆根（`_lib/cli/rdd_verify_cmd.py`）**

`validate_cache_for_archive(project_root, change_name, *, proposal_root=None,
cache_root=None)`：proposal 取门根、cache 取**实际读到的那一侧**；bash 段改传
显式参数 `--proposal-root` / `--cache-root`（env 变量保留为兜底）。

**4. 命名收敛（`_lib/archive.sh`）**

局部 `main_root`（其实是 **pkg 安装目录**）→ `pkg_root`；与 `main_repo_root()`
（仓库根）不再同名。未新造第三个根解析函数。

**5. 写端收敛（`skills/rdd-verifier/scripts/run_verification.sh`）**

根解析：`RDDF_PROJECT_ROOT`（显式钉住）→ canonical project root（ADR-0033）
→ `$PWD`；不再裸用 `--show-toplevel`。SKILL.md 新增「落点契约表」。

### 测试

**新增 2×2 矩阵**（`tests/integration/test_archive_gate_cache_root.bats`，8 例，真 worktree）：

| 用例 | 断言 |
|---|---|
| A：cache 只在主仓 | READY + 输出点名主仓（读到哪一侧） |
| B：cache 只在 worktree | READY + **无**兜底消息（用的是门根） |
| C：锚点不符 | stale（freshness 未放宽） |
| D：两侧都有 | 门根胜 + 报告另一侧 |
| E：false 分支（门根=主仓，HEAD 已前移） | 分支 tip ⇒ 仍 fresh（**AC-3 的回归用例**） |
| F：cache 记的是默认分支 HEAD | stale |
| G：分支不存在 | fail closed（无 HEAD 兜底） |
| H：锚点解不出 + SKIP_RDD_VERIFIER | 仍能放行并留审计（**AC-11**） |

**变异验证**：把锚点改回 `HEAD` ⇒ E/F/G 变红；去掉 state root 兜底 ⇒ A/D 变红。

**新增单测**（`tests/unit/test_verifier_gate_cache_root.py`，10 例）：门根优先 /
state root 兜底 / 缺失两侧 / 锚点是分支 tip 而非 HEAD / registry 读 state root /
integrity helper 两根独立。

**修假绿灯**（`tests/integration/test_archive_gate.bats:39-50`）：该用例的伪
worktree 没有 `proposal.md`，而 AC 门要求 proposal 存在 ⇒ **它根本没测到 AC
门**。改为真 worktree + 真 cache，并断言输出含 "Reusing verifier verdict cache"。

**适配分支 tip 锚点的既有 bats**（6 个文件）：它们用 `git rev-parse HEAD` 播种
cache —— 那是 **spec 违规的旧锚点**。改为播种分支 tip 并（必要时）创建分支：
`test_ac_verifier_archive_gate` / `test_archive_gate_no_ac_fallback` /
`test_rdd_verifier_archive_compat` / `test_rdd_builder_phase3_archive`（轻量模式
⇒ 在 `openspec/demo` 分支上执行，与 `skills/execute/SKILL.md` § 工作模式一致）/
`test_phase3_archives_in_main_repo`（false 分支）。

### 一次性代价

锚点从 HEAD 改为分支 tip ⇒ **历史 cache 全部失效一次**（它们的
`codebase_commit` 记的是 HEAD）⇒ 需重跑一次验证。这是 spec 要求的语义
（HEAD 从来就不是合法的授权 commit），不是新引入的限制。

### 全量门抓到的一项（sha256 锁）

`tests/integration/test_rdd_quick_isolation.bats` 用 **sha256 锁**钉住
`_lib/archive.sh` 等四个文件的字节内容（「rdd-quick 不得污染这些文件」）。
本项合法改动了 `_lib/archive.sh` 的 AC 验证块 ⇒ 锁必须**重取基线**（与
2026-09-11 / 2026-09-28 / 2026-11-14 / 2026-11-16 四次先例同处理），并在
测试文件里写明为何 rdd-quick 的零污染不变式仍成立：rdd-quick 是 bypass 路径
（ADR-0047），它从不写 verdict cache ⇒ 对它是「查不到 → 审计旁路」，改动前后一致。

### 顺带发现（未修，已记录）

`skills/rdd-verifier/scripts/run_verification.sh` 无生产调用方（只有 agent 按
SKILL.md 调）—— 本项改的是它的**落点语义**，不改调用关系。
