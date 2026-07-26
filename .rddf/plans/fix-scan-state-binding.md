# fix-scan-state-binding — 实施计划

**Change**: fix-scan-state-binding | **类型**: bug-fix | **模式**: worktree
**Worktree**: .rddf/wt/fix-scan-state-binding | **Branch**: openspec/fix-scan-state-binding

---

## 1. 修复 scan-state.sh:232 语法错误

- 修改 `skills/guide/scripts/scan-state.sh` line 232
- 将 `--format '{{.Owner})'` 修正为 `--format '{{.Owner}}'`
- 完成后 commit

## 2. 提取 check_heartbeat_timeouts 为独立函数

- 从 `scan_session_binding` 中解耦心跳超时检测逻辑
- 创建独立函数 `check_heartbeat_timeouts()`
- `scan_session_binding` 改为调用独立函数
- 完成后 commit

## 3. 验证

- 运行 `bats tests/smoke.bats`
- 调用 `skill_use("guide")` 验证 session 绑定显示正常

---

## 验证
    
- 每个步骤完成后 commit
- 最终运行 `pytest` / `bats` 确保回归通过
