## Context

### Background

rdd-workflow v2.0 实现了三阶段架构（arch → plan → ship，ADR-0003），每个阶段有 `guide-*` 状态机技能驱动。state machine 在每个 skill 内部维护，但**没有跨 OpenCode session 的工作流连续性**。

ADR-0010（多会话管理，2026-06-22 已采纳）设计了 `SessionCoordinator`（v2.0 轻量级）和 `SessionManager`（v2.1 完整并行）Python 抽象，但：
1. 这两个类**从未被 `loop_engine.py` 或任何 skill 导入使用**（grep 确认：仅在自身文件 + session_base.py 中引用）
2. `state_vector.py` 的 schema 在根层声明 `additionalProperties: false`，导致 ADR-0010 v2.0 设计的 `session_info`/`sub_sessions` 字段无法写入

用户最近通过 Metis review 发现：在不同 OpenCode session 之间切换时，workflow 上下文完全丢失。

### Current State

- **状态文件分散**：`iteration.json`（change 列表）、`.arch-handoff.json`、`.plan-handoff.json`（阶段完成信号）、`roadmap-state.json`、`deps-analysis.json` — 每个文件有独立 schema，但**没有任何文件包含 session ID**
- **跨 session 无记忆**：用户在 session A 执行 `guide-plan` Phase 2 后中断，在 session B 中只能看到 `iteration.json` 知道有 proposed changes，但**不知道是谁创建的、卡在哪一步**
- **子技能无 session 概念**：`propose.md`/`execute.md`/`deps.md` 等子技能不记录调用上下文

### Constraints

- **向后兼容**：现有 `SessionCoordinator`/`SessionManager` 代码保持不变
- **轻量级**：rddf-session 不引入新的 Python 包依赖，仅使用 stdlib + 现有 `state_vector.py` 的原子写模式
- **项目级作用域**：每个项目的 `.rddf/state/sessions.json` 独立（不跨项目共享）
- **gitignored**：sessions.json 加入 `.gitignore` 的 `.rddf/state/` 模式

### Stakeholders

- 主用户（产品经理/架构师/开发者）：跨 OpenCode session 恢复 workflow
- 维护者：需要清晰的 schema 和测试覆盖

## Goals / Non-Goals

**Goals:**
1. 实现项目级 `.rddf/state/sessions.json` 持久化层
2. 让 `guide-arch`/`guide-plan`/`guide-ship` 在入口自动管理 rddf-session 生命周期
3. 检测跨 OpenCode session 冲突并提供软提示（4 选项）
4. 复用 `state_vector.py` 的原子写 + checksum 模式保证并发安全
5. 修复 `state_vector.py` schema 阻止 session_management 字段写入的问题（向后兼容）
6. 提供 `skill_use("rddf-session")` 用户入口（list/show/resume/abandon/archive-history）
7. 12+ 单元测试 + 集成测试覆盖完整 lifecycle

**Non-Goals:**
1. **不实现真正的并行执行**：rddf-session 不替代 ADR-0010 的 v2.1 `SessionManager` 并行能力
2. **不修改现有 SessionCoordinator/SessionManager API**：保持向后兼容
3. **不实现进程间通信**：rddf-session 仅是持久化抽象，不替代 `session_ipc.py`（如未来需要）
4. **不跨项目共享**：每个项目独立的 `sessions.json`
5. **不实现自动化的 worktree-snapshot 关联**：worktree 由 git 独立管理

## Decisions

### Decision 1: rddf-session 作为用户层抽象，叠加在 v2.0 SessionCoordinator 之上

**Rationale:**
- ADR-0010 的 `SessionCoordinator` 已经是定义良好的状态机抽象，复用其 `Session` dataclass、状态转换规则
- rddf-session 增加**用户视角的元数据**（owner_opencode_session_id、parent_session_id、attached_changes、context_pointer），并强制**持久化到文件系统**
- 不修改 SessionCoordinator 源码，向后兼容；rddf_session.py 作为新的封装层

**Alternatives considered:**
- (A) 完全弃用 SessionCoordinator 重新设计 — 拒绝：丢失 ADR-0010 设计资产
- (B) 修改 SessionCoordinator 直接增加持久化 — 拒绝：污染现有 API

### Decision 2: 持久化到独立 sessions.json，不修改 state_vector.py 主体

**Rationale:**
- `state_vector.py` 是 Loop 引擎核心数据结构，频繁读写
- rddf-session 是用户视角的低频元数据，独立文件避免相互影响
- `state_vector.py` 的 schema 修改**仅放宽** root 层的 `additionalProperties: false`，允许新增字段而不破坏现有 schema（向后兼容）

**Alternatives considered:**
- (A) 在 state_vector 内嵌 rddf-session — 拒绝：导致 state_vector 频繁膨胀
- (B) 完全独立的数据库（如 SQLite）— 拒绝：超出当前规模

