# add-rddf-session-workflow-group

**优先级**: P2 | **来源**: 2026-08-02 ship 复盘
**阶段**: v2.1 | **分类**: workflow
**类型**: feature

## 架构依据

本会话一次 ship 流程处理 2 个 changes (`move-proposal-creation-to-design` + `refine-plan-openspec-integration`),但系统无法关联"这是同一次会话的连续两个工作":
- 第一次 `guide-ship` 处理 change A 走完 plan → execute → review → archive → ship-done
- 用户从 ship-done 菜单选择 "1. 继续处理",触发第二次 `guide-ship`
- 系统不知道这两次 ship 是同一逻辑工作流 (例如 "今日双 change 批次"),还是"用户关掉后又回来"

rddf-session 当前只有 parent_id (stage_plan → stage_ship) 这种**单步骤**链接,无法表达"多次连续 ship 调用属于同一批次"。

## 范围

- **In Scope**:
  - `sessions_schema.json` v1 → v2 (与 sub-phase-heartbeat 合并 bump): 新增 `workflow_group: str | null` (UUID v4 字符串)
  - 新 env var `RDDF_WORKFLOW_GROUP`: 跨多次 `guide-ship` 调用保持同一值;未设置则首次 entry 自动生成并 export
  - `rddf_session_hook_entry`: 创建 session 时写入 `workflow_group`
  - `rddf-session list`: 输出新增 `workflow_group` 列
  - `rddf-session status`: 按 `workflow_group` 聚合显示 (e.g., "📦 Workflow group abc123: 2 completed sessions (stage_plan + stage_ship)")
- **Out Scope**:
  - 不强制用户手动管理 `RDDF_WORKFLOW_GROUP`
  - 不修改现有 schema v1 必填字段

## 关键场景

- GIVEN 用户运行 `RDDF_WORKFLOW_GROUP=batch-2026-08-02 guide-ship`,WHEN 调用 2 次 `guide-ship`,THEN 2 个 stage_ship sessions 共享同一 `workflow_group="batch-2026-08-02"`
- GIVEN `RDDF_WORKFLOW_GROUP` 未设置,WHEN 第一次 entry 被调用,THEN 生成 UUID v4 并 export 到 env (后续 hooks 自动继承)
- GIVEN `rddf-session status`,WHEN 调用,THEN 显示 "📦 Workflow group [hash]: 2 sessions (plan + ship), both completed"

## 技术约束

- workflow_group 必须是 UUID v4 或用户指定的语义化字符串 (e.g., "batch-2026-08-02");长度 ≤64 字符
- 不强制 RDDF_WORKFLOW_GROUP 必填 (未设置时本地生成)
- 与 sub-phase-heartbeat 的 schema v2 bump 合并,避免连续两次 schema bump

## 验收标准

- [ ] schema v2 支持 `workflow_group: str | null`
- [ ] `RDDF_WORKFLOW_GROUP=batch-2026-08-02` 时,2 次 entry 产生同一 workflow_group
- [ ] 未设置时自动生成 UUID v4 并 export
- [ ] `rddf-session status` 按 workflow_group 聚合
- [ ] 单元测试 + bats 集成测试通过