# fix-execute-change-name-persistence

## Why

- **ADR-0003 §Decision 4 (三阶段 arch→plan→ship)**: ship 端由 guide-ship 状态机编排，execute 技能在 worktree 中执行 plan。`CHANGE_NAME` 是贯穿 guide-ship/execute 全流程的核心上下文变量（SKILL.md 中依赖出现 29 次），但当前无可靠的自动推导机制。
- **2026-08-03 guide-ship 会话实测**: execute Step 1 执行 `test -f .rddf/plans/$CHANGE_NAME.md` 时因 `$CHANGE_NAME` 未在 shell 中持久化而报"计划文件不存在"（AI 平台把每个 bash 代码块拆到独立进程，shell 变量无法跨块传递），需人工 `export CHANGE_NAME=...` 修复。
- **既有先例**: `skills/execute/scripts/select_worktree.sh::auto_detect_worktree_context` 已实现从 git branch 自动推导 change 名称（`openspec/<name>` 前缀剥离），本提案将该模式推广到 execute Step 1 入口。

## What Changes

**In Scope**:

- **In Scope**:
- execute SKILL.md Step 1 增加 CHANGE_NAME 自动推导 fallback：`git branch --show-current | sed 's|^openspec/||'`，当环境变量未设置时自动注入
- `skills/execute/scripts/select_worktree.sh` 的 `auto_detect_worktree_context` 在设置 `CHANGE_NAME` 后将其 `export`（当前可能仅在函数内局部）
- 为 `execute/scripts/tasks_writeback.sh` 等依赖 `CHANGE_NAME` 的辅助脚本增加同样的入口守卫（缺失时自动推导）
- 添加 2 个 bats 用例：worktree 分支自动推导 / 轻量分支自动推导
- **Out Scope**:
- 不修改 guide-ship 的 CHANGE_NAME 设置逻辑（用户选择 change 的流程不变）
- 不引入状态文件持久化（CHANGE_NAME 是运行时上下文，非持久状态）
- 不修改 `.plan-handoff.json` schema
- 不处理非 openspec/* 分支的推导（无 change 关联时保持现状报错）

### 关键场景

- **GIVEN** 用户调用 `skill_use("execute")` 且当前分支为 `openspec/extract-rdd-env-check-from-guide-arch`
  **WHEN** Step 1 执行且 `CHANGE_NAME` 环境变量未设置
  **THEN** 自动推导 `CHANGE_NAME=extract-rdd-env-check-from-guide-arch`，`test -f .rddf/plans/$CHANGE_NAME.md` 通过

- **GIVEN** 用户在轻量模式分支 `openspec/fix-ns-pollution` 执行
  **WHEN** Step 1 执行
  **THEN** 自动推导 `CHANGE_NAME=fix-ns-pollution`，与 worktree 模式行为一致

- **GIVEN** 当前分支不在 `openspec/*` 且 `CHANGE_NAME` 未设置
  **WHEN** Step 1 执行
  **THEN** 输出明确错误提示"无法推导 change 名称，请设置 CHANGE_NAME"，退出非 0（不静默猜测）

- **GIVEN** 用户显式设置了 `CHANGE_NAME`
  **WHEN** Step 1 执行
  **THEN** 尊重显式值，不覆盖（显式优先于推导）

**Out of Scope**:

- design 阶段不生成 tasks.md / design.md / specs (留在 plan fill)
- 不修改 ADR-0003 (另起 ADR 记录本次职责再分配)


## Capabilities

- `design-proposal-creation`: design 审批批准即创建完整 openspec change
- `design-content-review`: 两层内容审查 (improvements 5 段 + openspec validate), warning / strict 双模式


## Impact

- **受影响文件**: `skills/guide-design/SKILL.md` + 4 个 scripts, `skills/guide-plan/scripts/plan_intake.sh`, `docs/adr/ADR-0025-*.md` (新增)
- **兼容性**: `SKIP_DESIGN_HANDOFF=yes` 存量路径行为不变
- **硬约束**: 批准动作幂等; env-var 传参 (Oracle C1)


## Acceptance

- `skill_use("execute")` 在 `openspec/*` 分支无 CHANGE_NAME 环境下可直接运行（Step 1 不报"计划文件不存在"）
- worktree 与轻量模式分支均可自动推导
- 非 openspec 分支推导失败时退出非 0 且含修复指引
- 显式 CHANGE_NAME 不被覆盖
- 2 个新 bats 用例 GREEN（worktree 推导 + 轻量推导）
- 既有 execute 相关测试（test_execute_skill.bats / test_select_worktree_extraction.bats）零回归