### Decision 3: 心跳机制基于"主动刷新"，而非定时器

**Rationale:**
- 每个 `guide-*` skill 的内部 phase 调用都刷新心跳（Phase 1/2/2.5/3 等）
- 不引入后台线程或 cron，避免增加系统复杂度
- 30 分钟超时通过 `skill_use("rddf-session", "list")` 调用时的"惰性检测"完成

**Alternatives considered:**
- (A) 后台线程定时写心跳 — 拒绝：增加部署复杂度
- (B) 在每个 skill_use 入口检查超时 — 已采用（list/show/resume 时检测）

### Decision 4: kind 字段使用长名 stage_arch/stage_plan/stage_ship

**Rationale:**
- 明确表达"这是阶段 session"，未来可扩展 `stage_iteration`/`stage_task` 等其他类型
- 短名 arch/plan/ship 易与文件名、技能名混淆

**Alternatives considered:**
- (A) 短名 arch/plan/ship — 拒绝：易混淆
- (B) 枚举 stage/iteration/task — 拒绝：抽象过度

### Decision 5: 冲突处理采用 4 选项软提示

**Rationale:**
- 与用户已经确定的"软提示"原则一致
- 给用户完全的决策权（放弃/转移/强制/查看）
- 避免自动接管可能导致的静默合并（多人共享 repo 场景危险）

**Alternatives considered:**
- (A) 硬阻断 — 拒绝：限制灵活性
- (B) 自动接管 — 拒绝：风险高
- (C) 软提示（已选）— 平衡灵活与安全

## Risks / Trade-offs

1. **[并发写 sessions.json] 多 skill 同时写** → 复用 state_vector.py 的 `write-temp + rename + checksum` 原子写模式，O_EXCL 锁
2. **[sessions.json 累积过大] 长期使用后文件膨胀** → 提供 `archive-history` 命令，自动迁移历史到 `sessions.archive.json`
3. **[心跳超时误判] 用户思考时间长但不超过 30 分钟** → 5 分钟刷新粒度合理；用户主动调用 list/show 时自动刷新
4. **[owner 转移的安全] 误转移可能丢失原 session 上下文** → 软提示需要显式选择，且保留 end_reason 审计字段
5. **[schema 修改对现有代码的影响] 放宽 additionalProperties 可能引入未来 bug** → 单元测试覆盖 schema 校验；同时通过 `additionalProperties: false` 限定 session_management 内部结构
6. **[不同步 iteration.json 的反向索引] 性能与一致性权衡** → 通过扫描 sessions.json 反查（≤3 active session，开销可忽略）

## Migration Plan

### Deployment Steps

1. **P0 Schema**（~1h）：
   - 修改 `state_vector.py` schema 允许 session_management
   - 创建 `sessions_schema.json`
2. **P1 核心实现**（~4h）：
   - 创建 `rddf_session.py`（封装 SessionCoordinator + 原子写 + 心跳 + 冲突检测）
   - 创建单元测试 `tests/unit/test_rddf_session.py`（12+ 用例）
3. **P2 Skill 集成**（~4h）：
   - 修改 `skills/guide-arch.md`/`guide-plan.md`/`guide-ship.md` 入口
   - 创建 `skills/rddf-session.md` 用户入口
4. **P3 集成测试**（~4h）：
   - 创建 `tests/integration/test_rddf_session_lifecycle.py`
   - 验证完整 lifecycle + worktree 解耦
5. **P4 文档**（~2h）：
   - 新建 `ADR-0017-rddf-session.md`
   - 更新 `ADR-0010`、`v2-workflow-overview.md`、`v2-multi-session-guide.md`、`AGENTS.md`

### Rollback Strategy

- rddf-session 是叠加层，**完全独立**于现有功能
- 回滚仅需删除：
  - `skills/_lib/rddf_session.py`
  - `skills/_lib/schemas/sessions_schema.json`
  - `skills/rddf-session.md`
  - 撤销 `skills/guide-arch.md`/`guide-plan.md`/`guide-ship.md` 入口修改
- `state_vector.py` schema 修改**可逆**（恢复 `additionalProperties: false`）
- `.rddf/state/sessions.json` 文件保留无影响（只是不读取）

## Open Questions

1. **attached_changes 在 plan → ship 阶段的传递**：stage_plan session 的 attached_changes 是否在 stage_ship 创建时复制？建议：保持独立（各自管理），避免跨阶段耦合。
2. **心跳刷新粒度**：是否需要在 deps 阶段（自动执行，无用户交互）也刷新心跳？建议：是（避免长 deps 分析被误判 orphaned）。
3. **跨项目的 rddf-session 视图**：用户同时管理多个项目时，是否需要 CLI 命令 `rddf-session list --all-projects`？v1.0 不实现，留作 v1.1。