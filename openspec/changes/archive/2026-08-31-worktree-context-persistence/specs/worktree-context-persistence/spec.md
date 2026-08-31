## ADDED Requirements

### Requirement: Worktree Context Rule

系统 MUST 在 `skills/guide-ship/SKILL.md` 与 `skills/execute/SKILL.md` 的 Phase 1 / Phase 2 段各包含一段 "Worktree Context Rule",规范 Agent 在 rdd-workflow 流程中的 `cd` 纪律。

#### Scenario: Agent 识别同 worktree 内省略 cd 规则

- **WHEN** Agent 在同一 worktree 内连续执行 bash 命令
- **THEN** 上一条命令的 cwd 已在该 worktree,Agent 不重复 `cd <wt-path>`
- **AND** `guide-ship/SKILL.md` 含锚点 `Worktree Context Rule`、`同一 worktree 内省略 cd`、`跨 worktree 切换显式 cd`

#### Scenario: Agent 跨 worktree 切换显式 cd

- **WHEN** Agent 需要从 worktree A 切到 worktree B
- **THEN** 显式 `cd <wt-B-path>`,不依赖框架记忆
- **AND** 两个 SKILL.md 均含 `跨 worktree 切换显式 cd` 锚点

#### Scenario: 协议被 brainstorm skill 引用

- **WHEN** test_cross_repo_schemas 跑 Worktree Context Rule 文档测试
- **THEN** 2 个 SKILL.md 锚点全部匹配
- **AND** 测试 PASS

### Requirement: archive.sh 自动 cd 回主仓库

系统 MUST 在 `_lib/archive.sh::archive_change` 函数成功 exit 前追加 `cd "$MAIN_REPO_ROOT" 2>/dev/null || true`,使 archive 完成后 shell cwd 自动回到主仓库。

#### Scenario: archive_change 成功后 cwd 回到主仓库

- **WHEN** archive_change 走完完整流程 (含 post_archive_cleanup)
- **THEN** 函数返回前执行 `cd "$MAIN_REPO_ROOT" 2>/dev/null || true`
- **AND** bash 语法检查 `bash -n _lib/archive.sh` PASS

#### Scenario: archive_change 退出码不变

- **WHEN** archive_change 主流程成功
- **THEN** 函数返回 0 (与改造前一致)
- **AND** cd-back 行不引入新错误退出码 (`|| true` 容错)

### Requirement: worktree context 回归测试

系统 MUST 在 `tests/unit/test_worktree_context_rule_docs.py` 与 `tests/integration/test_worktree_context_persistence.bats` 中覆盖以下场景并全部 PASS:

#### Scenario: SKILL.md 文档锚点存在

- **WHEN** pytest 跑 `test_worktree_context_rule_docs.py`
- **THEN** `guide-ship/SKILL.md` 与 `execute/SKILL.md` 全部含 3 个锚点
- **AND** 测试 PASS

#### Scenario: archive cwd 模拟与文档存在性

- **WHEN** bats 跑 `test_worktree_context_persistence.bats`
- **THEN** 4 个测试 (archive cwd 模拟 / guide-ship 锚点 / execute 锚点 / 1-change flow cd 计数 < threshold) 全部 PASS

#### Scenario: 1-change flow cd 计数 < 6

- **WHEN** 模拟单 change 5 阶段 bash 命令流
- **THEN** `cd` 命令出现次数 < 6
- **AND** 验证协议规则覆盖典型命令序列