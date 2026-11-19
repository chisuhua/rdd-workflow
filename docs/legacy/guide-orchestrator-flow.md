# Guide Session 作为唯一交互入口 — 完整流程架构

> **范围**: 本文档描述 rdd-workflow v4.2 的**用户视角**最小用法流程。
> 用户**只**与 guide session 交互,guide 自动/手动调度下属 rddf session 推进 workflow。
>
> **For**: 用户 + 维护者。
> **状态**: 与 ADR-0056 同步,Wave 1 已 ship,Wave 2 进行中。
> **更新**: 任何 `guide_entry.sh` / `rddf_session_hooks.sh` / SKILL.md 改动后,本文件必须同步更新(同 ADR-0055 强约束)。

---

## 1. 设计目标(用户视角)

### 1.1 用户感知

```
我打开 OpenCode →
  guide session 创建 →
    看到项目状态 + 推荐下一步 →
      说/做这件事 →
        guide 自动/手动调度 →
          其他窗口看到我的进度 →
            完成 → 我回到 guide 看结果
```

**关键不变式**: 用户**只**与 guide session 交互。其他 session 是 guide 的"下属",由 guide 或 AI agent 调度。

### 1.2 与 v4.0 的差异

| 维度 | v4.0 之前 | v4.2(本架构) |
|---|---|---|
| 用户入口 | 5 个 skill 都可独立调用 | **唯一** guide session |
| 子阶段协同 | 手动切换 skill,无共享状态 | 通过 events.jsonl 自动协同 |
| 多窗口 | 不支持 | 支持(前提 OPENCODE_SESSION_ID 不同) |
| 进度可见 | 仅当前 skill 输出 | guide 渲染 child 进度 + 推荐下一步 |
| 历史回放 | 无 | events.jsonl 完整 timeline |

---

## 2. 核心实体

### 2.1 stage_guide session(long-lived orchestrator)

```yaml
kind: stage_guide
owner_opencode_session_id: <user-opencode-window-uuid>
parent_session_id: null  # 根节点
goal:
  intent: guide-orchestrator
  last_seen_offset: N  # events.jsonl 已读到的行数
state: active  # 直到用户退出或 8h 无 heartbeat
heartbeat_timeout: 8h  # vs 普通 stage 的 30min
```

**约束**(per ADR-0055 H7):
- 同一 owner **最多** 1 个 active stage_guide
- 第二次创建返回已有 session(不创建新)

**owner 标识**(per `fix-rddf-session-owner-stability.md` 4 层 fallback):
1. `$OPENCODE_SESSION_ID` env(OpenCode 平台层注入,highest)
2. `~/.cache/rddf-session-owner` cache 文件(per-host, TTL 1h)
3. `/proc/<shell-ppid>/cmdline` probe(depth ≤5, must contain "opencode")
4. `$(hostname -s)_$$` 当前 shell PID(最后 fallback)

### 2.2 events.jsonl(workflow event bus)

```jsonl
{"event_type":"phase_started","session_id":"rds_xxx","kind":"stage_arch","parent_session_id":"rds_guide","owner_opencode_session_id":"<owner>","timestamp":"2026-09-24T10:00:00Z"}
{"event_type":"phase_completed","session_id":"rds_xxx","kind":"stage_arch","end_reason":"arch-done","timestamp":"2026-09-24T10:05:00Z"}
```

**约束**:
- 文件位置:`.rddf/state/events.jsonl`
- 写保护:`fcntl.flock(LOCK_EX)`(阻塞式,非 NB — per `fix-events-log-blocking-lock`)
- 大小上限:50MB;超出自动 archive 到 `events.archive.jsonl`(line offset 重置)
- Append-only:永不修改历史行
- 7 类 event type:`phase_started` / `phase_completed` / `phase_failed` / `phase_heartbeat` / `guide_intent_detected` / `guide_routed` / `user_message`

