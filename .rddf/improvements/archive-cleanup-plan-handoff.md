# archive-cleanup-plan-handoff

**优先级**: P1 | **来源**: PTX-EMU add-cudart-unit-tests archive 复盘 2026-07-24
**阶段**: v2.1 | **分类**: core
**类型**: bugfix

## 架构依据
- 复盘发现：`add-cudart-unit-tests` 归档后 `.rddf/state/.plan-handoff.json` 仍然指向：
  ```json
  {"current_change": "add-cudart-unit-tests", "ship_started_at": null, "active_changes": 1}
  ```
- 没有任何步骤清理或重置这个 handoff 文件，导致 handoff 状态与文件系统实际状态不一致
- `plan-handoff.json` 是 guide-plan → guide-ship 的交接文件，archive 完成后应标记已完成或归档
- 此问题与 `archive-iteration-sync`（iteration.json 不更新）同源但不同文件

## 范围
- **In Scope**:
  - ship_archive.sh::archive_change() 末尾增加 handoff 清理步骤
  - handoff 清理格式：追加 `archived_at` 时间戳，记录已归档的 change 名称
  - 如果所有 changes 已归档，将 `active_changes` 置 0
  - 如果还有未归档的 changes，只更新归档 change 的记录，保留 `active_changes` 计数
  - 幂等保证：重复归档同一 change 不报错
- **Out Scope**:
  - 不修改 handoff 文件的 JSON schema（仅追加字段）
  - 不修改 guide-plan 阶段的 handoff 写入逻辑
  - 不涉及 sessions.json 的状态更新

## 关键场景
- GIVEN 单个 change 归档, WHEN archive 完成, THEN handoff 记录该 change 已归档
- GIVEN 多个 changes 中归档一个, WHEN archive 完成, THEN handoff 保留剩余 changes
- GIVEN 所有 changes 归档完成, WHEN archive 完成, THEN handoff.active_changes = 0
- GIVEN 重复 archive 同一 change, WHEN archive 完成, THEN 幂等不报错

## 技术约束
- MUST ship_archive.sh 脚本末尾追加（不修改已有逻辑,追加新步骤）
- MUST 保持 .plan-handoff.json 向后兼容（老版本没有 archived_at 字段也能正常读取）
- MUST 写入前读取 handoff 当前内容，写入后验证

## 验收标准
- archive 完成后 .plan-handoff.json 包含 `archived_at` 时间戳
- 已归档的 change 名称在 handoff 中可追溯
- active_changes 计数与实际一致
- 3 个 bats 测试：单 change 归档、多 change 部分归档、全部归档