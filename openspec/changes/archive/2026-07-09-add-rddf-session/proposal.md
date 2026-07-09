## Why

spec-workflow 当前的会话管理（ADR-0010）实现了 Loop 引擎的 `SessionCoordinator`/`SessionManager` Python 抽象，但**这些抽象从未与 OpenCode 会话 ID（`ses_...`）建立任何关联**。用户在不同 OpenCode session 之间切换时，工作流上下文完全丢失：

- 在 OpenCode session A 中执行 `guide-plan` Phase 2 创建了 3 个 change 后中断
- 进入 OpenCode session B，`iteration.json` 知道有 change 存在（status=proposed）
- 但**无法知道**之前创建了哪些 artifact、卡在哪一步、是否在并行 worktree 中有未完成工作

此外，`state_vector.py` 的 schema（`additionalProperties: false`）实际上阻止了 ADR-0010 v2.0 设计的 `session_info`/`sub_sessions` 字段写入，导致 `session_management` 字段永远为 None。

`rddf-session` 通过引入**项目级、gitignored 的 `.rddf/state/sessions.json` 持久化层**解决这个问题：每个 rddf-session 绑定到唯一的 OpenCode session，让用户能够跨 OpenCode session 恢复 workflow 上下文。

## What Changes

- **新建 `rddf_session.py`**：封装 rddf-session 生命周期（创建/心跳/状态转换/冲突检测/原子持久化），基于 `state_vector.py` 的 checksum+atomic write 模式
- **新建 `sessions_schema.json`**：sessions.json 的 JSON Schema 校验文件
- **修改 `state_vector.py`**：移除或扩展 `_SCHEMA` 中 `additionalProperties: false` 限制，允许 `session_management` 字段
- **新建 `skill_use("rddf-session")` 入口**：`list`/`show`/`resume`/`abandon` 子命令，可被任意 opencode session 调用
- **修改 `guide-arch`/`guide-plan`/`guide-ship`**：3 个状态机技能入口添加 rddf-session 创建逻辑（kind 分别为 `stage_arch`/`stage_plan`/`stage_ship`），`arch-done`/`plan-done`/`archive` 完成时关闭对应 rddf-session
- **新建 `tests/unit/test_rddf_session.py`**：覆盖 12+ 用例（创建/重检测/父子/心跳/超时/4 种冲突场景/关闭时序/幂等性）
- **新建 `tests/integration/test_rddf_session_lifecycle.py`**：覆盖完整 lifecycle 与 worktree 解耦
- **新建 `ADR-0017-rddf-session.md`**：正式记录设计
- **更新 ADR-0010**：标记为已实施
- **更新 `docs/v2-workflow-overview.md`**：增加 rddf-session 章节（4.5 / 闭环 11）
- **更新 `docs/v2-multi-session-guide.md`**：补充 rddf-session 用户指南
- **更新 `AGENTS.md` 关键约定**：状态文件表加 `sessions.json` 行
- **更新 `package.json`**：无新增依赖（仅使用 stdlib + 现有 `state_vector`/`event_log`）

## Capabilities

### New Capabilities
- `rddf-session`: 用户视角的 workflow 工作流会话抽象，提供跨 OpenCode session 的上下文恢复能力

### Modified Capabilities
- `multi-session-management`: 现有的 SessionCoordinator/SessionManager 实现保持不变（向后兼容），但 rddf-session 作为用户层抽象叠加其上
- `state-management`: state_vector.py 的 schema 扩展以允许 session_management 字段持久化

## Impact

**Affected code:**
- `skills/_lib/state_vector.py`（schema 修改，向后兼容）
- `skills/_lib/session.py`（保留为 v2.0 lightweight 基线，不修改）
- `skills/_lib/session_base.py`（保留，不修改）
- `skills/_lib/session_manager.py`（保留为 v2.1 parallel 基线，不修改）
- 新增 `skills/_lib/rddf_session.py`
- 新增 `skills/_lib/schemas/sessions_schema.json`

**Affected skills:**
- `skills/guide-arch.md`（入口添加 rddf-session 创建）
- `skills/guide-plan.md`（入口添加 rddf-session 创建）
- `skills/guide-ship.md`（入口添加 rddf-session 创建 + 阶段关闭）
- 新增 `skills/rddf-session.md`（用户入口）

**Affected documentation:**
- `docs/adr/ADR-0010-multi-session-management.md`（状态更新）
- 新增 `docs/adr/ADR-0017-rddf-session.md`
- `docs/v2-workflow-overview.md`（增加章节）
- `docs/v2-multi-session-guide.md`（增加章节）
- `AGENTS.md`（状态文件表）

**Backward compatibility:** 完全兼容。rddf-session 是叠加层，不修改现有 SessionCoordinator/SessionManager API。