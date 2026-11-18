---
优先级: P2
priority: P2
来源: 2026-11-18 `fix-bats-per-file-timeout` 验收过程中挖出的真 bug：`phase2_execute.sh` 的 worktree
  落点（worktree 主路径已修 120bddd；**lightweight→worktree 降级路径 :209 未修**）、 `phase1_plan.sh`
  / `phase1_5_deps.sh` 不认 PROJECT_ROOT。**原归因（`test_approve_proposal.bats` 写真仓 `openspec/`）经
  marker 扫描证伪** —— 债务被重述为「脚本的项目根锚定」，见
阶段: phase-2
分类: bugfix
类型: bugfix
状态: implemented (2026-11-18)
生成时间: 2026-11-18
roadmap_ref:
  project_id: 编排能力完善
  phase: phase-2
  theme: 编排能力完善
---

# fix-script-project-root-anchoring

**主题**: 编排能力完善

> 选 `编排能力完善` 而不是 `阶段步骤化执行`：本项判据落在**编排契约**（phase 脚本接收
> `PROJECT_ROOT` 的语义）与**门禁**上，与「阶段步骤化执行」描述的推进流程关系较弱。

## 架构依据

### 约定（不是既成事实）

`rdd-builder` 的 phase 脚本都接受 `PROJECT_ROOT`（默认 `$(pwd)`），期望「对 `$PROJECT_ROOT`
指向的项目操作，与调用者 cwd 无关」。**这个约定目前没有任何测试或门禁在守** —— 这正是本项的
理由。它也不是全局不变量：本仓另外几族脚本遵守的是 `_lib/_resolve_project_root_contract.yaml`
里以 `RDDF_PROJECT_ROOT` 为 env 名的另一套词（**`skills/_lib/` 是 shim，真源在 `_lib/`**）。

### 事实：同族脚本三套约定，其中两处仍是活的 bug

| 脚本 | 实际行为 | 判定 |
|---|---|---|
| `phase0_approval.sh` | 每条 IO 路径 `$PROJECT_ROOT/...`（:55-56、:148、:289）；:327 记录**相对**路径（描述字段，不据此做 IO） | ✅ 锚定（1 处豁免） |
| `phase2_execute.sh` 主路径 | `_carry_artifacts` 用 `$PROJECT_ROOT/$_rel`（:101）；:125 `cd "$PROJECT_ROOT"` 后建 worktree（今日修 120bddd） | ✅ 已修 |
| **`phase2_execute.sh` 降级路径** | lightweight 分支里若降级回 worktree（:180 / :199 设 `EXEC_MODE="worktree"`），:209 `WT_PATH=".rddf/wt/$CHANGE_NAME"` + :210 `git worktree add "$WT_PATH"` 是 **cwd 相对**；而该分支**从未**执行过 :125 的 `cd "$PROJECT_ROOT"`（那行在 `if [ "$EXEC_MODE" = "worktree" ]` 的主路径里） | ❌ **活 bug**（同一错误在另一条路径上重演） |
| `phase3_archive.sh` | 用 `$TASKS_ROOT` / `$main_root`，并对两个根的分工写了契约注释（:59-90） | ✅ 锚定 |
| **`phase1_plan.sh`** | :24 `PROPOSAL_PATH="openspec/changes/..."`、:30-31 `PLAN_OUTPUT_DIR=".rddf/plans"` + `mkdir -p`、:45 `TASKS_PATH="openspec/changes/..."` —— 全 cwd 相对；而同文件 :60-61 又把 `PROJECT_ROOT` 正确传给 python 做 iteration 记账 | ❌ 同文件两套 |
| **`phase1_5_deps.sh`** | :29-32 读 `.rddf/state/.plan-handoff.json`（cwd 相对）；:48/:67/:74/:78/:95 都是 `$PROJECT_ROOT` | ❌ 单点遗漏 |

> `phase2_execute.sh:241` 的 `[ -f ".rddf/plans/$CHANGE_NAME.md" ]` 在 `cd "$EXEC_DIR"` 之后，
> 语义正确 —— 本项改成 `$EXEC_DIR/...` 前缀是为了**不依赖 cwd**、顺便消掉一条豁免。

### 复现：`phase1_plan.sh` 读方向（只读即可证伪）

