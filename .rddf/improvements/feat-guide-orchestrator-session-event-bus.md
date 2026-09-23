# feat-guide-orchestrator-session-event-bus: 跨 OpenCode 窗口的 guide 主入口 + 事件总线

> **状态**: Proposed（待 rdd-builder 批准 → rdd-builder P0 决策）
> **日期**: 2026-09-22
> **影响范围**: rddf-session (kind 扩展 + 心跳分级) + guide (stage_guide 集成 + 轮询) + hooks (parent_kind_map + 写事件) + events_log (新模块) + monitor (双路径 fallback) + doctor (state-json 检查)

---

## Why

rdd-workflow v4 实现了四阶段工作流（rdd-arch → rdd-planner → rdd-builder → rdd-verifier）+ `guide` 推荐器，但 `guide` 是**无状态冷启动推荐器**——每次 `skill_use("guide")` 都从零扫描，无法感知其他 OpenCode 进程窗口里的 rddf-session 进度。

**用户场景**：用户在 OpenCode 窗口 A 跑 guide，窗口 B 跑 rdd-builder，希望 A 能看到 B 的进度。

**关键事实**（OpenSpec change 内容已通过 Oracle + Metis 双审查 + 全部修复）：

- `_lib/core/event_log.py` 模块虽已实现但**实际未使用**——`.rddf/state/event-log.jsonl` 不存在，`find` 验证
- `_commands.py:84-94` 有 stage-level singleton 守卫，会**阻塞用户场景**（修复：双向豁免）
- `parent_session_id` 在 `hooks.sh:274` 已有 3 个映射，缺 `stage_arch → stage_guide` 一环（修复：扩展 + owner-scoped）
- `_KIND_ALIAS` 加 `"guide-orchestrator": "stage_guide"` **不够**——必须同时加到 `_VALID_KINDS`（修复：双加）
- 30min 心跳超时对常驻 guide 不适用（修复：8h 分级）
- 跨 OpenCode 进程**架构性排除** push 机制（opencode `promptAsync` 需同 SDK 客户端句柄）

**OpenSpec change 已完成**：详见 `openspec/changes/feat-guide-orchestrator-session-event-bus/`（proposal + design + tasks + spec，4 文件 863 行，`openspec validate` 通过）

---

## What Changes（高层摘要；详见 proposal.md）

- 新建 `stage_guide` 作为第 5 个 rddf-session kind + schema v2 → v3
- 新建 `.rddf/state/events.jsonl`（不可复用——现有 event-log.jsonl 不存在）
- `_commands.py` 加 stage_guide 双向 singleton 豁免 + 8h 心跳分级 + `list_sessions` owner/state 过滤 + `check_heartbeat_timeouts(readonly=True)` 只读变体
- `rddf_session_hooks.sh` 扩展 `parent_kind_map` + owner-scoped 父查找 + 写 phase_* 事件 + 新增 guide_entry/close hook
- 新建 `events_log.py`（append_event / read_since / mark_seen / archive_events + 重置 last_seen_offset）
- `guide_entry.sh` 集成 stage_guide session + 轮询契约（先查 sessions.json → 读 events.jsonl since last_seen_offset → 渲染 → 更新）
- `monitor_cmd.py` 双路径 fallback（先 events.jsonl 再 event-log.jsonl）+ 新事件类型 `.get()` 容错
- `rdd-doctor --category state-json` 新增 2 条断言（events.jsonl JSON 合法 / last_seen_offset 合法）
- 文档同步（multi-session.md + CHANGELOG + USAGE + AGENTS.md + ADR-0055 状态）

---

## How（实施路径；详见 tasks.md 的 4 PR × TDD 5 步）

**4 个 PR**（按依赖顺序，每 PR 走 rdd-workflow TDD 5 步结构）：

| PR | 内容 | LOC | 测试 |
|---|---|---|---|
| **PR 1** | schema v2→v3 + `_VALID_KINDS` 双加 + 新建 `events_log.py` + `_commands.py` 改造（singleton 豁免 + list_sessions 过滤 + heartbeat readonly） | ~120 | 8 unit |
| **PR 2** | `hooks.sh` 扩展（parent_kind_map + owner-scoped 查找 + 写事件 + guide hook）+ `monitor_cmd.py` fallback | ~80 | 8 integration |
| **PR 3** | `guide_entry.sh` 集成（创建 stage_guide + 轮询契约）+ `scan-state.sh` 移除心跳副作用 | ~50 | 7 integration |
| **PR 4** | 文档 + doctor + ADR-0055 状态更新 | ~120 | 3 integration |

**Worktree 模式**：因 `.rddf/wt/test-change` 已有活跃 worktree，rdd-builder 自动用 worktree 模式（创建 `feat-guide-orchestrator-session-event-bus` 分支隔离）

**回归门控**：每个 PR 后跑 `./test.sh --quick`；PR 3 + PR 4 后跑 `./test.sh --full --regression` 必须全绿（或仅 baseline 已知失败）

---

## Acceptance（18 项；详见 proposal.md）

来自 OpenSpec change，已通过 Oracle + Metis 双审查 + 全部 BLOCKER 修复：

