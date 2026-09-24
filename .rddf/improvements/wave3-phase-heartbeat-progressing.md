---
优先级: P2
来源: 2026-09-24 complete-guide-orchestrator-flow Step A.5 Oracle 审查 — AC-G3 detail 字段 "X 完成 N/M" 在生产场景下 N/M 恒为 0/1（per-session phase_started/completed 计数），用户看不到真任务进度；需 `phase_heartbeat` 事件携带 `progress_percent` / `tasks_total` / `tasks_completed` 等字段实现真任务级别进度。
阶段: v4.3 (Wave 3)
分类: feature
类型: feature
主题: events 类型接入
依赖: feat-guide-orchestrator-session-event-bus (shipped), complete-guide-orchestrator-flow (shipped 2026-09-24)
roadmap_ref:
  project_id: 完整多会话支持
  phase: phase-3
revision_count: 0
feedback_status: none
---

**优先级**: P2 | **来源**: 2026-09-24 Oracle 审查
**阶段**: v4.3 (Wave 3) | **分类**: feature | **类型**: feature | **主题**: events 类型接入
**依赖**: feat-guide-orchestrator-session-event-bus (shipped), complete-guide-orchestrator-flow (shipped 2026-09-24)

> **本文件为 5 段式 improvements 提案**。
> **范围**: 接入现有 `phase_heartbeat` event_type + 增加 task-level 字段 + 修复 AC-G3 语义贫弱。

## Why

`complete-guide-orchestrator-flow` Wave 2 W2.2 (Step A.5) 实现 `workflow_synthesizer` 消费 events.jsonl。`_outputs.child_progress` 的 `detail` 字段格式为 `"X 完成 {completed}/{started}"`，per AC-G3。

实测显示：per-session 的 `phase_started` + `phase_completed` 各只发 1 次（hook entry + hook close），所以 progress 字段恒为 `0/1`（进行中）或 `1/1`（已完成）。**完成 0/1 的描述对用户毫无信息量** — 用户想看的是 task-level 进度（"rdd-builder 完成 3/5 tasks: write_test, implement, refactor"），不是 session-level phase 计数。

事件总线 schema (`events.jsonl`) 当前支持的 7 类 event_type（per ADR-0055 §polling contract）：
- `phase_started` / `phase_completed` — session 生命周期
- `phase_heartbeat` — **已定义但 0 接入**（per W2.3 Q1）
- `guide_intent_detected` / `guide_routed` / `user_message` — 已定义未接入（per Wave 3 P1-1/P1-2）
- (隐式) 子 agent 层 — 0 实现

**P2-2 接 phase_heartbeat 入生产路径** + 扩展 schema 携带 task 进度字段，可让 `_outputs.child_progress.detail` 升级为 `"X 完成 3/5 (last: refactor)"`。

## What Changes

### 1. 接入 phase_heartbeat 写端

`rddf_session_hook_heartbeat` (skills/rddf-session/scripts/rddf_session_hooks.sh:521) 当前只更新 `last_heartbeat` 字段（per herodic session）。需追加：
- 调用方传入 `RDDF_TASKS_TOTAL=N` + `RDDF_TASKS_COMPLETED=M` env var
- heartbeat 写入 events.jsonl `phase_heartbeat` event，context 含 `tasks_total` / `tasks_completed`

### 2. events.jsonl schema 扩展

当前 schema (`_lib/schemas/...` 若存在) 仅列出 event_type 白名单。需扩展 schema 允许：
- `context.tasks_total: int` (可选)
- `context.tasks_completed: int` (可选)

**MN1**: 不改变 ADR-0055 schema 的 7 类 event_type 白名单（向后兼容）；扩展仅在 `context` 子键内增加 optional 字段。

### 3. workflow_synthesizer 渲染升级

`_lib/workflow_synthesizer.py` 的 `_read_events_for_children`：
- 聚合 `phase_heartbeat` 事件 → 取最新 `tasks_completed` / `tasks_total`
- 优先用 heartbeat 数据渲染 `"X 完成 N/M (last: task_name)"`，无 heartbeat 时降级到原 phase-event ratio 格式

### 涉及文件

- `skills/rddf-session/scripts/rddf_session_hooks.sh` (heartbeat heredoc 追加 phase_heartbeat 写端)
- `_lib/workflow_synthesizer.py` (`_read_events_for_children` 聚合逻辑)
- 新增 `tests/integration/test_phase_heartbeat_progress.py` (e2e fixture)