```bash
mkdir -p /tmp/fake/openspec/changes/demo && echo '# demo' > /tmp/fake/openspec/changes/demo/proposal.md
cd <真仓>
PROJECT_ROOT=/tmp/fake bash skills/rdd-builder/scripts/phase1_plan.sh demo
# 实际输出：proposal.md not found at openspec/changes/demo/proposal.md   （rc=2）
# ⇒ 它在**真仓**里找，假仓那份被无视。写方向同理：真仓里若恰有同名 change，
#   `mkdir -p .rddf/plans` 与 tasks.md 会落到**真仓**。
```

### 生产为什么看不出来

生产路径里 `cwd == PROJECT_ROOT`，相对路径**碰巧**正确。它只在两种调用下暴露：测试
（`cwd=真仓` + `PROJECT_ROOT=假仓`）、从子目录调用。

### 代价形态：随机红/绿

`phase2_execute.sh` 的实例：`git worktree add .rddf/wt/<name>` 落在**真仓** ⇒ 真仓多出
`openspec/<name>` 分支 + 整树检出（数千文件）⇒ 机器一忙就超过测试的 10s 预算 ⇒ `timeout` 返回
124 ⇒ 用例报「TTY hang」⇒ **被当成负载 flake 放过两次**（本轮之前两次全量门都归因到「4 核机器 /
load avg 20」）。一个「项目根没锚定」的写法，在验收面上的表现是随机红/绿 —— 它危险在**能骗过
验收**。

### 证伪记录：原归因是错的

上一轮把这条债务记成「`test_approve_proposal.bats` 用 `cd "$REPO_ROOT"` 只隔离 `TMP_STATE` ⇒
真实 `openspec/` 被写」。**实测不成立**：

```bash
marker=$(mktemp); sleep 1
bats tests/integration/test_approve_proposal.bats
find openspec .rddf -newer "$marker" -type f     # → 空
```

用例 1 在参数校验处就 `exit 2`（早于任何写盘）；用例 2 设了 `RDDF_PROJECT_ROOT`；而
`scripts/approve_proposal.sh` 只写 `$RDDF_PROJECT_ROOT/.rddf/state/`，**从不碰 `openspec/`**。
同一轮扫描覆盖 21 个「archive / phase / approve」候选 bats 文件：**没有一个写 `openspec/`**。
被标成「写 `.rddf/state/.doctor-report.json`」的 3 个复跑不复现 ⇒ 机器上其它 session 的 doctor
调用（本机 72 个 tmux client 并联），环境噪声。

### 门禁盲区

`tests/scripts/check_test_isolation.sh` 只有 4 条静态 grep（`os.chdir`、裸 `os.environ[K]=`、
`tempfile.mkdtemp`、假断言），**没有**「脚本是否锚定项目根」的检查 ⇒ 这一类对 CI 不可见（今日的
bug 都是人肉发现的，其中 `phase2_execute.sh` 的降级路径至今还在）。

## 范围

**In Scope**：

1. `skills/rdd-builder/scripts/phase1_plan.sh`：`PROPOSAL_PATH` / `PLAN_OUTPUT_DIR`（含
   `mkdir -p`）/ `PLAN_FILE` / `TASKS_PATH` 锚定 `$PROJECT_ROOT`；
2. `skills/rdd-builder/scripts/phase1_5_deps.sh`：legacy `.rddf/state/.plan-handoff.json` 读取
   锚定 `$PROJECT_ROOT`（其余路径已正确，不动）；
3. `skills/rdd-builder/scripts/phase2_execute.sh`：三处消掉 cwd 依赖 —— :209 `WT_PATH` 用
   `$PROJECT_ROOT/...`（降级路径的关键修复）、:126 `WT_PATH` 同样改绝对（消豁免）、:241 改
   `$EXEC_DIR/...` 前缀（消豁免）；
4. `tests/scripts/check_test_isolation.sh` 新增 `check_no_unanchored_repo_paths` —— **token 级**
   判定（见 What Changes §4）；
5. 测试：新增 `tests/integration/test_phase_root_anchoring.bats`（7 条用例）。

**门禁的扫描面（冻结，不写「等」）**：

```
SCAN_ROOTS = skills/rdd-builder/scripts/*.sh
```

只收本 change 有把握清零的面。收窄是刻意的：**本仓有多处已存在的同类写法**（见下方「已知残留
清单」），面一放宽，门第一次跑就红，只能靠豁免调参 ⇒ 门变成豁免清单。

**已知残留清单（本项不修，作为后续 change 的准确依据 —— 已逐个核实 file:line）**：