### 2.3 last_seen_offset(per-owner poll progress)

**位置**: `sessions.json` 内 `stage_guide.goal.last_seen_offset`(int)
**语义**: "guide 已读到 events.jsonl 第 N 行"
**写入**: 每次 `guide_entry` 渲染完成后
**重置条件**: `archive_events` 把 events.jsonl 切片后,所有 stage_guide 强制重置为 0(一次性 re-read)

---

## 3. 数据流(用户视角)

### 3.1 单窗口流程(无 background poll)

```
[User]  "我想给项目加 RBAC"
  ↓
[AI Agent] skill_use("guide")
  ↓
[guide_entry.sh] 读 sessions.json + events.jsonl since last_seen_offset
  ↓
[workflow_synthesizer] 输出 RECOMMEND="rdd-arch" + 理由
  ↓
[AI Agent] skill_use("rdd-arch")
  ↓
[rddf-arch SKILL.md]
  ├─ source rddf_session_hooks.sh
  ├─ rddf_session_hook_entry  → phase_started event 写入
  ├─ [arch state machine 执行...]
  └─ trap rddf_session_hook_close EXIT INT TERM
     └─ exit 触发 → phase_completed event 写入
  ↓
[User]  "现在该做什么?"
  ↓
[AI Agent] skill_use("guide")
  ↓
[guide_entry.sh]
  ├─ 读 events.jsonl since last_seen_offset → 看到 phase_completed
  ├─ last_seen_offset += 1
  ├─ workflow_synthesizer → RECOMMEND="rdd-planner"
  └─ 渲染菜单
  ↓
[循环直到所有 stage 完成 → archive → done]
```

### 3.2 多窗口流程(2 OpenCode windows)

```
┌──────────────── Window A (Guide) ────────────────┐
│                                                  │
│  $OPENCODE_SESSION_ID=ses_A                      │
│  skill_use("guide") → stage_guide (owner=ses_A) │
│  last_seen_offset = 0                            │
│                                                  │
│  [Long-lived polling loop]                       │
│    read events.jsonl since last_seen_offset      │
│    render "child: stage_builder 2/5 done"        │
│    last_seen_offset = latest                      │
│                                                  │
└──────────────────────────────────────────────────┘
                       ↕ shared files
┌──────────────── Window B (Builder) ──────────────┐
│                                                  │
│  $OPENCODE_SESSION_ID=ses_B                      │
│  skill_use("rdd-builder")                        │
│    phase_started event → events.jsonl            │
│    [build state machine...]                      │
│    phase_completed event → events.jsonl         │
│                                                  │
└──────────────────────────────────────────────────┘
```

**前置条件**:
1. ses_A ≠ ses_B(否则 H7 ConflictError 或 owner 串扰)
2. rdd-builder SKILL.md 显式要求调用 hooks(per AC-G1)

---

## 4. 协议层(7 类 event)

### 4.1 event schema(v3, per ADR-0055)

```python
{
    "event_type": str,                    # 必填
    "session_id": str,                    # 必填,rddf-session id
    "kind": str,                          # 必填,rddf-session kind
    "owner_opencode_session_id": str,     # 必填
    "parent_session_id": str | None,      # 可选
    "timestamp": str,                     # ISO 8601 UTC
    "severity": "info" | "warn" | "error",
    "message": str,                       # 自由文本
    "context": dict,                      # event_type 特定字段
}
```

### 4.2 7 类 event type 详细

