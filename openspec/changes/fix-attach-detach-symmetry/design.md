## Context

W0-2 audit 发现 `rddf_session_hook_attach` 在所有调用点被注释/移除，而 `rddf_session_hook_detach` 仍在 guide-ship Phase 3 archive 流程中通过 heartbeat hook 自动调用。attach/detach 调用不对称，导致 session 状态机在 archive 阶段可能发出 detach 信号但缺少对应的 attach 绑定。

## Goals/Non-Goals

**Goals:**
- 新建 `rddf_session_hook_attach` 函数（Python + bash 双入口）
- 在 guide-plan Phase 2 完成（propose 后）和 guide-ship Phase 1 plan 生成后插入 attach 调用点
- 恢复 attach/detach 对称性，使 session 生命周期完整

**Non-Goals:**
- 不改 `rddf_session_hook_detach` 或 heartbeat 机制
- 不涉及 session 数据迁移或状态修复（已有 session 不受影响）

## Decisions

- `hook_attach` 调用时机：guide-plan Phase 2 所有 propose 完成后、guide-ship Phase 1 的 `generate_implementation_plan` 完成后
- detach 保持现有的 heartbeat hook 机制不动，不做双端修改
- 新函数签名与 `hook_detach` 镜像对齐，接受 `session_id` 和 `change_name` 参数
- 错误处理：attach 失败打 warning 日志，不阻塞主流程

## Risks/Trade-offs

- 低风险：向后兼容，仅新增调用点
- 需要注意 hook 注入点不重复调用（同一个 session 内只 attach 一次）
- 新函数需要 Python 端和 bash 端各实现一次，保持行为一致