| 文件:行 | 形态 |
|---|---|
| `skills/rdd-planner/scripts/planner_stage_exit.sh:13` / `planner_stage_entry.sh:13` | `[ ! -d "openspec/changes/$CHANGE_NAME" ]`（两个文件 :6 都声明了 `PROJECT_ROOT` 却没用） |
| `skills/rdd-planner/scripts/planner_stage_exit.sh:21` | python 内 `Path('.rddf/state/.planner-state.json')` |
| `skills/roadmap/scripts/roadmap_migrate.sh:21-25` | 5 个相对路径常量；:46 `cd "$PROJECT_ROOT"` 之后才安全（**静态检查看不出顺序**，这类只能靠豁免） |
| `skills/roadmap/scripts/roadmap_migrate.sh:61` | `cp ... "openspec/changes/$CHANGE_NAME/tasks.md"` |
| `_lib/gate.py:168` / `:178` / `:197` | 裸 `openspec/changes/...` / `.rddf/state/.deps-output.md`；**同一文件**另 5 个 check 用了 `ctx["project_root"]`（:145/:156/:304）—— 与 `phase1_plan.sh` 完全同型，且它**是质量门本身**（判错 = 结论不可信） |

**Out of Scope**：

- **不改上述已知残留**（含 `_lib/gate.py`）—— 逐个修会把 bugfix 变成扫荡战；
- **不换 canonical resolver**：`PROJECT_ROOT` 默认值保持 `$(pwd)`。⚠ 后果（不是「变好了」）：未设
  env 且从 `docs/` 调用时 `PROJECT_ROOT=docs/`，改后 `mkdir -p` 会在 `docs/` 下造 `.rddf/plans`
  —— 一类**新的**游离写入，比改前「找不到 proposal 就 exit 2」更隐蔽。本项**不处理**（换 resolver
  就改了契约，与「不动契约」冲突）⇒ 记在这里作 follow-up；
- **不修本仓隔离门已有的 9 处历史违规**（`tests/unit/test_project_root_resolution.py:11`、`test_proposal_source_tracking.py:48/:57`、`tests/integration/test_guide_cross_container.bats:75`、`tests/unit/test_bypass_audit.py:31`、4 处 `assert ... or True`）：⚠️ 它们让 **master 的隔离门与 CI 的断言质量门现在就是红的**（来自 `2de1ab5` / `93c5ecd` / `b2ee7b3` 等提交），而 `./test.sh` **不跑**隔离门 ⇒ 本地全量门看不到 ⇒ 变红无人发现。本项只保证**新 check 单独绿**（AC-G2）；历史 9 处另案（改动面在 tests/unit，与本项无关）；
- **不加运行期写盘检测**（CI 跑 integration 子集 + 前后 mtime 快照）：本次 marker 扫描**已实证**
  它会被并联 session 的写误判（`.doctor-report.json` 那 3 次）⇒ 归属判定未解决前会制造假红；
- 不改 `phase0_approval.sh` / `phase3_archive.sh`（已锚定；`phase0:327` 的相对路径是描述字段）；
- 不改 `scripts/approve_proposal.sh` 的 `$(pwd)` 默认值（当前不会被错误驱动：唯一调用者已显式设
  `RDDF_PROJECT_ROOT`）—— 作为**已知同族形态**记在这份文档里；
- 不处理 `PROJECT_ROOT` 含空格 / 单引号 / symlink 的情形（`phase1_5_deps.sh` 把路径插进
  `python3 -c "... open('$ROOT/...') ..."` 的单引号字符串，改前改后同样会炸）；
- 不处理 `CHANGE_NAME` 含 `/` 时 `tasks.md` 父目录不存在导致的写失败（与本次改动无因果关系）。

## Why

### 为什么现在做

代价都在本轮，且都**污染了验收结论**：`phase2_execute.sh` 让真仓反复被塞进 worktree 与分支，并
两次伪装成「负载 flake」跳过；`phase1_plan.sh` 的读方向错误在测试里表现为「假仓有 proposal 却报
not found」—— 今天只是怪现象，真仓里一旦有同名 change 就是**静默写错仓库**。而
`phase2_execute.sh` 的**降级路径**至今未修：同一份错误代码换条走法就能重演一次。

### 为什么不是「测试隔离债」

隔离债的说法会让人去改测试（加 `cd`、加 env），但**根因在脚本**：测试是按契约设置了
`PROJECT_ROOT`。改测试只是把 bug 藏回去 —— 本仓踩过同型的坑：`test_known_failures_baseline.bats`
曾用「先写再还原」迁就一个有 bug 的 gate，结果基线被测试自己清空过 4 次。

