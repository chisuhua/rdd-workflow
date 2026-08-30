# phase-1-general-20260829063800

## Why

当前 rddf-session (`ADR-0017`) 仅支持单工作流的 rddf-session 生命周期,缺少多会话并行、session-tree 继承、跨 opencode-session 恢复的完整契约。`ADR-0010` 定义的多会话管理虽已建模,但代码实现仅在 `_lib/session_manager.py` 局部实现,缺少对外 API 和 worktree 协作场景。**Why now**: 用户正在跨多 worktree 并行 archive 多个 change(feat-fix-audit-findings 涉及 phase-1/2/3/4),session 串行化导致 phase-boundary 卡顿。

## What Changes

**In Scope**:

- **Out Scope**: 多用户协作 (继续走 Hub-Spoke `ADR-0030`);session 加密存储

### 关键场景

- GIVEN 用户在 master仓库并行 ship 3 个 change WHEN guide-ship 入口创建 rddf-session
  THEN 3 个 session 并行存在,parent=当前 opencode session,各自 attached_changes 不重叠
- GIVEN 进程崩溃后重连  WHEN rddf-session resume 调用
  THEN 从 .rddf/state/sessions.json 加载全部未结束 session,提示用户选择 resume哪个

**Out of Scope**:

- (no items specified)

## Capabilities

- MUST: sessions.json 写操作 atomic (基于 `_lib/core/lock.py` 现有 LOCK_EX模式)
- SHOULD: 提供 `rddf session list-parallel` CLI 子命令

## Impact

- MUST NOT: 修改 v1 schema 现有字段 (v2 bump,新增字段)

## Acceptance

- 3 路并行 rddf-session 实测通过,bash test 覆盖
- crash → resume 路径测试通过 (用 SIGKILL 模拟)
- sessions.json v2 schema 测试覆盖 (新增字段解析 + 旧 v1 兼容读)

