# ADR-0055: Guide-as-Orchestrator Session + Cross-Container Event Bus

> **状态**: 待采纳（草案 v2 — Oracle 修订）
> **日期**: 2026-09-22
> **决策者**: sisyphus (受用户委托起草) + Oracle (read-only 架构审查)
> **依据**: ADR-0017 (rddf-session), ADR-0034 (rdd-verifier), ADR-0043 (v4 stage-merge), ADR-0048 (rdd-builder auto-pick), ADR-0051 (skill description convention), ADR-0040 (schema v2 注释)
> **版本目标**: v4.1

> ## v2 修订摘要（基于 Oracle 深度分析）
>
> | # | 原 v1 | v2 | Oracle 论据 |
> |---|-------|----|----|
> | 1 | 新建 `events.jsonl` | **扩展**现有 `event-log.jsonl` | 避免双事件源；复用 file-lock + 50MB 上限 + query API + monitor/orchestrate 已有消费者 |
> | 2 | schema v1 → v2 | schema **v2 → v3** | schema 实际已是 v2（sub_phase/workflow_group）；ADR-0040 声称的 v3 metrics 未落地 |
> | 3 | parent 串联伪代码 | **扩展**现有 `parent_kind_map` | hooks.sh:274 已有 3 个映射 |
> | 4 | 决策 5"不开 IPC" | 显式排除 promptAsync | 用户场景跨进程，promptAsync 需同 SDK 句柄（架构排除） |
> | 5 | `seen_by` 数组 + GC | `seen_by` **标量**（guide 单例） | 数组膨胀归零 |
> | 6 | 5 步实施 | **4 步**（Step 1+2 合并） | effort 缩小 ~40% |
> | 7 | 新建 `events_log.py` | **扩展** `event_log.py` | 减少新文件 |
> | 8 | doctor `--category events-bus` | **并入** `--category state-json` | 推迟完整 category |
> | 9 | In Scope 缺消费点迁移 | 显式加 `monitor_cmd.py:153` + `orchestrate_cmd.py` | 字段扩展需同步 |
> | 10 | 决策 5 缺轮询契约 | 补充"先查 sessions.json 再读 events" | 避免无谓 IO |

## Context

### 用户场景

在 opencode AI 编程助手上集成 rdd-workflow 时，用户期望 `guide` 成为"主会话入口"：

1. **进入**：打开 opencode → 自动进入 guide 模式 → 看到项目当前状态 + 推荐下一步
2. **路由**：在 guide 中表达意图（"执行 fix-bug"）→ guide 自动路由到 rdd-builder
3. **观察**：rdd-builder 在**另一个 opencode 会话窗口**执行完后 → guide 所在的窗口能看到结果

第 3 点是核心需求 —— **跨 OpenCode session 容器的工作流状态可见性**。

### 现状分析（v2 事实核查后）

| 模块 | 现状 | 缺口 |
|------|------|------|
| `_lib/core/event_log.py` (148 行) | **已文件持久化** —— 写入 `.rddf/state/event-log.jsonl`，fcntl.flock 保护（line 78-81），10K 事件 <100ms 查询（line 5 测试），已有 `query()` API | 缺工作流事件类型（仅基础 EventType）；缺 `session_id` / `kind` / `seen_by` 字段；缺 `archive_events()` 方法 |
| `_lib/core/defaults.py:28-30` | `event_log.path: .rddf/state/event-log.jsonl`，`max_size_mb: 50`（line 68 `EVENT_LOG_PATH` 常量） | 缺 `archive_keep` 配置 |
| `skills/rddf-session/scripts/rddf_session_hooks.sh:274` | **已部分串联 parent** —— `parent_kind_map = {"stage_design": "stage_arch", "stage_plan": "stage_design", "stage_ship": "stage_plan"}` | 缺 `stage_arch → stage_guide` 唯一一环 |
| `_lib/schemas/sessions_schema.json` | 已是 **v2**（含 `sub_phase` / `workflow_group`，line 102-109），`version` 字段 `minimum: 1` 天然兼容 | 缺 `stage_guide` kind；缺 `guide-orchestrator` intent |
| `_lib/cli/monitor_cmd.py:153` + `orchestrate_cmd.py` | 已消费 `event-log.jsonl` | 字段扩展时需同步迁移（用 `.get()` 容错） |
| `goal.intent` 枚举 | `["guide-arch", "guide-design", "guide-plan", "guide-ship"]` | 缺 `guide-orchestrator` |
| `parent_session_id` 实际使用 | grep 显示 23 文件提及，hook 里 stage→stage 已有映射 | 仅缺 `stage_guide` 根节点一环 |

