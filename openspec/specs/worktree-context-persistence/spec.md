# worktree-context-persistence Specification

## Purpose
TBD - created by archiving change worktree-context-persistence. Update Purpose after archive.
## Requirements
### Requirement: Worktree Context Rule

> **RETIRED (2026-11-20, retire-execute-skill)** —— 落点退役。原始 MUST 要求的 prose 落点 `skills/execute/SKILL.md` 已归档到 `docs/legacy/skills/execute/`（本仓 `skills/execute/` 已不存在），落点消失后本 Requirement 不可验证，故退役。
>
> 理由与残留：**archive 完成后回主仓**这一子句已由 `_lib/archive.sh` 承接（见下方 Requirement 2，仍有效）；但 **cd 纪律 prose（省略 cd / 显式 cd / DO-DON'T）属 agent 行为规范，当前无代码可承接** ⇒ 记 backlog（候选落点：AGENTS.md 的 cd 纪律段）。
>
> 注：ADR-0036 AMENDED（2026-11-17）的 NOTE 收窄的是「builder stage 不需要重复 prose」（handoff 由 code 交接），**并未裁决 cd 纪律 prose 的去留** —— 本次退役只声明「落点没了」，不声称「意图已由代码承接」。

#### Scenario: Agent 识别同 worktree 内省略 cd 规则

> 随本 Requirement 一并退役（2026-11-20）—— 断言锚点随落点归档而失效。
- **NOTE** (narrowed 2026-11-17, per ADR-0036 AMENDED): the Requirement used to demand the section in two skill files, each "in its Phase 1 / Phase 2 section". The v1-phase skill was removed in the v4 stage merge (ADR-0043 / ADR-0044 / ADR-0048), and the section text existed ONLY in the (now archived) execute skill — keeping both halves would have pinned a MUST that is false. The worktree context is handed over by CODE (`phase2_execute.sh` writes `worktree_path`/`branch` into the builder handoff), so the builder stage needs no duplicate prose. The paragraph qualifier was dropped too: that file had no Phase 1 / Phase 2 sections.

- **WHEN** Agent 在同一 worktree 内连续执行 bash 命令
- **THEN** 上一条命令的 cwd 已在该 worktree,Agent 不重复 `cd <wt-path>`
- **AND** （已退役）原锚点断言随落点归档失效

#### Scenario: Agent 跨 worktree 切换显式 cd

> 随本 Requirement 一并退役（2026-11-20）—— 断言锚点随落点归档而失效。

- **WHEN** Agent 需要从 worktree A 切到 worktree B
- **THEN** 显式 `cd <wt-B-path>`,不依赖框架记忆
- **AND** （已退役）原锚点断言随落点归档失效

#### Scenario: 协议被文档测试引用

> 随本 Requirement 一并退役（2026-11-20）—— 该 bats 测试的 execute 锚点用例已于本次一并删除。

- **WHEN** `tests/integration/test_worktree_context_persistence.bats` 跑 Worktree Context Rule 文档测试
- **THEN** （已退役）原锚点匹配断言随落点归档失效
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

> **RETIRED (2026-11-20, retire-execute-skill)** —— 整 Requirement 退役。理由：① 本 Requirement 引用的 `tests/unit/test_worktree_context_rule_docs.py` **早已不存在**（spec 早已不可验证）；② bats 侧实际只有 3 个 `@test`（本文件写的「4 个」已不准）；③ 归档 `skills/execute/SKILL.md` 时删除了其中的 execute 锚点用例，使本 Requirement 的 execute 半句**由本次改动变为假** —— 不一并退役就是「声称 spec 已对齐、实际只对齐一半」。
>
> 仍有效的部分：archive cwd 模拟与「1-change flow cd 计数」两个 Scenario 继续由 `tests/integration/test_worktree_context_persistence.bats` 覆盖（见 Requirement 2）。

系统 MUST 在 `tests/unit/test_worktree_context_rule_docs.py` 与 `tests/integration/test_worktree_context_persistence.bats` 中覆盖以下场景并全部 PASS:

#### Scenario: SKILL.md 文档锚点存在

> 随本 Requirement 一并退役（2026-11-20）。

- **WHEN** pytest 跑 `test_worktree_context_rule_docs.py`
- **THEN** （已退役）原文档锚点断言随落点归档失效
- **AND** 测试 PASS

#### Scenario: archive cwd 模拟与文档存在性

> 部分退役（2026-11-20）—— execute 锚点用例随归档删除；archive cwd 模拟部分仍有效。

- **WHEN** bats 跑 `test_worktree_context_persistence.bats`
- **THEN** 剩余 2 个测试 (archive cwd 模拟 / 1-change flow cd 计数 < threshold) 全部 PASS

#### Scenario: 1-change flow cd 计数 < 6

- **WHEN** 模拟单 change 5 阶段 bash 命令流
- **THEN** `cd` 命令出现次数 < 6
- **AND** 验证协议规则覆盖典型命令序列