### 为什么是静态门禁而不是运行期检测

静态门禁可判定（有/无锚定前缀）、零 CI 成本、不假红；运行期检测依赖「谁写的」这一归属判定，
在并联环境里判不准（见 Out of Scope）。先用可判定的那道门把复发率压到 0。

## What Changes

### 1. `phase1_plan.sh` —— 锚定项目根

```bash
# 改前
PROPOSAL_PATH="openspec/changes/$CHANGE_NAME/proposal.md"
PLAN_OUTPUT_DIR=".rddf/plans"
TASKS_PATH="openspec/changes/$CHANGE_NAME/tasks.md"
# 改后
PROPOSAL_PATH="$PROJECT_ROOT/openspec/changes/$CHANGE_NAME/proposal.md"
PLAN_OUTPUT_DIR="$PROJECT_ROOT/.rddf/plans"
TASKS_PATH="$PROJECT_ROOT/openspec/changes/$CHANGE_NAME/tasks.md"
```

### 2. `phase1_5_deps.sh` —— 只修 legacy 读取

```bash
# 改前
if [ -f ".rddf/state/.plan-handoff.json" ]; then
    LEGACY_EXEC_MODE=$(python3 -c "... json.load(open('.rddf/state/.plan-handoff.json')) ...")
# 改后
if [ -f "$PROJECT_ROOT/.rddf/state/.plan-handoff.json" ]; then
    LEGACY_EXEC_MODE=$(python3 -c "... json.load(open('$PROJECT_ROOT/.rddf/state/.plan-handoff.json')) ...")
```

### 3. `phase2_execute.sh` —— 降级路径（关键）+ 两处消豁免

```bash
# 降级路径（:209）：lightweight 分支从未 cd 过项目根 ⇒ 这里必须绝对
WT_PATH="$PROJECT_ROOT/.rddf/wt/$CHANGE_NAME"
# 主路径（:126）：cd 之后语义已对，但仍依赖 cwd ⇒ 改绝对，消掉一条豁免
WT_PATH="$PROJECT_ROOT/.rddf/wt/$CHANGE_NAME"
# :241：cd "$EXEC_DIR" 之后 ⇒ 显式前缀，消掉一条豁免
if [ -f "$EXEC_DIR/.rddf/plans/$CHANGE_NAME.md" ]; then
```

⚠ 保留 :122 的 fallback `WT_PATH="$PROJECT_ROOT"`（把 worktree 当主仓用时，绝对路径同样成立）。

### 4. `check_test_isolation.sh` — `check_no_unanchored_repo_paths`

**判定粒度 = token，不是行**。`cp "openspec/x" "$PROJECT_ROOT/openspec/x"` 必须报（行级判定会
整行放行 ⇒ 门空转）。

| 项 | 值（枚举常量，不用「等」） |
|---|---|
| 扫描根 | `RDDF_ISOLATION_SCAN_ROOTS`（默认 `skills/rdd-builder/scripts`，冒号分隔；**仅供测试指向 `$BATS_TMPDIR` 假仓**） |
| 单 check 模式 | `RDDF_ISOLATION_ONLY=<check_name>`（如 `check_no_unanchored_repo_paths`）—— 只跑这一个 check，退出码只反映它。**必需**：master 的隔离门**已经红了**（9 处历史违规，见 Out of Scope），不隔离就断言不了新 check 自己的退出码 |
| 命中 token | 引号 / heredoc 内以 `openspec/changes/` 或 `.rddf/` 开头的字面量路径 —— **不含裸 `openspec/`**（那是 git ref `openspec/<name>` 的形态，会误报） |
| 跳过 | 注释行（首个非空字符 `#`）、以及已命中 token 但同行含 allowlist 前缀的 token |
| 锚定 allowlist | `$PROJECT_ROOT` `$project_root` `$RDDF_PROJECT_ROOT` `$REPO_ROOT` `$main_root` `$TASKS_ROOT` `$WT_PATH` `$EXEC_DIR` `$root` `$BOOTSTRAP_REPO_ROOT` `$(git rev-parse --show-toplevel)` |
| 豁免标记 | 行尾 `# isolation-ok: <理由>`（**同一条物理行**；文件顶部标记**不生效**），理由长度 ≥ 10 |
| 豁免上限 | 本仓 `# isolation-ok` 行数 ≤ **2**（本项落地后应当只剩下面两条，超出即红） |
| 输出 | `file:line: <片段>` + `exit 1` |
| bypass | `ALLOW_TEST_POLLUTION=1` 时**仍**执行本 check（改为报告），打印 `skipped: check_no_unanchored_repo_paths`，并写 `.rddf/state/.bypass-audit.jsonl`（复用 `_lib/bypass_audit.sh`），不得静默 exit 0 |