| event_type | 写入者 | 触发时机 | context 字段 |
|---|---|---|---|
| `phase_started` | `rddf_session_hook_entry` | skill 入口 | `{kind, parent_session_id, ...}` |
| `phase_completed` | `rddf_session_hook_close` | skill 正常退出 | `{end_reason, duration_seconds}` |
| `phase_failed` | `rddf_session_hook_close` | skill 异常退出 | `{error_type, error_message, traceback}` |
| `phase_heartbeat` | `rddf_session_hook_heartbeat` | 长任务定时刷新 | `{progress_percent, current_step}` |
| `guide_intent_detected` | (Wave 3 P1-1) | guide 检测用户意图 | `{intent, confidence, matched_skill}` |
| `guide_routed` | (Wave 3 P1-2) | guide 自动路由到 skill | `{target_skill, reason}` |
| `user_message` | (Wave 3 P2-2) | 用户在 guide 中表达 | `{raw_text, parsed_intent}` |

### 4.3 写入路径约束

每个 hook 调用必须满足:
```bash
# Hybrid fallback path (per D3): try relative first, fall back to PROJECT_ROOT / global install
source "${_HOOKS_SH:-$(dirname "${BASH_SOURCE[0]:-$0}")/../rddf-session/scripts/rddf_session_hooks.sh}"
[ -z "$_HOOKS_SH" ] && _HOOKS_SH="${PROJECT_ROOT:-$HOME/.agents/skills}/rddf-session/scripts/rddf_session_hooks.sh"
# (actual fallback chain follows _lib/skill_root.sh tier order — same idiom used elsewhere)

# 入口 — 5 个位置参数: <kind> <intent> <subject> <expected_outcome> [context_pointer]
rddf_session_hook_entry stage_${SKILL_NAME} rdd-${SKILL_NAME} "${SUBJECT}" "${EXPECTED_OUTCOME}" "${CONTEXT_POINTER:-}"

# 出口(trap) — 3 个位置参数: <kind> <end_reason> <intent>
trap 'rddf_session_hook_close stage_${SKILL_NAME} "${REASON}" rdd-${SKILL_NAME}' EXIT INT TERM
```

SKILL.md 必须**显式**包含这两段代码(不只是源码里有 hook 函数)。位置参数签名是 `rddf_session_hook_entry()` 的真实接口(参见 `rddf_session_hooks.sh:231-236`),**不要**使用 `--kind` / `--goal-intent` 等命名标志 — 函数不接受,会静默失败。

---

## 5. 多窗口协作(cross-process)

### 5.1 架构