- **AC-1**：schema v2 → v3；`stage_guide` + `guide-orchestrator` 双加 `_VALID_KINDS`（Oracle B2 修复）
- **AC-2**：`_commands.py` 加 stage_guide **双向** singleton 豁免（Oracle B1 修复）
- **AC-3**：stage_guide 独立 8 小时心跳超时（按 kind 分级）
- **AC-4**：新建 `events.jsonl` + `events_log.py`（**不是** event-log.jsonl——`test_no_event_log_jsonl_alias` 反模式守卫）
- **AC-5**：`events_log.py` 提供 append/read_since/mark_seen/archive_events + flock + atomic + **50MB cap 实施**（不仅是配置）
- **AC-6**：`hooks.sh` 扩展 `parent_kind_map` + **owner-scoped** 父查找（修复 hooks.sh:524 已损坏的 detach 调用）
- **AC-7**：hook 写 phase_started/completed/failed
- **AC-8**：新增 `rddf_session_hook_guide_entry/close`
- **AC-9**：guide 轮询契约（先查 sessions.json → 渲染 → 更新 last_seen_offset）
- **AC-10**：`monitor_cmd.py` **双路径 fallback**（Oracle B5 修复）
- **AC-11**：`scan-state.sh:535` `check_heartbeat_timeouts` 改只读检查（违反 guide 只读契约）
- **AC-12**：`rdd-doctor --category state-json` 新增 2 条断言
- **AC-13**：文档同步 + ADR-0055 状态更新
- **AC-14**：全量回归 `./test.sh --full --regression` 通过
- **AC-15**（Metis 新严重）：`archive_events()` 后**重置所有 active stage_guide 的 `last_seen_offset = 0`**（行号重置归档后掉队问题）
- **AC-16**：`_VALID_KINDS` 双加 belt-and-suspenders 兼容
- **AC-17**：`events_log.py` 的 `list_sessions` 接受 `owner_opencode_session_id` + `state`
- **AC-18**：`check_heartbeat_timeouts(readonly=True)` 只读变体（scan-state.sh 用）

---

## Capabilities（MUST / MUST NOT；详见 proposal.md）

### MUST

- 新增 `stage_guide` rddf-session kind（schema 扩展）；**不阻塞**其他 stage 的并发创建（双向 singleton 豁免）
- 新建 `.rddf/state/events.jsonl` 文件事件总线（fcntl.flock + 50MB cap + `archive_events(keep=1000)` + 重置 last_seen_offset）；7 类新事件类型
- stage_guide session 跟踪每个 owner 的 `goal.last_seen_offset`（per-owner 进度，跨多 OpenCode 窗口正确）
- guide_entry.sh 启动时创建 stage_guide session，退出时 close（受 `RDDF_GUIDE_SESSION_ENABLED` 控制）
- guide 轮询契约：先查 sessions.json → 有 active 子会话才读 events.jsonl → 渲染 → 更新 `last_seen_offset`
- hook entry/close 自动写 phase_started / phase_completed / phase_failed 事件
- rdd-doctor 新增 events.jsonl 完整性检查
- **全局单例约束（H7）**：`stage_guide` 是**全局单例**——一次只能有一个活跃 stage_guide session（不论 owner）。第二次启动会触发 ConflictError，需先 resume 或 abandon。

### MUST NOT

- **不**修改 OpenCode session 语义或要求 opencode 平台加 API
- **不**引入 IPC / socket / HTTP server / SQLite / fs.watch（见 ADR-0055 备选方案分析）
- **不**改动现有 rdd-arch / rdd-planner / rdd-builder / rdd-verifier 的**阶段状态机内部业务逻辑**（仅改 hook entry/close 调用）
- **不**改 `_commands.py` 中的 `create_session` 主流程逻辑（仅扩展：`list_sessions` 接受新参数、`check_heartbeat_timeouts` 接受 `readonly` 参数、`stage-level singleton` 加 stage_guide 双向豁免分支）
- **不**实施 push 推送（跨进程架构性排除——ADR-0055 §决策 5.1）
- **不**放宽 `additionalProperties: false` schema 约束
- **不**改动现有 `event_log.py`（保持未启用状态）；新事件用独立 `events.jsonl`
- **不**改 `parent_session_id` 的单父查找为多父（保持树状层级严格）

---

## Capabilities 完整性检查（已通过）

- ✅ OpenSpec 变更：`openspec/changes/feat-guide-orchestrator-session-event-bus/`（proposal.md 99 行 / design.md 366 行 / tasks.md 147 行 / spec.md 246 行 = 863 行）
- ✅ Oracle 审查通过：APPROVE WITH MINOR REVISIONS（5 CRITICAL 全部修复）
- ✅ Metis 审查通过：MAJOR REVISIONS REQUIRED（8 HIGH + 1 新严重 BLOCKER 全部修复）
- ✅ `openspec validate` 通过："Change 'feat-guide-orchestrator-session-event-bus' is valid"
- ✅ Baseline `test_adr_index_gate` 测试通过（README 与生成器一致）

---

## Cross-Reference

- **OpenSpec change**: `openspec/changes/feat-guide-orchestrator-session-event-bus/`
- **ADR**: `docs/adr/ADR-0055-guide-orchestrator-session-event-bus.md`（v3, Oracle 修订 + Metis 修复后）
- **父 ADR**: ADR-0017 (rddf-session), ADR-0034 (rdd-verifier), ADR-0043 (v4 stage-merge), ADR-0048 (rdd-builder P0 5-option 修正)
- **依赖**: 旧 `event_log.py` 模块（不修改，仅参考 event_id 格式）；现有 `hooks.sh` 的 `_rddf_resolve_owner()`（统一 $PPID）