**落地后应只剩的 2 条豁免**：

| 位置 | 理由（同时写进行尾标记） |
|---|---|
| `phase2_execute.sh:100` | `_rel` 是**相对片段**，稍后分别与 `$PROJECT_ROOT` / `$EXEC_DIR` 拼接 |
| `phase0_approval.sh:327` | 记录给调用方的**描述字段**（相对路径便于跨机复用），本脚本不据此做 IO |

**不需要改 CI**：`test.yml:39-41` 已调用 `bash tests/scripts/check_test_isolation.sh`，新 check
挂进同一脚本的 `checks` 数组即自动生效。

### 5. 测试（新增 `tests/integration/test_phase_root_anchoring.bats`）

| 用例 | 假仓最小文件集 / 前置 | 判据 |
|---|---|---|
| A 读方向 | `openspec/changes/demo/proposal.md` + `.rddf/plans/demo.md`（**含 `### Task ` 行**，否则脚本在 :41 `exit 2`，断言会假绿） | 不再报 `proposal.md not found`（改前 rc=2） |
| B 写落点 | 同 A | 假仓出现 `openspec/changes/demo/tasks.md` 与 `.rddf/plans/` **目录**；真仓那两条路径零写入（marker + `find -newer` **只扫这两个路径**） |
| C `phase1_5` | `openspec/changes/demo/proposal.md` + `.rddf/state/.plan-handoff.json`（legacy mode、无 blocker） | `exit 0` **且** stderr 的 `legacy .plan-handoff.json execution_mode='<值>'` 反映**假仓**那份（真仓写不同值对照） |
| D `phase2` 降级路径 | 假仓 + builder handoff 标 `lightweight`，但让 `lightweight_branch_prepare` 失败（例如 `_lib/archive.sh` 不可用）⇒ 降级成 worktree | worktree 落在**假仓** `.rddf/wt/`；真仓无新 worktree/分支（改前：落在真仓） |
| E 门禁正例 | `$BATS_TMPDIR/scanroot/x.sh` 含未锚定 `"openspec/changes/x"` | `RDDF_ISOLATION_SCAN_ROOTS=<假仓>` ⇒ `exit 1` 且输出含 `x.sh:` 行号 |
| F 门禁豁免 + 变异 | 同 E + 行尾 `# isolation-ok: cwd 已在目标根内` | `exit 0`；**变异**：删标记 ⇒ 必须重新变红 |
| G token 级判定 | 一行同时含 `"openspec/changes/x"` 与 `"$PROJECT_ROOT/openspec/changes/x"` | **必须**报（按行判定会漏） |

## Acceptance

