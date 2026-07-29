# Fix plan-done gate zero stale count — Gate 0 should read filesystem not iteration.json

**优先级**: P2
**阶段**: default
**分类**: core-impl

## 概要

修复 `plan_done_gate.sh` Gate 0 从 `iteration.json` 读取缓存计数导致 archive 后计数不准确的问题。

## 背景

- `plan_done_gate.sh` Gate 0 通过 `iteration.list_ready_for_ship()` 从 `.rddf/state/iteration.json` 读取 "ready-for-ship" 计数
- `iteration.json` 是派生视图（多 hook 写入），archive 后旧条目未被清理 → 累积 stale 数据
- 实际案例：Gate 0 报 `ready-for-ship: 5`，但实际活跃 change 仅 1 个（其余 4 个已归档）
- Gate 1（Active changes check）直接读文件系统 `ls openspec/changes/*/`，始终是权威数据源
- 根因：`iteration.json` 缺乏 archive 时清理旧条目的机制（独立 issue：`archive-iteration-sync` 已归档）

## 范围

### In Scope

- Gate 0 计数改为文件系统扫描（`ls -d openspec/changes/*/ | grep -v archive/ | wc -l`），与 Gate 1 同源
- 或：移除 Gate 0 独立计数，合并到 Gate 1（`active_changes >= 1` 等价于 "ready-for-ship >= 1"）
- 添加 bats 测试：归档后 Gate 0 计数正确减少
- 添加 bats 测试：0 活跃 change 时 Gate 0 拒绝

### Out Scope

- 不修改 `iteration.json` 的清理逻辑（独立 issue）
- 不修改 Gate 1 或 Gate 2 逻辑
- 不删除 `iteration.list_ready_for_ship()` 函数（其他 consumer 可能使用）

## 关键场景

- GIVEN 已归档 3 个 change，活跃 change 为 1，WHEN `run_plan_done_gate` 被调用，THEN Gate 0 输出 `ready-for-ship: 1`（非 5）
- GIVEN 所有 change 已归档，0 个活跃 change，WHEN `run_plan_done_gate` 被调用，THEN Gate 0 输出 `ready-for-ship: 0` → 门控失败（正确拒绝）
- GIVEN 有 3 个活跃 change，其中 1 个被另一 change 阻塞，WHEN Gate 0 从文件系统计数，THEN blocked change 仍计入（与当前行为一致，deps 分析结果在 plan-done 后处理）

## 验收标准

| # | 标准 | 验证方式 |
|---|------|----------|
| 1 | 归档所有 change 后，Gate 0 计数降为 0 | bats：fixture 先创建 3 个 change，全部归档，断言 Gate 0 输出 0 |
| 2 | 1 个活跃 change 时，Gate 0 计数为 1 | bats：fixture 含 1 个 change，断言输出 1 |
| 3 | Gate 1 行为不受影响 | 现有 bats 全部通过 |