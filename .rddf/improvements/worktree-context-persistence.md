# worktree-context-persistence

**优先级**: P1 | **来源**: opencode session retrospective (ses_fb4e3770dffeCYhR7xxAAQdI9l) | **阶段**: ship | **分类**: ship
**类型**: refactor
**主题**: 多方对称与回归

## 架构依据

实测 rdd-workflow 5 阶段流程 (`ses_fb4e3770dffeCYhR7xxAAQdI9l`,492 tool calls) 中,`cd` 命令出现 **354 次**——占总 bash 命令的 ~50%:

- 219x `cd /workspace/project/rdd-workflow` (主仓库)
- 39x `cd ~/.local/share/opencode` (事后分析)
- 96x `cd /workspace/project/rdd-workflow/.rddf/wt/phase-*-general-202608290638*` (9 个 worktree 各 6-31 次)

每个 worktree 平均被 cd 切换 16 次——`cd wt && pytest` → `cd master && cat X` → `cd wt && sed Y` → `cd master && commit` 的循环。Agent 每次进入 worktree 都重新 cd,因为 opencode 工具不维护"当前 worktree"指针。

**Why now**:rdd-workflow 流程典型场景是 N 个并行 change × K 个命令,重复 cd 的开销随 N 线性增长。本会话 9 个 change 已经浪费 ~30s 纯 cd 时间 + 354 × ~50 bytes = 17.7KB LLM command tokens。如果项目继续 dogfood 30+ changes,这些数字会 3-4 倍。

## 范围

- **In Scope**: 在 `guide-ship`/`execute` skill 文档中新增"worktree 上下文协议"段;Agent 自发遵守"省略 cd"规则;在 `archive.sh` 完成后自动 `cd` 回到主仓库
- **Out Scope**: 改 opencode/Claude Code 工具内部行为(由 vendor 决定);持久化 bash 状态(如环境变量)— 超出本提案范围

## 关键场景

- GIVEN Agent 想在 worktree wt-X 内运行 pytest
  WHEN 上下文已经在 wt-X (前一条命令已 cd)
  THEN 不需要重复 `cd wt-X`,可直接 `pytest`
- GIVEN Agent 想从 worktree wt-X 切回 master 看 proposal-approved.md
  WHEN 显示 `cd master` 显式切换
  THEN 工具框架维护 worktree 栈,Agent 用 `cd master` 显式标记切换
- GIVEN Agent 完成 archive
  WHEN `archive.sh` 退出
  THEN shell cwd 已自动回 master,后续 bash 调用无需再次 cd

## 技术约束

- MUST NOT: 修改 git worktree 自身机制(用现有 `git worktree add`/`remove`)
- MUST NOT: 改变 `guide-ship.md` 的用户可见流程(只在 Agent 内部行为层)
- MUST NOT: 引入新依赖(纯文档+skill 行为约束)

## 验收标准

- 354 个 cd 减少到 < 50 个(每个 worktree 最多 5-6 个 = 初始切换 + archive 退出 + 几个显式跨 wt 操作)
- 端到端复测 1 个 change 的 5 阶段流程: cd 命令数 < 20(对比当前 39+)
- 文档化的"worktree 上下文协议"被新会话采用
- 在 `guide-ship/SKILL.md` 与 `execute/SKILL.md` 的 Phase 1 / 2 增加"worktree-context rule"提示框

## Why

每次执行 5 阶段流程都重复同样 cd 模式(实测 354 次),不修就继续累积。P1 而非 P0 因为它不破坏流程(只增加 token 浪费),可与其他 P1 一起做。

## What Changes

- `skills/guide-ship/SKILL.md` 增加 1 段 "Worktree Context Rule"(10-15 行)
- `skills/execute/SKILL.md` 同步增加同段
- `skills/_lib/archive.sh` 末尾追加 `cd <main_root>` 显式回 master
- `tests/integration/test_worktree_context_persistence.bats` 验证 1-change 流程的 cd 计数

## Capabilities

- MUST: Agent 在同一 worktree 内连续命令省略 `cd`
- MUST: Agent 跨 worktree 切换时显式 `cd <wt-path>`
- SHOULD: `archive.sh` 完成后 Agent 立即回主仓库

## Impact

- MUST NOT: 修改 git worktree 自身(已在"技术约束"中重复)
- MUST: 文档化协议后,所有新会话和现有 30+ session 历史保持兼容

## Acceptance

- [ ] 354 个 cd 减少到 < 50 个(每个 worktree 最多 5-6 个 = 初始切换 + archive 退出 + 几个显式跨 wt 操作)
- [ ] 端到端复测 1 个 change 的 5 阶段流程: cd 命令数 < 20(对比当前 39+)
- [ ] 文档化的"worktree 上下文协议"被新会话采用
- [ ] 在 `guide-ship/SKILL.md` 与 `execute/SKILL.md` 的 Phase 1 / 2 增加"worktree-context rule"提示框