```
┌─────────────────────────────────────────────────────────────┐
│ OpenCode Window A (Guide session)                           │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ stage_guide session (owner=ses_A)                    │  │
│  │   goal.last_seen_offset = N                          │  │
│  │   heartbeat: refresh on every guide_entry call       │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  Polling loop (per guide_entry invocation):                 │
│    1. Read sessions.json → find child sessions             │
│    2. Any child owned by ses_A or ses_B?                   │
│    3. Yes → read events.jsonl since last_seen_offset       │
│    4. Render child progress to menu                         │
│    5. Update goal.last_seen_offset = latest line           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              ↕ events.jsonl (fcntl flock)
┌─────────────────────────────────────────────────────────────┐
│ OpenCode Window B (rdd-builder / rdd-arch / rdd-planner)    │
│                                                             │
│  rddf_session_hook_entry   → phase_started event            │
│  [state machine execution...]                               │
│  rddf_session_hook_close   → phase_completed event          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 关键决策

| 决策 | 依据 | 理由 |
|---|---|---|
| **New `stage_guide` kind** | ADR-0055 | Long-lived main orchestrator;8-hour heartbeat vs 30min stages;global singleton per owner |
| **events.jsonl (不是 push)** | re-read session | opencode `promptAsync` 锁死单 SDK 句柄,无法跨进程;file-based 是架构 fit |
| **per-owner `goal.last_seen_offset`** | Oracle 评审 | NO `seen_by` 数组,避免事件行膨胀 |
| **Owner-scoped parent lookup** | `parent_kind_map` 扩展 | `stage_arch → stage_guide` 唯一根节点 |
| **Bidirectional singleton exemption** | H7 扩展 | stage_guide 不阻塞其他 stage;其他 stage 不阻塞 stage_guide |

### 5.3 边角案例(已接受)

| 案例 | 行为 |
|---|---|
| events.jsonl > 50MB | `archive_events(keep=1000)` 自动 archive,所有 active stage_guide 的 last_seen_offset 重置为 0(一次性 re-read) |
| 2 个 guide 不同 owner | ConflictError on 2nd create(H7 global singleton — by design) |
| 1 个 owner 2 个 stage_guide | 第二个返回已有 session(no duplicate) |
| guide 进程 SIGKILL | 下次 guide_entry 检测 heartbeat timeout → orphaned(8h 后) |

---

## 6. 已 ship 部件 vs 缺失部件

### 6.1 已 ship (v4.1, 2026-09-22~23)

| 部件 | 文件 | 验证 |
|---|---|---|
| `events.jsonl` + flock + atomic write | `events_log.py:1-308` | unit tests |
| `rddf_session_hook_entry/close` 写端 | `rddf_session_hooks.sh:298-505` | unit + integration |
| `stage_guide` kind | schema v3 | unit + e2e |
| `goal.last_seen_offset` | schema v3 | unit + e2e |
| `guide_polling_loop_implementation` | `guide_entry.sh:225-229` | unit + e2e |
| `RddfSessionCoordinator.update_last_seen_offset` | `_commands.py` | unit + e2e |
| A+B+C 三层 e2e 验证 | `tests/e2e/agent/test_multi_window_poll.bats` (REAL-2P-1/2 + MWP-1/2) | 5/5 PASS |

### 6.2 进行中 (v4.2 Wave 2)

| # | 缺口 | 影响 | 修复 |
|---|---|---|---|
| W2.0 | **kind-enum 缺 stage_builder/verify/quick** → hook 调 builder/verifier/quick 时 `RddfSessionError` 被吞 | events.jsonl 在生产路径几乎空(SKILL.md 强制 hook 也没用) | `_VALID_KINDS` + `sessions_schema.json` enum + `HEARTBEAT_TIMEOUT_BY_KIND` + `parent_kind_map` + cross-stage 豁免。**Step A.1 已完成**,锁定于 `tests/unit/test_valid_kinds_v4.py` (18 tests)。 |
| W2.1 | hook entry 块只 catch ConflictError → `RddfSessionError` 静默 traceback | invalid kind/SKILL.md 错误难诊断 | `rddf_session_hooks.sh` entry 块加 `except RddfSessionError → sys.exit(3)` 分支。**Step A.2 已完成**,锁定于 `tests/unit/test_hook_invalid_kind.py` (14 tests)。 |
| W2.2 | workflow_synthesizer 不消费 events.jsonl | menu 看不到过程 | `_lib/workflow_synthesizer.py` 融合 events |
| W2.3 | guide_entry 无 background polling | 跨窗口 progress 必须重新调 guide | 优先扩展既有 `rddf monitor --watch=N` (`monitor_cmd.py:36-61`) 而非新建第二个 watch loop |

### 6.3 未来 (v4.3+ Wave 3)

| # | 缺口 | 修复 |
|---|---|---|
| P1-1 | intent detection | NLP/正则识别 "加 RBAC" → rdd-arch |
| P1-2 | auto-routing | guide_intent_detected → guide_routed → auto-call |
| P1-3 | OpenCode 平台层 OPENCODE_SESSION_ID 注入 | 多窗口 owner 区分 |
| P2-1 | background daemon | push 方案(OpenCode 解锁 promptAsync 后) |
| P2-2 | events 类型未充分使用 | 接入 `phase_heartbeat` / `guide_intent_detected` / `guide_routed` / `user_message` |
| P2-3 | cross-repo guide | Hub-Spoke federation 接入 polling 循环 |
| P2-4 | 历史回放 | `rddf session show --events` |

---

## 7. 测试矩阵

### 7.1 三层证据(已 PASS)

| 层 | 测试 | 文件 | 验证内容 |
|---|---|---|---|
| A(手工) | `/tmp/test_real_poll_v2.sh` | 长期 bash & | last_seen_offset=10, state=completed |
| B(bats fixture) | `tests/e2e/agent/test_multi_window_poll.bats` (REAL-2P-1/2 真 subprocess × 2) | 2/2 PASS |
| C(agent scenario) | `tests/e2e/agent/test_multi_window_poll.bats` + `scenarios/mwp_{1,2}.json` | mock framework | 3/3 PASS |

### 7.2 Wave 2 待增(per ADR-0056 AC-G1~G5)

| AC | 测试类型 | 验证内容 |
|---|---|---|
| AC-G1 | pytest | 调 `rddf_session_hook_entry stage_builder rdd-builder ...` 等 3 种新 kind,断言 `.rddf/state/sessions.json` 含对应 session **且** `.rddf/state/events.jsonl` 含 `event_type=phase_started`。W2.0 前 fail,W2.0 后 pass。 |
| AC-G2 | fixture | 跑完整 arch→planner→builder→verifier→archive,events.jsonl ≥ 20 行 |
| AC-G3 | fixture | 2 stage_X child + 5 events,synthesizer output 含 "X 完成 N/M" |
| AC-G4 | e2e | `rddf monitor --watch=1` 长跑 30s 内至少重渲染 2 次 **且** Panel 5 反映新写入的 event(`last_seen_offset` 由 stage_guide 推进,判据移至 AC-G5) |
| AC-G5 | automated e2e fixture | 开 2 个 owner 跑 guide + rdd-builder,30s 后 last_seen_offset 推进 ≥1 且 guide output 含 builder 进度 |

---

## 8. 与其他 ADR/架构的关系

```
ADR-0017 (rddf-session)
   ↓
