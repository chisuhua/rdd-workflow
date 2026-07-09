## ADDED Requirements

### Requirement: rddf-session 持久化
系统 SHALL 在 `.rddf/state/sessions.json` 文件中持久化所有 rddf-session 生命周期，文件路径符合 AGENTS.md"关键约定"gitignored 状态文件规范。系统 MUST 在每次 rddf-session 状态变更时执行原子写（write-temp + rename）以防止并发损坏。

#### Scenario: 创建 rddf-session 后立即落盘
- **WHEN** `guide-arch` 在新的 OpenCode session 中启动并创建 `stage_arch` rddf-session
- **THEN** 系统 SHALL 在 `.rddf/state/sessions.json` 写入新 session 条目，包含 session_id/kind/owner_opencode_session_id/parent_session_id/goal/state/started_at/last_heartbeat
- **AND** 文件 SHALL 通过原子写创建（write to .tmp + rename）

#### Scenario: 跨 OpenCode session 读取 rddf-session
- **WHEN** 用户在 OpenCode session B 启动 `skill_use("rddf-session", "list")`
- **THEN** 系统 SHALL 从 `.rddf/state/sessions.json` 读取所有 sessions
- **AND** SHALL 显示 session_id/kind/owner/state/last_heartbeat/attached_changes

### Requirement: rddf-session kind 分类
系统 SHALL 仅在以下 3 个 kind 上创建 rddf-session：`stage_arch`、`stage_plan`、`stage_ship`。其他技能（包括 `feature`、`status`、`guide`、所有子技能）MUST NOT 创建 rddf-session。

#### Scenario: guide-arch 创建 stage_arch session
- **WHEN** 用户调用 `skill_use("guide-arch")` 且无 active stage_arch rddf-session
- **THEN** 系统 SHALL 创建 kind=stage_arch 的新 rddf-session，state=active

#### Scenario: 子技能不创建 rddf-session
- **WHEN** 用户调用 `skill_use("propose")`（被 guide-plan 调用的子技能）
- **THEN** 系统 MUST NOT 创建新的 rddf-session
- **AND** SHOULD 继承当前 active stage_plan rddf-session 的 session_id 作为 owner

#### Scenario: 只读视图不创建 rddf-session
- **WHEN** 用户调用 `skill_use("feature", "summary")` 或 `skill_use("status", "--iteration")`
- **THEN** 系统 MUST NOT 创建任何 rddf-session

### Requirement: rddf-session 状态机
系统 SHALL 实现以下状态转换：`active → completed | failed | orphaned`。COMPLETED 和 FAILED 是终态。ORPHANED 是终态（除非显式 RESUME）。

#### Scenario: arch-done 触发 completed
- **WHEN** `guide-arch` 通过 arch-done 门控（ADR ≥ 1 + roadmap.md 存在）
- **THEN** 当前 stage_arch rddf-session SHALL transition 到 state=completed
- **AND** SHALL 设置 ended_at 为当前时间
- **AND** SHALL 设置 end_reason="arch-done"

#### Scenario: 门控失败触发 failed
- **WHEN** `guide-plan` 门控 0（ready-for-ship ≥ 1）失败
- **THEN** 当前 stage_plan rddf-session SHALL transition 到 state=failed
- **AND** SHALL 设置 end_reason="plan-done-gate-rejected"

#### Scenario: 心跳超时触发 orphaned
- **WHEN** 任意 active rddf-session 的 last_heartbeat 距当前时间 > 30 分钟
- **THEN** 系统 SHALL 在下次 `skill_use("rddf-session", "list")` 调用时检测并标记 state=orphaned
- **AND** SHALL 设置 end_reason="heartbeat-timeout"

### Requirement: 心跳机制
系统 SHALL 在 rddf-session 创建后保持心跳活跃。心跳刷新阈值为 5 分钟，超时阈值为 30 分钟。

#### Scenario: guide-plan 阶段内调用刷新心跳
- **WHEN** `guide-plan` Phase 2（propose）或 Phase 2.5（fill）或 Phase 3（deps）任何阶段被执行
- **THEN** 当前 active stage_plan rddf-session 的 last_heartbeat SHALL 更新为当前时间
- **AND** 文件 SHALL 通过原子写持久化

#### Scenario: 5 分钟内无操作不报警
- **WHEN** rddf-session 最后心跳在 5 分钟内
- **THEN** 系统 SHALL NOT 标记为 orphaned

#### Scenario: 30 分钟无操作标记为 orphaned
- **WHEN** rddf-session 最后心跳距当前时间超过 30 分钟
- **THEN** 系统 SHALL 在 `skill_use("rddf-session", "list")` 调用时自动检测并标记 orphaned

### Requirement: opencode session 冲突软提示
系统 SHALL 在创建新 rddf-session 前检测 owner 冲突。如冲突，提供 4 选项软提示。

#### Scenario: 同一 opencode session 重复创建
- **WHEN** 用户在同一 OpenCode session 中重复调用 `skill_use("guide-plan")` 且已有 active stage_plan session
- **THEN** 系统 SHALL 复用现有 rddf-session，不创建新 session
- **AND** SHALL 刷新 last_heartbeat

#### Scenario: 不同 opencode session 创建冲突
- **WHEN** 用户在 OpenCode session B 启动 `skill_use("guide-plan")` 且存在 active stage_plan session by OpenCode session A
- **THEN** 系统 SHALL 显示 4 选项软提示：1) 放弃原 session 创建新；2) 转移所有权给当前 session；3) 强制接管（不转移 owner）；4) 仅查看
- **AND** MUST NOT 默认选择任一选项（必须用户显式选择）

