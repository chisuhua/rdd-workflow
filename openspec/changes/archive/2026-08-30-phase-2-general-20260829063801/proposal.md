# phase-2-general-20260829063801

## Why

`ADR-0004` (loop engine core) + `ADR-0020` (incremental skeleton planning) 已支持单 change 编排,但 `_lib/loop/schedulers/` 缺少 wave概念,多 change 并行执行依赖手工 deps排序。**Why now**: 当前 archive feat-fix-audit-findings (涉及 18 个 audit-followup 提案) 手工编排,易出错。

## What Changes

**In Scope**:

- **Out Scope**: 跨 repo wave 编排 (留 Hub);wave UI 控制台

### 关键场景

- GIVEN 5 个 change 提交, deps关系形成2 个 wave
  WHEN guide-ship detect_execution_mode
  THEN 自动分配 2 个 worktree +1 个 wave调度,5 个 change 在 2 个 wave 内并行 ship
- GIVEN wave 2失败
  WHEN rollback
  THEN wave 1 commits保留,wave 2 worktree 清理

**Out of Scope**:

- (no items specified)

## Capabilities

- MUST: wave 计算 ≤100ms (5 change × 50 task 矩阵)

## Impact

- MUST NOT: 修改 `_lib/deps_analysis.py` 现有 schema (新增 fields)

## Acceptance

- 10 change × 3 wave 端到端测试 (生成 → execute → archive 全程)
- 失败回滚测试 (mock wave 2 失败)
- wave 计算性能测试 < 100ms