ADR-0043 (v4 stage-merge: arch→planner→builder→verifier)
   ↓
ADR-0048 (rdd-builder P0 auto rdd-quick)
   ↓
ADR-0055 (Guide-as-Orchestrator + Cross-Container Event Bus)
   ↓
ADR-0056 (Guide Session 作为唯一交互入口) ← 本文档
   ↓
[Wave 2 in progress]
   ↓
[Wave 3: intent detection + auto-routing]
```

**强依赖**:
- ADR-0055 提供 events.jsonl + stage_guide + polling 机制
- ADR-0017 提供 session lifecycle + owner resolution
- ADR-0043 提供四阶段架构边界

**反向影响**:
- ADR-0056 强制所有 rdd-* SKILL.md 调用 hooks(对 ADR-0048 rdd-quick 例外)
- ADR-0056 定义 G-1~G-4 契约(为未来 intent detection / auto-routing 提供目标)

---

## 9. 维护

### 9.1 更新触发

任一情况发生,**必须**更新本文件:
1. 任何 `guide_entry.sh` / `rddf_session_hooks.sh` / `events_log.py` 改动
2. 任何 rdd-* SKILL.md 改动(hook 调用方式变化)
3. 任何新增 event type
4. 任何 stage kind 新增/移除

### 9.2 同步清单(每次改动)

- [ ] `docs/adr/ADR-0056-*.md` 状态字段
- [ ] `docs/architecture/guide-orchestrator-flow.md`(本文件)
- [ ] `.rddf/improvements/complete-guide-orchestrator-flow.md`
- [ ] `docs/adr/README.md` ADR_INDEX 表
- [ ] `openspec/specs/cross-container-event-bus/spec.md`(如新增 event type)
- [ ] `tests/unit/test_valid_kinds_v4.py`(如新增 kind)
- [ ] `tests/unit/test_hook_invalid_kind.py`(如改 hook 错误处理)
- [ ] `tests/e2e/agent/test_multi_window_poll.bats`(如 polling 行为变)
- [ ] `tests/e2e/agent/scenarios/mwp_*.json`(如场景语义变)