- [x] **AC-A（读方向）**：`PROJECT_ROOT=/tmp/fake` + `cwd=真仓`（假仓有 `openspec/changes/demo/proposal.md`、真仓无）⇒ `phase1_plan.sh demo` 不再报 `proposal.md not found`（改前 rc=2）
- [x] **AC-B（写方向）**：同场景下 `openspec/changes/demo/tasks.md` 与 `.rddf/plans/` 目录落在**假仓**；marker + `find <真仓>/openspec/changes/demo <真仓>/.rddf/plans -newer` 断言真仓零写入
- [x] **AC-C（phase1_5）**：真仓与假仓 `.rddf/state/.plan-handoff.json` 写不同 `execution_mode` ⇒ `exit 0` 且 stderr 的 `legacy ... execution_mode='<值>'` 反映**假仓**那份
- [x] **AC-D（phase2 降级路径，活 bug）**：lightweight 模式被迫降级回 worktree 且 `cwd=真仓`、`PROJECT_ROOT=假仓` ⇒ worktree 建在**假仓**；真仓 `git branch --list 'openspec/*'` 与 `git worktree list` 不变（**改前该用例必须红**：先写用例跑红再修）
- [x] **AC-E（门禁正例）**：`RDDF_ISOLATION_ONLY=check_no_unanchored_repo_paths` + `RDDF_ISOLATION_SCAN_ROOTS=<假仓>` + 含未锚定 `"openspec/changes/x"` 的脚本 ⇒ `exit 1` 且输出含 `file:line`
- [x] **AC-F（门禁豁免 + 变异）**：同行加 `# isolation-ok: <≥10 字理由>` ⇒ `exit 0`；删标记后**必须**重新变红（两条都走单 check 模式）
- [x] **AC-G（token 级判定，防空转）**：一行内同时出现未锚定与已锚定 token（`cp "openspec/changes/x" "$PROJECT_ROOT/openspec/changes/x"`）⇒ **必须**报
- [x] **AC-G2（新 check 单独绿）**：`RDDF_ISOLATION_ONLY=check_no_unanchored_repo_paths` 在**本仓**（默认扫描根）⇒ `exit 0`（⇒ 新 check 不依赖那 9 处历史违规）
- [x] **AC-H（豁免预算是 2 条）**：`grep -c '# isolation-ok' skills/rdd-builder/scripts/*.sh` 恰为 **2**（`phase2_execute.sh:100`、`phase0_approval.sh:327`）；`cd "$PROJECT_ROOT"` 之后的相对路径形态（原 :126）**不再需要**豁免
- [x] **AC-I（bypass 可计量）**：`ALLOW_TEST_POLLUTION=1` ⇒ 打印 `skipped: check_no_unanchored_repo_paths` **且** `.rddf/state/.bypass-audit.jsonl` 新增一条（不得静默 exit 0）
- [x] **AC-J（生产不退化）**：真仓（`cwd == PROJECT_ROOT`）对一个 **`tasks.md` 尚不存在** 的假 change 跑 `phase1_plan.sh`，生成的 `tasks.md` 与改前逐字节相同（⚠ 必须用「不存在」场景 —— 已存在时脚本根本不写（:46），断言会恒真）
- [x] **AC-K（既有测试）**：`test_phase_auto_approve.bats` / `test_phase0_auto_approve.bats` / `test_rdd_builder_phases.bats` / `test_phase0_iteration_register.bats` / `test_lightweight_branch_and_archive.bats` 全绿
- [x] **AC-L（全量门）**：`./test.sh --full --regression` ⇒ `评估 M/M 个文件` + `未评估 0` + `新增失败 0`
- [x] **AC-M（不改 CI）**：`git diff <base> --stat` 不含 `.github/workflows/test.yml`（新 check 复用既有 CI step）

## Capabilities

- **MUST**：`phase1_plan.sh` / `phase1_5_deps.sh` / `phase2_execute.sh` 的 worktree 落点只由 `$PROJECT_ROOT` 决定（降级路径同样）；
- **MUST**：新 check 的扫描根是常量 `skills/rdd-builder/scripts`（可被 `RDDF_ISOLATION_SCAN_ROOTS` 覆盖，仅用于测试）；
- **MUST**：判定粒度是 **token** —— 同行混有未锚定 token 时必须报；注释行与 git ref（裸 `openspec/`）不得误报；
- **MUST**：锚定 allowlist 是**枚举**（11 个前缀，见 What Changes §4），**不得**用「等同类」模糊表述；
- **MUST**：豁免必须写在同一物理行、带 ≥10 字理由、本仓总数 ≤ 2；文件顶部标记不生效；
- **MUST**：bypass 时打印 `skipped: <check 名>` 并写 `.rddf/state/.bypass-audit.jsonl`；
- **MUST NOT**：改变生产路径下的行为（`cwd == PROJECT_ROOT` 时落点不变）；
- **MUST NOT**：把测试改成「先 `cd` 到假仓」来迁就脚本（那是把 bug 藏回去）；
- **MUST NOT**：把扫描根放宽到 `skills/**` 或 `_lib/**`（本仓已有 6 处已知残留，放宽即红 ⇒ 门会退化成豁免清单）。

## Impact

**影响面**：

| 文件 | 改动性质 |
|---|---|
| `skills/rdd-builder/scripts/phase1_plan.sh` | 3 处路径锚定（`mkdir -p` 目标随之正确） |
| `skills/rdd-builder/scripts/phase1_5_deps.sh` | 1 处 legacy 读取锚定 |
| `skills/rdd-builder/scripts/phase2_execute.sh` | 3 处：:209 降级路径（**bug 修复**）、:126 / :241 改前缀（消豁免） |
| `tests/scripts/check_test_isolation.sh` | 新增 1 个 check（token 级 + 豁免 + bypass 计量）+ 文件头 rationale + `checks` 数组注册 |
| `tests/integration/test_phase_root_anchoring.bats`（新增） | 7 条用例 |

**风险与对策**：