#### Scenario: 用户选择"放弃原 session"
- **WHEN** 用户在冲突软提示中选择选项 1
- **THEN** 原 rddf-session SHALL 标记 state=abandoned
- **AND** SHALL 创建新 rddf-session，owner=当前 OpenCode session

#### Scenario: 用户选择"转移所有权"
- **WHEN** 用户在冲突软提示中选择选项 2
- **THEN** 原 rddf-session 的 owner_opencode_session_id SHALL 更新为当前 OpenCode session ID
- **AND** SHALL 刷新 last_heartbeat
- **AND** SHALL NOT 创建新 session

### Requirement: rddf-session 父子关系
系统 SHALL 通过 `parent_session_id` 字段建立父子关系。父子关系 SHALL 在以下时机建立：
- `stage_plan` session 创建时，parent = 最新 stage_arch session
- `stage_ship` session 创建时，parent = 最新 stage_plan session

#### Scenario: 父子关系建立
- **WHEN** `guide-plan` 在 arch-done 之后启动
- **THEN** 新创建的 stage_plan rddf-session 的 parent_session_id SHALL 指向最新 stage_arch session_id

#### Scenario: 孤儿 session（无父）允许存在
- **WHEN** stage_arch session 创建时无父
- **THEN** parent_session_id SHALL 为 null（允许顶层 session）

### Requirement: 关闭时序
系统 SHALL 在以下时机关闭 rddf-session：
- `arch-done` 门控通过 → stage_arch → completed
- `plan-done` 门控通过 → stage_plan → completed
- 所有 attached_changes 完成 archive → stage_ship → completed

#### Scenario: 阶段切换无条件关闭
- **WHEN** `guide-plan` 启动且存在 active stage_plan session（即使子技能有未完成工作）
- **THEN** 现有 stage_plan session SHALL 被强制关闭（state=completed 或 failed）
- **AND** 新 stage_plan session SHALL 创建

#### Scenario: archive 完成关闭 stage_ship
- **WHEN** 所有 attached_changes（stage_ship rddf-session 的）已 archive
- **THEN** stage_ship session SHALL transition 到 state=completed

### Requirement: 与 worktree 完全解耦
rddf-session MUST NOT 持有 worktree 路径信息。所有 worktree 由 `git worktree list` 管理，与 rddf-session 完全解耦。

#### Scenario: worktree 变更不影响 rddf-session
- **WHEN** 用户在 worktree 内执行操作
- **THEN** rddf-session 状态 MUST NOT 包含 worktree_path 字段
- **AND** worktree 列表 MUST 由 `git worktree list` 独立管理

### Requirement: rddf-session 用户入口
系统 SHALL 提供 `skill_use("rddf-session")` 入口，支持以下子命令：`list`、`show <id>`、`resume <id>`、`abandon <id>`。

#### Scenario: list 列出所有 sessions
- **WHEN** 用户调用 `skill_use("rddf-session", "list")`
- **THEN** 系统 SHALL 显示所有 sessions（按 started_at 降序）
- **AND** SHALL 显示字段：session_id/kind/owner/state/last_heartbeat/attached_changes

#### Scenario: show 显示单个 session 详情
- **WHEN** 用户调用 `skill_use("rddf-session", "show", "rds_xxx")`
- **THEN** 系统 SHALL 显示该 session 的完整 JSON

#### Scenario: resume 转移所有权并刷新心跳
- **WHEN** 用户调用 `skill_use("rddf-session", "resume", "rds_xxx")` 且当前 OpenCode session 与原 owner 不同
- **THEN** 系统 SHALL 转移 owner_opencode_session_id 为当前 OpenCode session
- **AND** SHALL 刷新 last_heartbeat
- **AND** SHALL transition state 从 orphaned → active

#### Scenario: abandon 标记为 abandoned
- **WHEN** 用户调用 `skill_use("rddf-session", "abandon", "rds_xxx")`
- **THEN** 系统 SHALL transition state → abandoned
- **AND** SHALL 设置 end_reason="user-abandoned"

### Requirement: 与现有 Session 抽象的兼容性
rddf-session 实现 MUST NOT 修改 `skills/_lib/session.py`、`session_base.py`、`session_manager.py` 的现有 API。rddf-session 作为用户层抽象，叠加在 v2.0 SessionCoordinator 之上。

#### Scenario: 向后兼容性
- **WHEN** rddf-session 实现完成
- **THEN** `SessionCoordinator`（v2.0）和 `SessionManager`（v2.1）API MUST 保持不变
- **AND** 现有调用者（loop_engine/agents 模块）MUST NOT 被破坏

### Requirement: 历史归档策略
系统 SHALL 在 sessions.json 包含超过 100 条历史 session 时提供归档命令 `skill_use("rddf-session", "archive-history", "--keep=N")`，将早于指定数量的 completed/failed/abandoned session 移动到 `.rddf/state/sessions.archive.json`。

#### Scenario: 历史归档减少主文件大小
- **WHEN** 用户调用 `skill_use("rddf-session", "archive-history", "--keep=20")`
- **THEN** 主 sessions.json SHALL 仅保留最近 20 条历史 + 所有 active/orphaned sessions
- **AND** 其余 completed/failed/abandoned sessions SHALL 移动到 sessions.archive.json