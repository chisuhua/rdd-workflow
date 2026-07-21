# fix-scan-state-binding

**Priority**: P0
**Phase**: v2.1
**Status**: skeleton

## Why

## 架构依据
- 仪表盘设计规范 docs/superpowers/specs/2026-07-20-dashboard-design.md 明确列出的前置依赖
- scan-state.sh line 232 存在 syntax bug（变量展开缺闭合 brace），阻塞 session 绑定检测

## 范围
- **In Scope**:
  - skills/guide/scripts/scan-state.sh:232 — 修复 local owner 变量展开语法（缺 }）
  - 将 check_heartbeat_timeouts() 从 scan_session_binding 中解耦提取为独立函数
  - 验证 rddf dashboard session 区块正确显示绑定
- **Out Scope**:
  - 不修改 rddf_session.py（仅修复调用方）
  - 不修改 dashboard 渲染逻辑

## 验收标准
- rddf dashboard session 区块显示当前 session 绑定而非 "(no active session)"
- scan_session_binding 不因语法错误提前中断
- 所有现有测试通过

## What Changes

- TODO: define specific changes during fill phase

## Impact

- Affected specs: TBD
- Affected code: TBD