## Acceptance

- **AC-P2-2-1**: `rddf_session_hook_heartbeat <kind> [tasks_total=N tasks_completed=M]` 在 events.jsonl 追加 1 行 `phase_heartbeat` 事件，context 含 `tasks_total` + `tasks_completed`
- **AC-P2-2-2**: `workflow_synthesizer(child_progress).detail` 在有 heartbeat 时渲染 `"X 完成 {tasks_completed}/{tasks_total}"`（不是原 0/1 ratio）
- **AC-P2-2-3**: heartbeat 数据格式：`{"event_type":"phase_heartbeat","context":{"tasks_total":5,"tasks_completed":3,"session_id":"rds_xxx","kind":"stage_builder"}}` 通过 `EventsLog.append_event` 写入并经 `read_since` 原样读回（含 `tasks_total`/`tasks_completed` 字段）
- **AC-P2-2-4**: 心跳频率默认 5 min（per existing heartbeat timeout），可由 RDDF_HEARTBEAT_INTERVAL_SEC env var 调整

## Capabilities

### MUST (M-HB1~5)

- **M-HB1**: `rddf_session_hook_heartbeat` 追加 phase_heartbeat 事件写入（除更新 last_heartbeat 字段外）
- **M-HB2**: heartbeat 事件 context 子结构含 `tasks_total` / `tasks_completed` / `session_id` / `kind` / `owner_opencode_session_id`
- **M-HB3**: workflow_synthesizer 优先消费 heartbeat 数据（降级到 phase_started/completed ratio）
- **M-HB4**: 字段均 optional（旧代码 / 未调用方不传时不写入 schema-violating 字段）
- **M-HB5**: 心跳频率可配置（`RDDF_HEARTBEAT_INTERVAL_SEC` env var 默认 300s）

### MUST NOT (MN-HB1~3)

- **MN-HB1**: 不修改 events.jsonl 的 7 类 event_type 白名单（per ADR-0055）
- **MN-HB2**: 不修改 phase_started / phase_completed 的写端语义
- **MN-HB3**: 不强制要求所有调用方传 tasks_total — 旧调用方零行为变更

## Impact

### 用户体验
- **真任务进度可见**: monitor --watch=1 Panel 5 显示 "rdd-builder 完成 3/5 tasks"，而不是 "完成 0/1"
- 4 个 rdd-* skill (arch/planner/builder/verifier) 的 execute 循环可周期性报告 task 进度

### 代码量
- heartbeat 写端: ~15 行 (python heredoc 追加)
- synthesizer 聚合逻辑: ~30 行 (`_read_events_for_children` 扩展 + `ChildProgress.detail` 渲染)
- 测试: ~150 行（heartbeat 写端 roundtrip + synthesizer 渲染 + 降级 path）

### 测试影响
- `tests/unit/test_workflow_synthesizer_events.py` (Wave 2 14 tests): 扩展 ~3 个 test 锁 heartbeat 渲染
- 新增 `tests/integration/test_phase_heartbeat_e2e.py`: heartbeat 写端真 subprocess 验证

### 文档影响
- `docs/architecture/guide-orchestrator-flow.md` §6.3 Wave 3 P2-2: 标记完成
- `docs/adr/ADR-0056-guide-orchestrator-minimal-usage-flow.md` §决策 2 Wave 3: 标记完成
- `_lib/schemas/...`: 若有 events schema 文件需更新 description（`context.tasks_total` / `context.tasks_completed` optional）

### 风险
- **R1 (低)**: 调用方未传 `tasks_total` 时 detail 降级到 "完成 0/1" — 与 Wave 2 行为相同，无回归
- **R2 (中)**: heartbeat 事件高频写 events.jsonl（默认 5min/次 / session = 12/h）— 文件大小仍受 50MB cap 控制；archival reset 正常工作
- **R3 (低)**: schema 扩展需同步 `_lib/schemas/` 描述（per MN1 兼容）— 易漏；测试覆盖 `.context.tasks_total` 解析即可锁

### 依赖与协同
- 上游: `feat-guide-orchestrator-session-event-bus` (shipped, 7 类 event_type 已定义)
- 协同: `complete-guide-orchestrator-flow` W2.2 (shipped, synthesizer 消费端已实现，本提案仅扩展渲染)
- 下游: rdd-builder P2 execute 循环 (未来机会，调用 heartbeat 报告 task 进度)