| 风险 | 对策 |
|---|---|
| 门禁只覆盖 `skills/rdd-builder/scripts`，`skills/rdd-planner`、`skills/roadmap`、`_lib/gate.py` 仍有同类写法 | 「已知残留清单」逐个列 file:line；AC 要求验收报告复核该清单，作为后续 change 的输入 |
| 门禁被读成「这类 bug 已闭环」 | 文档 + 验收报告都要写清：门抓的是「路径没前缀」这一**形态**，不是「写错仓库」这一**后果**；运行期检测明确列为未做 |
| 豁免条款被滥用（整文件豁免 / 空理由 / 无限增长） | 行级标记 + 理由 ≥10 字 + 总数 ≤ 2（AC-H）；AC-F 变异验证豁免真的生效 |
| `phase2` 降级路径改动影响 lightweight 模式 | 只改路径构造（相对→绝对），不碰三分支策略；`test_lightweight_branch_and_archive.bats` 与 `test_phase2_*` 全跑（AC-K） |
| 从子目录调用会变成在子目录造 `.rddf/plans` | 已写进 Out of Scope 并列为 follow-up（换 canonical resolver 需改契约，不在本项） |
| `phase1_plan.sh` 的 `skill_use` 分支依赖外部 skill 生成 plan 文件 | 判据不依赖它：用例 A/B 预置 plan 文件，只断言「不再报 not found」与「写落点」 |

**CI 现状（必须知道）**：master 的 `check_test_isolation.sh` 现在就红（9 处历史违规），CI 的「Assertion quality门」也因同一批 `or True` 而红 ⇒ **CI 在 master 上已经是红的**，本项不修那 9 处（见 Out of Scope），但会因新增单 check 模式而让「本项新 check」可被单独验证。

**与既有 ADR 的关系**：不引入新架构决策，不改 `PROJECT_ROOT` 语义与默认值，也不改
`_lib/_resolve_project_root_contract.yaml` 的三条不变量 —— 本项只是让三个脚本**遵守**已有的约定。
⚠ 已知词名分叉：phase 脚本用 `PROJECT_ROOT`（默认 `$(pwd)`），contract 用 `RDDF_PROJECT_ROOT`
（无 env 时 `git rev-parse --show-toplevel`）—— 本项不统一它们（那会改契约），只记录。

## 实施记录（2026-11-18）

### 落地形态

| 项 | 值 |
|---|---|
| 执行模式 | worktree（`.rddf/wt/fix-script-project-root-anchoring`，分支 `openspec/fix-script-project-root-anchoring`） |
| 提交 | `a3df546`（worktree）→ `443f689`（合入 master） |
| 修复的脚本 | `phase1_plan.sh`（3 条路径）、`phase1_5_deps.sh`（legacy 读取）、`phase2_execute.sh`（3 处 + 1 次 `cd`） |
| 门禁 | `tests/scripts/check_test_isolation.sh` 新增 `check_no_unanchored_repo_paths`（token 级 + 豁免 + bypass 计量 + 单 check 模式） |
| 测试 | 新增 `tests/integration/test_phase_root_anchoring.bats`（11 例） |
| 未动 | `.github/workflows/test.yml`（新 check 挂在既有 CI step 内） |

### AC 逐条结论

