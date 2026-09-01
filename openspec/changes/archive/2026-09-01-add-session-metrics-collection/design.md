# add-session-metrics-collection

## Context

**症状 (2026-08-31 session 复盘)**:

- 一次完整 5 阶段流程（design 批准 2 提案 → plan fill → ship 2 change → archive）总耗时 ~12 小时
- 关键耗时：4 轮回归门各 ~8 分钟（合计 ~32 分钟），其中多轮因 KNOWN_FAILURES / specs/ 缺失 / flaky E2E 误报而重跑
- 工具调用分布（估算）：
  - design: ~30 次 bash + 4 question
  - plan: ~40 次 bash + 1 question + 4 write
  - ship: ~50+ 次 bash + 5 question + 3 skill + 2 task(deep agent)
- 用户决策点：~10 个 question（菜单选择 / 批准 / 路径）
- 重试：回归门 4 轮（2 次因 pre-existing WIP + specs/ 缺失，1 次 flaky E2E）
- 但以上全是**事后人工估算**，无系统记录

**根因分析**:

`_lib/session.py` / `_lib/session_manager.py` / `_lib/session_stats.py` 已管理 rddf-session 生命周期（创建/关闭/父子/心跳），但 `sessions.json` schema 只含：

```json
{ "stage": "stage_ship", "status": "completed", "parent": "...", "owner_opencode_session_id": "..." }
```

无以下字段：
- 阶段开始/结束时间戳（用于耗时）
- 工具调用计数（按类型）
- 用户决策计数（question 交互）
- 重试次数 / 失败原因
- change 数 / commit 数

`session_stats.py` 已有会话统计基础（消息数、token 数），但未接入工作流阶段指标。

**影响范围**:

- 无法量化「哪个阶段最耗时」→ 无法针对性优化
- 无法验证改进提案（如 `worktree-context-persistence` 减少 354 cd）的实际效果
- 无法检测回归门重复跑的浪费（本次 4 轮 vs 理想 1 轮）
- 复盘依赖人工回忆（本次 session 复盘靠估算）

## Goals

**In Scope**:

- 新增可选字段（向后兼容，旧 session 缺失不影响）：
- schema 文件 `skills/_lib/schemas/sessions_schema.json` bump version 3
- 旧 session 缺 metrics 字段 → 读取时 default `{}`（向后兼容）
- rddf-session 入口 hook（`rddf_session_hook_entry`）：记录 `started_at`
- rddf-session 关闭 hook（`rddf_session_hook_close`）：记录 `ended_at` + `duration_s`
- tool call 计数：在 `_lib/loop/actions.py` / `_lib/loop_engine.py` 的 action dispatch 处增量计数（bash/write/read/skill/task/question 分类）
- question 决策：在 `_lib/loop/human_nodes.py` 的 human 交互处计数
- retry：在 `_lib/loop/tribunal.py` 或 gate 失败重试处计数
- 不侵入 vendor 工具调用（opencode/Claude Code 的 tool schema 由 vendor 决定，只在自己代码层计数）
- 新子命令：`rddf session metrics <session_id>` 查看单 session 指标
- `rddf session metrics --recent` 查看最近 N 个 session 的汇总表（阶段 × 耗时 × 决策 × 重试）
- `rddf session metrics --stage=ship` 按阶段过滤
- 输出格式：markdown 表格（与 `rddf status` 风格一致）
- sessions.json 每 session 增加 `phase_breaks` 数组：`[{stage, started_at, ended_at, duration_s}]`
- 依赖各阶段 skill 的 entry/close hook（guide-arch/guide-design/guide-plan/guide-ship/rdd-verifier 已有 rddf-session hook，只需记录时间戳）
- **不修改** vendor 工具调用记录（opencode trace 由 opencode 自己的 session 管理）
- **不实现** 实时 dashboard（`rddf session metrics` CLI 输出足够，dashboard 归 feature 阶段）
- **不修改** `sessions.json` 的 stage/status/parent 语义
- **不实现** 自动 proposal 生成（基于 metrics 的改进建议由人工判断）
- **不重写** `session_stats.py`（复用其基础统计，扩展 metrics）

### 关键场景

### 场景 1: 完整 5 阶段流程的 metrics 收集

- **GIVEN** 用户跑完整 arch → design → plan → ship → verify 流程（跨多个 rddf-session）
- **WHEN** 每阶段 entry/close hook 触发
- **THEN**
  - 每 session 记录 started_at / ended_at / duration_s
  - tool_calls 按类型计数（bash/write/read/skill/task/question）
  - user_decisions 计数（human 交互点）
  - retries 计数（gate 失败重试）
  - `rddf session metrics --recent` 显示 5 阶段耗时 + 决策/重试汇总

### 场景 2: 回归门多轮重跑的检测

- **GIVEN** ship 阶段跑了 4 轮回归门（因 KNOWN_FAILURES / specs/ / flaky E2E）
- **WHEN** `rddf session metrics <ship-session-id>`
- **THEN** 显示 `retries: 4` + `retry_reasons: ["KNOWN_FAILURES drift", ...]`
- **AND** 复盘可量化「4 轮 vs 理想 1 轮」的浪费

### 场景 3: 改进效果验证

- **GIVEN** `worktree-context-persistence` 提案声称减少 354 cd
- **WHEN** 实施后跑新 5 阶段流程，对比 `tool_calls.bash` 指标
- **THEN** 指标显示 bash 调用数是否下降（量化验证改进）

### 场景 4: 旧 session 向后兼容

- **GIVEN** 已存在的旧 session（v2 schema，无 metrics 字段）
- **WHEN** `rddf session metrics` 查询
- **THEN** metrics 显示 `{}`（或 "no metrics recorded"），不报错，不影响其他字段

**Out of Scope**:

- (no items specified)

## Decisions

- **MUST NOT**: 破坏 `sessions.json` 现有 schema 读取（旧 session 缺 metrics 不报错）
- **MUST NOT**: 修改 vendor 工具调用（只计数自己的 action dispatch）
- **MUST NOT**: 引入新依赖（Python stdlib + 现有 `_lib/session*.py`）
- **MUST**: schema version 从 2 → 3，消费者拒绝 version=0 payload（对齐 `arch_handoff_schema` 模式）
- **MUST**: metrics 写入是 append-only 增强（不重写既有字段）
- **SHOULD**: 采集开销 < 1ms/事件（只做内存计数，session close 时才落盘）
- **SHOULD**: 与 `session_stats.py` 复用（不重复实现计数逻辑）

## Risks

- (no items specified)
