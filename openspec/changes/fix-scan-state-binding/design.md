# fix-scan-state-binding — 设计

## 问题

`scan-state.sh` 中 `scan_session_binding()` 函数有两处问题:

1. **Line 232 syntax bug**: `local owner=$(rddf session ...  --format '{{.Owner})'` — 缺闭合 `}`，导致 bash 语法错误，函数提前中断
2. **耦合**: `check_heartbeat_timeouts()` 逻辑嵌入在 `scan_session_binding` 中，无法独立复用

## 方案

- 修复 line 232: 补全 `--format '{{.Owner}}'`
- 提取 `check_heartbeat_timeouts()` 为独立函数，保持 `scan_session_binding` 的调用不变

## 影响

仅在 `scan-state.sh` 内修改，不影响其他文件。修复后 dashboard 的 session 绑定检测恢复正常。