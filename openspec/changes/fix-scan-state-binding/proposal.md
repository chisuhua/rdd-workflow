# fix-scan-state-binding

## 动机

`scan-state.sh` line 232 存在 syntax bug（变量展开缺闭合 brace），阻塞 session 绑定检测，导致 rddf dashboard 显示 "(no active session)"。

## 提议

1. 修复 `scan-state.sh:232` 的 `local owner` 变量展开语法（缺 `}`）
2. 将 `check_heartbeat_timeouts()` 从 `scan_session_binding` 中解耦提取为独立函数
3. 验证 rddf dashboard session 区块正确显示绑定

### 架构依据

- 仪表盘设计规范 `docs/superpowers/specs/2026-07-20-dashboard-design.md §Prerequisite`

### 范围

- **In Scope**:
  - 修复 scan-state.sh:232 语法错误
  - 提取 check_heartbeat_timeouts 为独立函数
  - 验证 dashboard session 区块绑定
- **Out Scope**:
  - 不修改 rddf_session.py
  - 不修改 dashboard 渲染逻辑

### 验收标准

- rddf dashboard session 区块显示当前 session 绑定
- scan_session_binding 不因语法错误提前中断
- 所有现有测试通过