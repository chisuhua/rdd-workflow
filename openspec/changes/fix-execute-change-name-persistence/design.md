## Context

**背景**: `CHANGE_NAME` 是贯穿 guide-ship/execute 全流程的核心上下文变量（execute SKILL.md 中依赖出现 29 次），但当前无可靠的自动推导机制。2026-08-03 guide-ship 会话实测：execute Step 1 执行 `test -f .rddf/plans/$CHANGE_NAME.md` 时因 `$CHANGE_NAME` 未在 shell 中持久化而报"计划文件不存在"（AI 平台把每个 bash 代码块拆到独立进程，shell 变量无法跨块传递），需人工 `export CHANGE_NAME=...` 修复。

**当前状态**: `skills/execute/scripts/select_worktree.sh::auto_detect_worktree_context` 已实现从 git branch 自动推导 change 名称（`openspec/<name>` 前缀剥离），且在设置后执行 `export CHANGE_NAME`（L45、L127 已 export）。但 execute SKILL.md Step 1 入口与 `execute/scripts/tasks_writeback.sh` 等辅助脚本不执行此推导——入口处 `CHANGE_NAME` 为空时直接失败。

**约束**:
- MUST 推导逻辑与 `select_worktree.sh` 的 `auto_detect_worktree_context` 一致（单一来源，复用而非复制）
- MUST 显式 `CHANGE_NAME` 优先于自动推导（不破坏用户手动指定路径）
- MUST 推导失败时明确报错而非静默使用空值
- MUST NOT 在非 git 仓库或非 openspec 分支上猜测 change 名称
- SHOULD 辅助脚本（tasks_writeback.sh 等）复用同一推导函数，而非各自实现
- MUST NOT 修改 `.plan-handoff.json` schema；不引入状态文件持久化（CHANGE_NAME 是运行时上下文）

## Goals / Non-Goals

**Goals**:
- execute SKILL.md Step 1 增加 CHANGE_NAME 自动推导 fallback：`git branch --show-current | sed 's|^openspec/||'`，当环境变量未设置时自动注入
- 确保 `auto_detect_worktree_context` 设置的 `CHANGE_NAME` 被 `export`（当前已 export，需验证覆盖 worktree 与轻量两条路径）
- 为 `execute/scripts/tasks_writeback.sh` 等依赖 `CHANGE_NAME` 的辅助脚本增加同样的入口守卫（缺失时自动推导）
- 添加 2 个 bats 用例：worktree 分支自动推导 / 轻量分支自动推导
- 既有 execute 相关测试（test_execute_skill.bats / test_select_worktree_extraction.bats）零回归

**Non-Goals**:
- 不修改 guide-ship 的 CHANGE_NAME 设置逻辑（用户选择 change 的流程不变）
- 不引入状态文件持久化（CHANGE_NAME 是运行时上下文，非持久状态）
- 不修改 `.plan-handoff.json` schema
- 不处理非 openspec/* 分支的推导（无 change 关联时保持现状报错）
- 不修改 ADR-0003

## Decisions

### 决策 1: 入口推导以「显式优先、分支推导、失败报错」三级逻辑实现

execute SKILL.md Step 1 与各辅助脚本入口统一使用同一模式：先检查 `CHANGE_NAME` 环境变量是否已设置（非空则直接用）；未设置时执行 `git branch --show-current | sed 's|^openspec/||'` 推导；推导结果为空或分支不含 `openspec/` 前缀时报错退出非 0，提示"无法推导 change 名称，请设置 CHANGE_NAME"。显式值永远不被覆盖。

### 决策 2: 复用 `auto_detect_worktree_context` 而非新写推导逻辑

`select_worktree.sh::auto_detect_worktree_context` 已实现分支解析与 `export CHANGE_NAME`。execute Step 1 入口在轻量/无 worktree 场景下直接调用该函数（或提取共享的 `derive_change_name` 辅助函数到 `skills/execute/scripts/` 共享文件），避免两处独立实现产生漂移。tasks_writeback.sh 等脚本 source 同一共享函数。

### 决策 3: 用 bats 锁定两条推导路径与显式优先语义

新增 2 个 bats 用例：① worktree 分支 `openspec/<name>` 自动推导成功且 `test -f .rddf/plans/$CHANGE_NAME.md` 通过；② 轻量分支同样推导成功；另补显式 `CHANGE_NAME` 不被覆盖与非法分支报错用例（作为既有用例扩展）。测试在临时 git 仓库中构造分支名，不依赖真实 worktree。

## Risks

- **推导出错误 change 名称**: 分支名与 change 名不一致时推导错误 → 推导结果必须经 `test -f .rddf/plans/$CHANGE_NAME.md` 校验，失败即报错而非继续
- **与显式设置冲突**: 用户手动 export 被覆盖 → 显式优先逻辑 + 测试锁定
- **跨脚本行为漂移**: 各脚本各自实现推导 → 共享单一函数，bats 覆盖全部调用点
- **非 openspec 分支静默猜测**: 分支不在 `openspec/*` 时错误继续 → 报错退出非 0，含修复指引
- **导出泄漏到 shell 会话**: export 后影响后续命令 → 推导仅设置 CHANGE_NAME 本身，不改动其他变量

## Open Questions

- 无；推导优先级、报错语义、复用路径与测试范围均由 proposal 和 improvement source 明确约束。
