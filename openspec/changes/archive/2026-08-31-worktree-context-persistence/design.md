## Context

实测 rdd-workflow 5 阶段流程 (`ses_fb4e3770dffeCYhR7xxAAQdI9l`,492 tool calls) 中,`cd` 命令出现 **354 次**——占总 bash 命令的 ~50%:

- 219x `cd /workspace/project/rdd-workflow` (主仓库)
- 39x `cd ~/.local/share/opencode` (事后分析)
- 96x `cd /workspace/project/rdd-workflow/.rddf/wt/phase-*-general-202608290638*` (9 个 worktree 各 6-31 次)

每个 worktree 平均被 cd 切换 16 次——`cd wt && pytest` → `cd master && cat X` → `cd wt && sed Y` → `cd master && commit` 的循环。Agent 每次进入 worktree 都重新 cd,因为 opencode 工具不维护"当前 worktree"指针。

rdd-workflow 流程典型场景是 N 个并行 change × K 个命令,重复 cd 的开销随 N 线性增长。本会话 9 个 change 已经浪费 ~30s 纯 cd 时间 + 354 × ~50 bytes = 17.7KB LLM command tokens。

## Goals / Non-Goals

**Goals:**
- 修 rdd-workflow 自己 skill 文档,新增"worktree 上下文协议"段
- Agent 自发遵守"省略 cd"规则(同 worktree 连续命令)
- `archive.sh` 完成后自动 `cd` 回到主仓库
- 端到端复测 1 个 change 的 5 阶段流程: cd 命令数 < 20

**Non-Goals:**
- 改 opencode / Claude Code 工具内部行为(由 vendor 决定)
- 持久化 bash 状态(如环境变量) — 超出本提案范围
- 修改 git worktree 自身机制(用现有 `git worktree add` / `remove`)
- 改变 `guide-ship.md` 的用户可见流程(只在 Agent 内部行为层)

## Decisions

### 1. 协议只走 skill 文档,不改工具

在 `skills/guide-ship/SKILL.md` 与 `skills/execute/SKILL.md` 的 Phase 1 / 2 各加 1 段 "Worktree Context Rule" (~10-15 行),作为 Agent 内部行为约束。不改任何 vendor 工具。

**Alternatives considered:**
- 改 opencode SDK 增 `cwd` 持久化:vendor territory, scope 失控 → 拒绝
- 在 shell wrapper 层 `cwd-tracker.sh` 维护 cwd 状态:bash stateful 不能跨调用 → 拒绝
- skill 文档 + Agent 纪律:零外部依赖, 可立即采用 → 采用

### 2. archive.sh 末尾追加 `cd <main_root>`

`_lib/archive.sh` 的 `archive_change` 函数最后一步(exit 0 之前)显式 `cd "$main_root"`。这样 Agent archive 完一个 change 后,下一条 bash 调用就已在 master,无需自己再 cd。

**Alternatives considered:**
- 让 Agent 自己 cd:依赖 Agent 自觉, 总有忘记的 → 拒绝
- archive 时打 tag:与现有工作流无关 → 拒绝

### 3. 用 bats 测试 `tests/integration/test_worktree_context_persistence.bats`

跑 1-change 的 5 阶段 happy path,通过 `git worktree list` + awk + sort 解析实际产生的 bash 调用序列,断言 cd 命令数 < 50(总) / < 20(e2e)。

**Alternatives considered:**
- 在 Agent prompt 中加 cwd-aware 提示:行为约束不在 test 范畴 → 拒绝作为兜底
- 用 pytest 模拟:bats 已在 wt 测试中, 复用 .bats 文件结构 → 采用

## Risks / Trade-offs

- **Risk: skill 文档不被新会话采纳**:Agent 不主动 Read `SKILL.md` 的 Phase 段 → mitigation 把 rule 加到 frontmatter `description` 段,触发 skill 自动加载时显示
- **Risk: archive.sh 中 `cd` 在 subshell 中无效**:现有 archive_change() 已大量用 `cd` 在主进程 → mitigation 在 exit 前一步(非 subshell)显式 cd
- **Trade-off**:Agent 跨 worktree 切换时仍需显式 `cd <wt-path>`, 不能省 → acceptance 在协议文档中明示