### Oracle 关键架构洞察（写入 ADR 作为决策依据）

> opencode 的 `session.promptAsync()` 推送注入（oh-my-opencode L3 父子通信机制）要求调用方持有目标 session 的 SDK 客户端句柄。本 ADR 的用户场景是**两个独立 OpenCode 进程**（窗口 A 与 B 各持自己的 SDK 句柄），跨进程无法复用该机制。
>
> —— Oracle 报告 §Q1

**含义**：push 方案不是工程取舍，而是架构排除。把这一点从"备选方案"升级为"核心决策依据"。

### 三个层级的概念边界

```
┌─────────────────────────────────────────────────────────┐
│ OpenCode Session (ses_xxx)                              │
│   平台侧 LLM 聊天上下文，opencode 自己管理生命周期            │
│   不可被外部"创建/嵌套"——只能由用户在 opencode UI 里开新会话  │
│                                                          │
│   ┌───────────────────────────────────────────────────┐ │
│   │ rddf-session (rds_xxx)                             │ │
│   │   工作流层抽象，持久化在 .rddf/state/sessions.json  │ │
│   │   kind: stage_guide | stage_arch | stage_design |  │ │
│   │         stage_plan | stage_ship                     │ │
│   │   parent_session_id: 串联成树                       │ │
│   │   owner_opencode_session_id: 绑定到具体 opencode 容器│ │
│   └───────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## Decision

### 决策 1: 新增 `stage_guide` 作为第 5 个 rddf-session kind（schema v2 → v3）

修改 `_lib/schemas/sessions_schema.json`：

- `kind` 枚举追加 `"stage_guide"`
- `intent` 枚举追加 `"guide-orchestrator"`（与 stage_guide 对应）
- `version` 字段保持 `minimum: 1` 以兼容 v1 / v2 存量数据（ADR-0040 声称的 v3 `metrics` 字段未落地 —— schema 无此字段）

```jsonc
"kind": {
  "type": "string",
  "enum": ["stage_arch", "stage_design", "stage_plan", "stage_ship", "stage_guide"]
}
"intent": {
  "type": "string",
  "enum": ["guide-arch", "guide-design", "guide-plan", "guide-ship", "guide-orchestrator"]
}
```

**新增到 `_VALID_KINDS`**（`skills/rddf-session/scripts/rddf_session_pkg/_types.py:27`）：

```python
_VALID_KINDS = (
    "stage_arch", "stage_design", "stage_plan", "stage_ship",
    "stage_guide",          # ← 新增
    "rdd-arch", "guide-design", "guide-plan", "guide-ship",
)
_KIND_ALIAS["guide-orchestrator"] = "stage_guide"   # intent → kind 映射
```

`stage_guide` 是 **单例**（同时只允许一个 active guide session），不参与现有 `_VALID_KINDS` 的"跨 stage 互斥"规则。

**严格必需，不可复用 `stage_arch`**：冲突检测（`_commands.py:70-94`）会自锁 + 30min 心跳超时对 guide 不适用 + 决策 4 的 parent 链需要独立根节点。

### 决策 2: 扩展现有文件事件总线（复用 `.rddf/state/event-log.jsonl`）

**不新建** `events.jsonl`。现有 `_lib/core/event_log.py::EventLog` 已是文件持久化 append-only 日志：

- 文件：`~/.rddf/state/event-log.jsonl`（`defaults.py:68` 常量）
- 并发：fcntl.flock（`core/lock.py`，`_LOCK_TIMEOUT = 10.0`）
- 上限：`max_size_mb: 50`（`defaults.py:31`）
- 查询：`query()` API，10K 事件 < 100ms（`event_log.py:5` 测试）
- 消费者：`rddf monitor`（`monitor_cmd.py:153`）+ `rddf orchestrate show`（`orchestrate_cmd.py`）

**扩展**而非重建：

| 现有字段（保留） | 新增字段（写入 `context` 子字典） |
|---|---|
| `event_id` (`evt_YYYYMMDD_HHMMSS_NNN`) | — |
| `ts` | — |
| `event_type`（基础类型） | 新增 7 类工作流事件类型 |
| `severity` | — |
| `message` | — |
| `context` | 扩展为 `{session_id, kind, parent_session_id, owner_opencode_session_id, seen_by}` |

**新增事件类型**（扩展 `EventType` enum）：

| type | 触发时机 |
|------|----------|
| `phase_started` | stage_arch / design / plan / ship / guide 进入 |
| `phase_completed` | 同上退出（state → completed） |
| `phase_failed` | 同上退出（state → failed） |
| `phase_heartbeat` | 长操作子阶段更新 |
| `guide_intent_detected` | guide 检测到路由意图 |
| `guide_routed` | guide 路由到具体 skill |
| `user_message` | 用户在 guide 中表达的内容 |

**`EventLog.record()` 签名扩展** —— 可选接受新字段，存到 `context` dict 子键。

**兼容约束**：`Event.from_dict()` 必须用 `.get()` 读取 `context` 子字段（旧事件行没有这些字段时给默认值），避免破坏历史数据 + `rddf monitor` 用户。

**`archive_events()` 新增**：超 `max_size_mb` 时把旧事件移到 `.rddf/state/event-log.archive.jsonl`，参考 `_commands.py:283-329` 的 `archive_history` 模式（`.archive.json` 后缀），配置项 `event_log.archive_keep: 1000`（新增）。

### 决策 3: `goal.intent` 新增 `guide-orchestrator`

如决策 1 schema 扩展所示。

**实施时机**：可推迟到 Step 3（guide 集成）—— `stage_guide` session 未创建前此枚举无消费者，提前加是死代码。

### 决策 4: `parent_session_id` 串联规则（扩展现有 `parent_kind_map`）

现有 `rddf_session_hooks.sh:274-275`：

```python
parent_kind_map = {
    "stage_design": "stage_arch",
    "stage_plan": "stage_design",
    "stage_ship": "stage_plan",
}
parent_kind = parent_kind_map.get(kind)
```

**扩展为**（仅新增 `stage_arch → stage_guide` 一环，保持下游映射不变）：

```python
parent_kind_map = {
    "stage_arch": "stage_guide",       # ← 新增（其余 stage 上游是 stage_arch）
    "stage_design": "stage_arch",
    "stage_plan": "stage_design",
    "stage_ship": "stage_plan",
}
# stage_guide 是根节点，parent_kind = None
```

**最终树形**：

```
stage_guide (intent=guide-orchestrator)           [根节点，parent=null]
   └─> stage_arch  (intent=guide-arch)
       └─> stage_design (intent=guide-design)
           └─> stage_plan (intent=guide-plan)
               └─> stage_ship (intent=guide-ship)
