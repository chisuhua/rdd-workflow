# ADR-0017: rddf-session — 用户视角工作流会话

> **状态**: ✅ 已采纳（已实施）
> **日期**: 2026-07-09
> **决策者**: sisyphus
> **依据**: ADR-0003 (三阶段架构), ADR-0010 (多会话管理), ADR-0016 (arch discovery contract)
> **版本目标**: v2.0.2

## Context

spec-workflow v2.0 实现了三阶段状态机（`guide-arch` → `guide-plan` → `guide-ship`），但**没有跨 OpenCode 会话的 workflow 上下文连续性**：

- 在 OpenCode session A 中执行 `guide-plan` Phase 2 后中断
- 在 OpenCode session B 中只能看到 `iteration.json` 知道有 proposed changes
- 但**无法知道**之前创建了哪些 artifact、卡在哪一步、是否在并行 worktree 中有未完成工作

ADR-0010 设计了 `SessionCoordinator`/`SessionManager` Python 抽象，但：

1. 这些类从未被 `loop_engine.py` 或任何 skill 导入使用
2. `state_vector.py` 的 schema `additionalProperties: false` 阻止了 ADR-0010 v2.0 设计的 `session_info`/`sub_sessions` 字段写入

## Decision

引入 **`rddf-session`** —— 用户视角的工作流会话抽象，叠加在 v2.0 SessionCoordinator 之上：

1. **项目级 `.rddf/state/sessions.json`**（gitignored）持久化所有 rddf-session 生命周期
2. **`guide-arch`/`guide-plan`/`guide-ship`** 在入口自动创建/查找对应 kind 的 rddf-session
3. **5 分钟心跳刷新 + 30 分钟超时 → orphaned**
4. **跨 OpenCode session 冲突时 4 选项软提示**：放弃/转移/强制/查看
5. **`state_vector.py` schema 放宽**：允许 `session_management.active_sessions[]` 包含 `owner_opencode_session_id` 和 `rddf_session_id` 字段（向后兼容）

## Schema (v1)

rddf-session 必须匹配 `skills/_lib/schemas/sessions_schema.json` v1：

```json
{
  "version": 1,
  "sessions": [
    {
      "session_id": "rds_<12 hex>",
      "kind": "stage_arch | stage_plan | stage_ship",
      "owner_opencode_session_id": "ses_xxx | null",
      "parent_session_id": "rds_yyy | null",
      "goal": {"intent": "guide-arch", "subject": "...", "expected_outcome": "..."},
      "state": "active | completed | failed | orphaned | abandoned",
      "attached_changes": ["change-x"],
      "context_pointer": ".rddf/state/.arch-handoff.json",
      "started_at": "ISO 8601",
      "last_heartbeat": "ISO 8601",
      "ended_at": "ISO 8601 | null",
      "end_reason": "arch-done | heartbeat-timeout | ..."
    }
  ]
}
```

## State Machine

```
        ┌──────────┐
        │  active  │
        └────┬─────┘
             │
   ┌─────────┼──────────┐
   ↓         ↓          ↓
completed  failed    orphaned
   (arch-done / archive)   (gate拒绝)        (心跳>30min)
```

移除 ADR-0010 的 `paused` 状态（arch-done 后不允许"恢复"）。

## Implementation

- **`skills/_lib/rddf_session.py`**: `RddfSessionCoordinator` 封装 SessionCoordinator + 原子写 + 心跳 + 冲突检测（24 单元测试 + 5 集成测试）
- **`skills/_lib/schemas/sessions_schema.json`**: JSON Schema v1 校验
- **`skills/rddf-session.md`**: 用户入口（list/show/resume/abandon/archive-history 5 子命令）
- **修改 `state_vector.py` schema**: 添加 `owner_opencode_session_id` 和 `rddf_session_id` 可选字段到 `active_sessions[]` 项
- **修改 `guide-arch.md`/`guide-plan.md`/`guide-ship.md`**: 入口创建 + 阶段关闭 hooks

## Backward Compatibility

- 完全兼容。rddf-session 是叠加层，不修改 `SessionCoordinator`/`SessionManager` API
- 现有调用者（loop_engine/agents 模块）不被破坏
- `state_vector.py` schema 修改仅添加可选字段，不影响现有字段

## Consequences

### 正面
- **跨 OpenCode session 恢复**：用户在 session B 中可以列出 session A 创建的 rddf-session 并选择继续
- **冲突安全**：4 选项软提示避免静默合并
- **心跳机制**：30 分钟超时自动标记 orphaned，避免无限期悬挂
- **零新依赖**：仅使用 stdlib + 现有 state_vector 原子写模式
- **24 + 5 = 29 个测试覆盖**：create/find/list/update/attach/detach/heartbeat/conflict/transfer/abandon/archive/idempotency/lifecycle/cross-opencode/worktree-decoupling/orphaned-recovery

### 风险
- **schema 修改对 state_vector**：仅添加可选字段，单元测试已覆盖
- **sessions.json 累积过大**：提供 `archive-history` 命令自动迁移历史
- **心跳误判**：5 分钟刷新粒度合理，list/show/resume 自动刷新
- **POSIX-only 锁**：使用 `fcntl.flock`，Windows 需替换

## Migration Plan

### Deployment

1. P0 Schema：sessions_schema.json + state_vector.py schema 放宽（已完成）
2. P1 核心：rddf_session.py + 24 单元测试（已完成）
3. P2 Skill 集成：3 个 guide 技能 hooks + rddf-session.md（已完成）
4. P3 集成测试：5 integration tests（已完成）
5. P4 文档：ADR-0017 + ADR-0010 状态更新 + 用户指南（本次）

### Rollback

删除 `rddf_session.py`、`sessions_schema.json`、`rddf-session.md`，撤销 3 个 guide 技能入口修改。sessions.json 保留无影响（仅不被读取）。

## References

- ADR-0003 — 三阶段架构（arch → plan → ship）
- ADR-0010 — 多会话管理（SessionCoordinator/SessionManager）
- ADR-0016 — Arch discovery contract
- `docs/v2-workflow-overview.md` §4.5 rddf-session + 闭环 11
- `docs/v2-multi-session-guide.md` rddf-session 用户指南
- `openspec/changes/add-rddf-session/` — OpenSpec change artifacts