| AC | 结论 | 证据 |
|---|---|---|
| AC-A 读方向 | ✅ | 用例「phase1_plan: PROJECT_ROOT 指向假仓 ⇒ 读假仓的 proposal」：改前 rc=2（`proposal.md not found`，它在真仓里找），改后进入后续步骤并在假仓生成 `tasks.md` |
| AC-B 写落点 | ✅ | 用例「写落点跟随 PROJECT_ROOT ⇒ 真仓零写入」：marker + `find` **只扫那两条路径**（全仓扫描会被并联 session 的写误判 —— 本次立项时已实证），断言真仓零写入 |
| AC-C phase1_5 | ✅ | 用例「legacy plan-handoff 从 PROJECT_ROOT 读」：真仓与假仓各放一份不同 `execution_mode`，断言 stderr 的 `legacy ... execution_mode='lightweight'` 反映**假仓**那份 |
| AC-D phase2 降级路径（活 bug） | ✅ | 用例「lightweight 降级回 worktree 时，worktree 建在 PROJECT_ROOT（不是 cwd）」。**改前该用例是红的，并真的在真仓留下 `openspec/demo` 分支 + prunable worktree 条目**（已手工清理）。修法比计划多了一步：路径锚定**不够** —— `git worktree add` 注册到**当前目录**的仓 ⇒ 降级路径补 `cd "$PROJECT_ROOT"` |
| AC-E 门禁正例 | ✅ | 用例「未锚定 ⇒ exit 1 且报 file:line」（单 check 模式） |
| AC-F 门禁豁免 + 变异 | ✅ | 用例「行尾 # isolation-ok 理由 ⇒ 放行」；**变异**：删掉 `phase2_execute.sh:100` 的标记 ⇒ 「豁免恰好 2 条」用例变红 ⇒ 豁免机制真的生效 |
| AC-G token 级判定 | ✅ | 用例「同行同时有未锚定与已锚定 token ⇒ 仍必须报」；**变异**：把判定改成行级（同行有锚点就整行放行）⇒ 该用例变红 ⇒ token 级真的生效 |
| AC-G2 新 check 单独绿 | ✅ | `RDDF_ISOLATION_ONLY=check_no_unanchored_repo_paths` 在本仓 ⇒ exit 0（豁免恰好 2 条） |
| AC-H 豁免预算 = 2 | ✅ | 用例断言 `grep -h '# isolation-ok' skills/rdd-builder/scripts/*.sh` 恰为 2 条且理由 ≥10 字；实际：`phase2_execute.sh:100`（相对片段）、`phase0_approval.sh:327`（描述字段） |
| AC-I bypass 可计量 | ✅ | 用例「bypass 可计量」：打印 `skipped: check_no_unanchored_repo_paths` **且** `.rddf/state/.bypass-audit.jsonl` 新增一条 |
| AC-J 生产不退化 | ✅ | 用例在「`tasks.md` 不存在」场景断言生成内容一致；既有 `test_phase_auto_approve.bats` / `test_phase0_auto_approve.bats` / `test_rdd_builder_phases.bats` / `test_phase0_iteration_register.bats` / `test_lightweight_branch_and_archive.bats` 全绿（59 例） |
| AC-K 既有测试 | ✅ | 上列 5 个文件全绿；`test_phase_root_anchoring.bats` 11 例全绿 |
| AC-L 全量门 | ✅ | 见下 |
| AC-M 不改 CI | ✅ | `git diff <base> --stat` 不含 `.github/workflows/test.yml` |

### 变异测试

| # | 变异 | 结果 |
|---|---|---|
| M1 | 删掉 `phase2_execute.sh:100` 的 `# isolation-ok:` 标记 | ✅ 「豁免恰好 2 条」变红 |
| M2 | 把 token 级判定改成行级（同行有锚点即整行放行） | ✅ 「token 级」用例变红 |

### 顺带修掉的既有污染

`phase2` 的降级路径修好后，`test_lightweight_branch_and_archive.bats`（既有测试）**不再**
在真仓留下 `openspec/<name>` 分支 + prunable worktree 条目 —— 那是本项之前每次跑该测试
都会产生、但没人清理的残留。

### 本次不做 / 留给后续

1. **master 的隔离门已经红了**（9 处历史违规：`test_project_root_resolution.py:11`、
   `test_proposal_source_tracking.py:48/:57`、`test_guide_cross_container.bats:75`、
   `test_bypass_audit.py:31`、4 处 `assert ... or True`）⇒ CI 的「断言质量门」因同一批
   `or True` 也红 ⇒ **CI 在 master 上已经是红的**；而 `./test.sh` 不跑隔离门 ⇒ 本地全量门
   看不到 ⇒ 变红无人发现。本项只保证**新 check 单独绿**（AC-G2）；那 9 处另案（约 9 行，
   改动面在 `tests/unit`，与本项无关）。
2. **已知残留清单**（`skills/rdd-planner/scripts/planner_stage_{entry,exit}.sh:13/:21`、
   `skills/roadmap/scripts/roadmap_migrate.sh:21-25/:61`、`_lib/gate.py:168/:178/:197`）
   —— 本项刻意不修（面一放宽门就退化成豁免清单）；`_lib/gate.py` 那三处尤其值得单独处理：
   它**是质量门本身**，判错 = 验收结论不可信。
3. **运行期写盘检测**（CI 跑 integration 子集 + 前后 mtime 快照）—— 本次 marker 扫描实证它
   会被并联 session 的写误判；归属判定未解决前会制造假红。
4. **`generate_full_proposal.py` 的段映射失真** —— P0 生成 proposal 时把 `## 范围` 的
   Out of Scope **重复输出了一遍**（本次手工修正了生成的 proposal.md，未改生成器）。