```

父 stage 不存在（用户直接调 rdd-builder 而没经过 guide）→ `parent_session_id = null`，**不报错**（向后兼容）。

**注意**：`stage_design` 等不直接挂到 stage_guide 下 —— 必须先经过 stage_arch，否则会跳级。这是有意为之：保证 tree 层级严格。

### 决策 5: OpenCode session 作为不可变容器 + 文件轮询

#### 5.1 显式排除 push 机制（架构排除，非实现取舍）

opencode 的 `session.promptAsync()` 推送注入（oh-my-opencode L3 父子通信机制）要求调用方持有目标 session 的 SDK 客户端句柄。本 ADR 的用户场景是**两个独立 OpenCode 进程**（窗口 A 与 B 各持自己的 SDK 句柄），跨进程无法复用该机制。

**结论**：推送方案在架构上不可行，文件轮询是唯一满足跨进程约束的路径。

不开 IPC、不开 socket、不要求 opencode 平台加 API。

#### 5.2 轮询触发契约

guide 每次启动 + 每次返回主菜单时：

1. **先查 sessions.json** 判定是否有 active 子会话（非本 owner）
2. **无活跃子会话** → 跳过 events 读取（避免无谓 IO）
3. **有活跃子会话** → 读 `event-log.jsonl` 渲染"上次跨容器事件"

#### 5.3 `seen_by` 降级为标量

guide 是单例消费者（决策 1），事件被读取渲染后将其 `seen_by` 覆写为当前 `owner_opencode_session_id` 即可，**无需数组**。

**含义**：
- 彻底消除 `seen_by` 数组膨胀风险
- 字段类型：`string | null` 而非 `array<string>`
- 未来若有多个消费者再升级为数组

#### 5.4 边界记录（不实施）

未来若出现同进程实时需求（单 OpenCode 窗口内 guide → 子会话），评估 opencode L3 promptAsync —— 但需处理 macOS SIGABRT 反竞态（`userMessageInProgressWindowMs` defer，issue #4120）。

**当前不实施**：同进程场景由 `guide_entry.sh` 顺序调用天然覆盖，无实时需求。

### 决策 6: hook 写事件流（扩展现有 hook 调用）

`rddf_session_hooks.sh` 在每次 entry / close 之后，调用现有 `EventLog`：

```bash
rddf_session_hook_entry() {
  # ... 现有逻辑（create_session + 串联 parent）...
  python3 -c "
from skills._lib.core.event_log import EventLog
EventLog('.rddf/state/event-log.jsonl').record(
    event_type='phase_started',
    severity='info',
    message='rddf-session: <sid> (<kind>, parent=<id>)',
    context={
        'session_id': '$session_id',
        'kind': '$kind',
        'parent_session_id': '${parent_id:-}',
        'owner_opencode_session_id': '$RDDF_OWNER',
        'seen_by': None,                # 单例消费者，无需数组
    },
)
"
}
```

**新增** `rddf_session_hook_guide_entry` / `rddf_session_hook_guide_close`，仅用于 guide 启动 / 退出。

## Implications

### In Scope

- `_lib/schemas/sessions_schema.json` v2 → v3（kind + intent enum）
- `_lib/core/event_log.py`（扩展 `Event` dataclass + 新增 7 类事件类型 + `archive_events()`）
- `_lib/core/defaults.py`（新增 `event_log.archive_keep: 1000`）
- `skills/rddf-session/scripts/rddf_session_pkg/_types.py`（`_VALID_KINDS` 追加 + `_KIND_ALIAS` 加 `"guide-orchestrator": "stage_guide"`）
- `skills/rddf-session/scripts/rddf_session_hooks.sh`（扩展 `parent_kind_map` + 写事件）
- 新增 `rddf_session_hook_guide_entry` / `rddf_session_hook_guide_close`
- `skills/guide/scripts/guide_entry.sh`（启动时 create_session + 读 events + 先查 sessions.json）
- **同步迁移既有事件消费点**：
  - `_lib/cli/monitor_cmd.py:153`（读 event-log.jsonl 尾部 5 行）
  - `_lib/cli/orchestrate_cmd.py` trace 摄入
  - 用 `.get()` 容错，**保持向后兼容**
- 测试：`tests/unit/test_event_log_extension.py`、`tests/unit/test_sessions_schema_v3.py`、`tests/integration/test_rddf_session_event_flow.bats`、`tests/integration/test_parent_kind_map.bats`、`tests/integration/test_guide_cross_container.bats`、`tests/integration/test_doctor_state_json.bats`
- `docs/architecture/multi-session.md` 新增"Cross-Container Event Bus"章节
- `rdd-doctor --category state-json` 新增 2 条断言：(1) event-log.jsonl 每行 JSON 合法；(2) seen_by 引用存在的 opencode session
- `CHANGELOG.md` + `USAGE.md` + `AGENTS.md` 同步

### Out Scope

- **不**修改 OpenCode session 语义或要求 opencode 平台加 API
- **不**引入 background daemon / IPC socket / HTTP server
- **不**改动 rddf-session 心跳 / 超时 / 冲突检测机制
- **不**放宽 `additionalProperties: false` schema 约束
- **不**改动现有 rdd-arch / rdd-planner / rdd-builder / rdd-verifier 内部业务逻辑
- **不**实施 push 推送（已架构性排除 —— 决策 5.1）
- **不**引入 SQLite（违反 file-backed 哲学）
- **不**引入 fs.watch（跨平台不一致 inotify / FSEvents / ReadDirectoryChangesW）
- **不**新建 `events.jsonl`（决策 2 —— 复用 event-log.jsonl）

### 备选方案

| 备选 | 评估 |
|------|------|
| HTTP 本地 server（FastAPI / aiohttp） | **拒绝**：不引入常驻进程；增加 CI 复杂度 |
| WebSocket / Unix socket IPC | **拒绝**：opencode 平台无 IPC API |
| 共享数据库（SQLite WAL） | **拒绝**：违反 file-backed 哲学；增加依赖 |
| 让 opencode 自己实现 session 嵌套 | **拒绝**：依赖外部平台 roadmap |
| **opencode `promptAsync()` 推送** | **拒绝（架构排除）**：跨进程场景无法复用 SDK 句柄 |
| fs.watch + inotify | **拒绝**：跨平台不一致 |
| **新建 `events.jsonl` 文件** | **拒绝**（v2 修订）：与现有 event-log.jsonl 重复，违反"双事件源"原则 |
| **`stage_guide` 复用 `stage_arch` kind** | **拒绝**：冲突检测会自锁 + 心跳超时对 guide 不适用 + parent 链需要独立根节点 |

## Consequences

### 正面

1. **跨容器可见性**：用户能在主 opencode 窗口看到子 opencode 窗口的工作流进度
2. **guide 上下文连续**：跨 opencode session 后 guide 启动能"恢复" —— 恢复工作流状态 + 最近事件
3. **`parent_session_id` 真正贯通**：补全 `stage_arch → stage_guide` 唯一缺失环节（修复 ADR-0017 实施后遗留的 dead field）
4. **零外部依赖**：纯文件系统，CI / 跨平台友好
5. **审计可追溯**：event-log.jsonl 是天然 append-only log（已存在），用于 `rddf doctor` 排查
6. **与现有架构兼容**：扩展而非重建，所有 `rddf monitor` / `rddf orchestrate show` 用户无感升级
7. **effort 缩小 ~40%**（v2 修订）：复用 event-log.py 避免双事件源；schema v2 → v3 而非 v1 → v2；Step 1+2 合并
8. **`seen_by` 标量化**（v2 修订）：彻底消除数组膨胀风险

### 负面 / 风险

| # | 风险 | 缓解策略 |
|---|---|---|
| 1 | event-log.jsonl 无界增长 | 已有 `max_size_mb: 50` 上限；新增 `archive_events(keep=1000)` 自动归档到 `.archive.jsonl`；**超限只归档不丢写**（append-only 日志的硬约束） |
| 2 | 跨文件一致性（sessions.json vs event-log.jsonl） | hooks 在**同一 `with_file_lock` 临界区内**两写（sessions.json 后立即 events.jsonl，不释放锁）；reader **只把 events 当派生视图**，永不反向推导 sessions |
| 3 | `seen_by` 数组膨胀 | **已消除**（决策 5.3 标量化） |
| 4 | 轮询延迟（1-5s） | 接受（用户场景是人工切窗）；guide 渲染时显示事件时间戳管理预期 |
| 5 | schema v2 → v3 迁移 | 简单 —— `version` 字段 `minimum: 1` 天然兼容；枚举加值；不需兼容层（ADR Step 1 声称的"读时填 null"实际上现有字段全 optional / nullable） |
| 6 | doctor 检查增加 | 推迟完整 `--category events-bus`；先加 2 条断言入 `--category state-json` |

### 后续待办

- [ ] `archive_events(keep=1000)` 实施（Step 1 一并）
- [ ] 完整 `rdd-doctor --category events-bus` category（P1，等用户量上来再加）
- [ ] guide UI 是否要展示"事件流时间线"（v4.1+ 可选）
- [ ] `rddf-session events` 子命令（list / show / archive-events）
- [ ] 未来同进程实时需求 → 评估 promptAsync（需 macOS SIGABRT 反竞态处理）

## Implementation Plan

**v2 修订后：5 步 → 4 步**

### Step 1: schema + types + EventLog 扩展（1 PR，~120 行）

- `_lib/schemas/sessions_schema.json` v2 → v3（kind + intent enum）
- `_lib/core/event_log.py`：
  - `Event` dataclass 增加可选字段（用 `.get()` 向后兼容）
  - 新增 7 类工作流事件类型（`EventType` enum 扩展）
  - `record()` 方法签名增加 `session_id` / `kind` / `parent_session_id` / `owner_opencode_session_id` / `seen_by`
  - 新增 `archive_events(keep=1000)` 方法
- `_lib/core/defaults.py` 加 `event_log.archive_keep: 1000`
- `skills/rddf-session/scripts/rddf_session_pkg/_types.py`（`_VALID_KINDS` + `_KIND_ALIAS`）
- 测试：`tests/unit/test_event_log_extension.py`、`tests/unit/test_sessions_schema_v3.py`

### Step 2: hook 写事件 + parent 串联扩展 + 消费点迁移（1 PR，~80 行）

- `skills/rddf-session/scripts/rddf_session_hooks.sh`：
  - 扩展 `parent_kind_map`（加 `stage_arch → stage_guide`）
  - 在 entry / close 现有逻辑后增加 `EventLog.record()` 调用
  - 新增 `rddf_session_hook_guide_entry` / `rddf_session_hook_guide_close`
- **同步迁移既有消费点**（必须 Step 1 + Step 2 同 PR，否则 schema 改了消费者会崩）：
  - `_lib/cli/monitor_cmd.py:153`（读 event-log.jsonl 尾部 5 行）
  - `_lib/cli/orchestrate_cmd.py` trace 摄入
  - 用 `.get()` 容错，**保持向后兼容**
- 测试：`tests/integration/test_rddf_session_event_flow.bats`、`tests/integration/test_parent_kind_map.bats`

### Step 3: guide 集成（1 PR，~50 行）

- `skills/guide/scripts/guide_entry.sh`：
  - 启动时调 `rddf_session_hook_guide_entry` 创建 stage_guide session
  - 退出时调 `rddf_session_hook_guide_close`
  - **轮询触发契约**（决策 5.2）：先查 sessions.json，有 active 子会话才读 events
  - 渲染"上次跨容器事件"到菜单顶部（含时间戳管理预期）
- `skills/guide/SKILL.md` 更新意图路由规则（L180-195）
- 测试：`tests/integration/test_guide_cross_container.bats`

### Step 4: 文档 + doctor（1 PR，~120 行）

- `docs/architecture/multi-session.md` 新增"Cross-Container Event Bus"章节
- `docs/adr/README.md` 索引更新
- `CHANGELOG.md` + `USAGE.md` + `AGENTS.md` 同步
- `rdd-doctor --category state-json` 新增 2 条断言：(1) event-log.jsonl 每行 JSON 合法；(2) seen_by 引用存在的 opencode session
- 测试：`tests/integration/test_doctor_state_json.bats`

## Migration / Rollback

### 迁移路径

- **既有 sessions.json（v1 / v2）**：所有现有 session 没有 stage_guide；Step 1 兼容层读时填充 `parent_session_id = null`
- **新增 stage_guide session**：Step 3 上线后用户首次 `skill_use("guide")` 自动创建（无需迁移命令）
- **`parent_session_id` 重建**：现有 stage_arch session 的 `parent_session_id` 是 null（建时 guide 还没 stage_guide）；**不强制重建**，新 session 才会有正确 parent（接受历史污染）
- **event-log.jsonl 不存在**：所有读操作 fall back 到空 list，UI 显示"无跨容器事件"
- **event-log.jsonl 旧字段缺失**：所有读操作 `.get()` 容错，UI 显示字段为 None

### 回滚路径

- **禁用 stage_guide 创建**：`rddf_session_hook_guide_entry` 加 feature flag `RDDF_GUIDE_SESSION_ENABLED`（默认 `true`，设 `false` 时跳过）
- **停止 events 追加**：hook 加 `RDDF_EVENTS_LOG_ENABLED` flag（默认 `true`）
- **schema 回滚到 v2**：旧数据天然兼容（`minimum: 1`）；新创建的 stage_guide session 在回滚后无法被读（acceptable：用户失去"主会话"特性，其他功能不受影响）

### Backward Compatibility

- 旧 `rdd-arch` / `rdd-planner` / `rdd-builder` / `rdd-verifier` skill 调用方式不变
- 旧 sessions.json 不需要重新生成
- 旧 event-log.jsonl 不需要迁移（新字段默认 None）
- 旧 `rddf monitor` / `rddf orchestrate show` 不需要修改（消费者用 `.get()` 容错）
- 旧 tests 不需要修改（除非测试了 sessions.json 字面结构 —— 现有 25 个 rddf_session 测试需 review 但预计无需改）

## References

- ADR-0017 §Implementation — RddfSessionCoordinator 模式（file-lock + atomic write + 心跳）
- ADR-0034 §5 — rdd-verifier 阶段扩展
- ADR-0048 §Decision 3 — rdd-builder P0 5-option
- ADR-0010 §扩展状态向量 Schema — `parent_session_id` 字段最初设计
- ADR-0051 §Skill Description Convention
- ADR-0040 §schema v3 metrics — 声称的 v3 metrics 字段未落地；本 ADR 是 v2 → v3 的实际升级
- `_lib/core/event_log.py` (148 行) — **已存在的文件持久化 event log**（v2 核心复用对象）
- `_lib/core/defaults.py:28-30, 68` — `event_log.max_size_mb: 50` + `EVENT_LOG_PATH` 常量
- `rddf_session_hooks.sh:274-275` — **已存在的 `parent_kind_map`**（v2 核心扩展点）
- `_lib/cli/monitor_cmd.py:153` — **已存在的 event-log.jsonl 消费点**（同步迁移对象）
- `_lib/cli/orchestrate_cmd.py` — trace 摄入（同步迁移对象）
- `docs/architecture/state-and-events.md` — 既有 event-log 文档
- oh-my-opencode `dist/features/background-agent/parent-wake-notifier.d.ts` — promptAsync + ParentWakeNotifier 模式参考（**跨进程场景下不可用**）
- oh-my-opencode `dist/tools/call-omo-agent/session-creator.d.ts` — `createOrGetSession()` session_id 复用机制（用户提到的"Oracle 反复追问"原理）
- `skills/guide/SKILL.md` L180-195 — 现有意图路由规则（决策 4 扩展点）
- Oracle 报告 §Q1-Q5 — v2 修订依据（透明化决策来源）
- `.rddf/improvements/add-session-progress-view.md` — P1 已存在，可复用其进度视图

---

## v2 修订日志

| 修订 | 原 v1 内容 | v2 内容 | Oracle 论据 |
|------|-----------|---------|------------|
| 1 | 新建 `.rddf/state/events.jsonl` | 扩展现有 `.rddf/state/event-log.jsonl` | 避免双事件源；复用 file-lock + 50MB 上限 + query API + monitor/orchestrate 消费 |
| 2 | schema v1 → v2 | schema v2 → v3 | schema 实际已是 v2（sub_phase/workflow_group） |
| 3 | parent 串联伪代码 case | 扩展现有 `parent_kind_map` | hooks.sh:274 已有 3 个映射 |
| 4 | 决策 5"不开 IPC" | 显式排除 promptAsync（架构排除） | 用户场景跨进程，promptAsync 需同 SDK 句柄 |
| 5 | `seen_by` 数组 + GC | `seen_by` 标量（guide 单例） | 数组膨胀归零 |
| 6 | 5 步实施 | 4 步（Step 1+2 合并） | effort 缩小 ~40% |
| 7 | 新建 `events_log.py` 模块 | 扩展 `event_log.py` 现有类 | 减少新文件 |
| 8 | doctor `--category events-bus` | 并入 `--category state-json` | 推迟完整 category |
| 9 | In Scope 缺消费点迁移 | 显式加 `monitor_cmd.py:153` + `orchestrate_cmd.py` | 字段扩展需同步 |
| 10 | 决策 5 缺轮询契约 | 补充"先查 sessions.json 再读 events" | 避免无谓 IO |

> **下次审查**: v2 草案提交后 24h 内（无反对则采纳）；采纳后按 Step 1 → Step 4 顺序实施。