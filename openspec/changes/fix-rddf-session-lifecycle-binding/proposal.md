## Why

会话复盘 2026-07-31 发现 4 阶段工作流（guide → design → plan → ship）执行中缺少 session 生命周期管理：

- ADR-0017 要求每个 workflow stage 创建/绑定/关闭 rddf-session，但 `rddf_session_hook_entry` / `rddf_session_hook_close` 从未被触发
- 根因：`rddf_session_hooks.sh` 依赖 `resolve_rdd_skill_dir` 函数（来自 `skill_root.sh`），但当前会话环境中 `skill_root.sh` 未被 source 或不可用，导致 3 个 orphaned session 残留（`rds_0569`, `rds_1221`, `rds_a1b5`），本次工作流未被追踪，跨 session 恢复不可用

## What Changes

- `skills/guide-design/SKILL.md` Phase 1 & Phase 5 — 在 `rddf_session_hook_entry` / `rddf_session_hook_close` 调用前确保 source `skill_root.sh`（含 fallback 查找）
- `skills/guide-plan/SKILL.md` Phase 1 & Phase 4 — 同上
- `skills/guide-ship/SKILL.md` Phase 1 & Phase 5 — 同上
- 当 `skill_root.sh` 不存在或 `resolve_rdd_skill_dir` 失败时优雅降级：打印 warning 而非 crash，不阻塞工作流

## Capabilities

### New Capabilities
- `rddf-session-lifecycle-hooks`: 确保 3 个 guide skill 的入口/出口可靠触发 rddf-session hook，失败时优雅降级

### Modified Capabilities
<!-- 无 spec 级行为变更 -->

## Impact

**In Scope:**
- `skills/guide-design/SKILL.md` — Phase 1 入口 + Phase 5 出口 hook 前置 source 逻辑
- `skills/guide-plan/SKILL.md` — Phase 1 入口 + Phase 4 出口 hook 前置 source 逻辑
- `skills/guide-ship/SKILL.md` — Phase 1 入口 + Phase 5 出口 hook 前置 source 逻辑

**Out of Scope:**
- 不修改 `rddf_session_hooks.sh` 本身
- 不修改 `skill_root.sh` 本身
- 不修改 `guide` 推荐器（无状态只读）
- 不涉及 sessions.json schema 变更