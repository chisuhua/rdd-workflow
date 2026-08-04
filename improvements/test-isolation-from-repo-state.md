# test-isolation-from-repo-state

**优先级**: P2 | **来源**: Session 复盘 2026-08-04 — test_select_worktree 测试改写 3 次
**阶段**: v2.1 | **分类**: core-test
**类型**: fix

## 架构依据
- 实测：`tests/integration/test_select_worktree_extraction.bats::auto_detect_runs_in_main_repo` 假设"主仓库无 worktree"，但 2026-08-04 会话执行时仓库存在 3 个活跃 worktree，测试断言连续失败、改写 3 次才通过
- 根因：测试依赖真实仓库状态（worktree 数量/分支），而仓库状态随工作流推进变化
- 正确做法：测试在临时 git 仓库内构造隔离场景，不依赖 $REPO_ROOT 的运行时状态

## 范围
- **In Scope**:
  - 审计 `tests/integration/` 与 `tests/_lib/` 中依赖真实仓库状态（worktree list、分支、openspec/changes 目录内容）的 bats 测试
  - 将环境依赖断言改写为临时仓库 + fixture 构造（参考 `test_execute_change_name_derive.bats` 的 `make_repo_with_branch` 模式）
  - 1 个结构性 bats 测试：锁定"主仓库场景测试不读取真实 worktree 状态"
- **Out Scope**:
  - 不改被测产品代码（仅测试基建）
  - 不处理依赖 openspec CLI 的集成测试（其 fixture 已隔离）

## 关键场景
- **GIVEN** 开发者 fork 仓库并运行 bats 测试
  **WHEN** 仓库存在 0 个或 3 个活跃 worktree
  **THEN** `test_select_worktree_extraction.bats` 均稳定通过

## 技术约束
- 临时仓库 fixture 必须清理（mktemp + trap/rm），不泄漏到 `.bats-tmp/`

## 验收标准
- 环境依赖测试全部改写为隔离场景
- 在 0 worktree 与多 worktree 状态下均 GREEN
- 无新增 fixture 泄漏
