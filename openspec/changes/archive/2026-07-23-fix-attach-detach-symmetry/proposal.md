## Why

基于 W0-2 audit，`attach_change`/`detach_change` 调用点存在不对称性：detach 有完善的 hook 机制，但 attach 缺少对应的 `rddf_session_hook_attach` 调用。这导致 session 生命周期管理不完整，attach 操作无法被 hook 系统感知和追踪。

## What Changes

- `rddf_session_hooks.sh` 新增 `rddf_session_hook_attach` 函数
- `guide-plan` Phase 2（propose 完成后）调用 attach hook
- `guide-ship` Phase 1（plan 生成后）调用 attach hook
- 不修改 detach 逻辑（heartbeat hook 保持不变）
- 4 个测试覆盖：attach 正常流程、idempotent 安全、detach 兼容、hook 集成

## Capabilities

### New Capabilities
- `session-attach-hook`: 提供 session attach 生命周期 hook，在 change 被 attach 到工作流时执行必要的状态记录和通知

### Modified Capabilities
<!-- 无 spec 级别行为变更 -->

## Impact

- **Affected files**: `skills/_lib/rddf_session_hooks.sh`（新增 hook 函数），`skills/guide-plan/guide-plan.md`（Phase 2 调用点），`skills/guide-ship/guide-ship.md`（Phase 1 调用点）
- **Effort**: 1 天
- **Priority**: P1
- **Phase**: v2.1
- **Category**: core