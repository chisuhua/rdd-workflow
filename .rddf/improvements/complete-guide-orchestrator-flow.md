---
优先级: P0
来源: 2026-09-24 用户对"guide 作为唯一入口"最小用法的复盘 — ADR-0055 (v4.1) 架构层已落地但流程层契约未形式化,SKILL.md
  不强制 hook 调用导致生产路径 events.jsonl 几乎空,workflow_synthesizer 不消费 events.jsonl 导致 menu
  只看 sessions.json 看不到过程,guide_entry 无 background polling 导致多窗口必须重新调 guide 才看到进度
阶段: v4.2
分类: arch-design
类型: feature
主题: 完整多会话支持
依赖: feat-guide-orchestrator-session-event-bus (已 ship), fix-events-log-blocking-lock
  (已 ship), add-stage-guide-e2e-cross-process-coverage (已 archive), add-guide-polling-loop-implementation
  (已 archive 2026-09-23), fix-guide-close-owner-resolution (已 ship 2026-09-23)
roadmap_ref:
  project_id: 完整多会话支持
  phase: phase-2
revision_count: 1
last_feedback_id: feedback-20260924-001
last_feedback_at: '2026-09-24T04:49:59+00:00'
feedback_status: needs-revision
---

**优先级**: P0 | **来源**: 2026-09-24 用户复盘
**阶段**: v4.2 | **分类**: arch-design | **类型**: feature | **主题**: 完整多会话支持
**依赖**: feat-guide-orchestrator-session-event-bus, fix-events-log-blocking-lock, add-stage-guide-e2e-cross-process-coverage, add-guide-polling-loop-implementation, fix-guide-close-owner-resolution

> **背景**: 用户说"我理解用户只要通过 guide session 作为交互入口,由这个 session 再和其他 rddf session 进行交互推进",并要求梳理这个流程 + 补全需要完成的工作。复盘发现 v4.1 (ADR-0055) 架构层已 100% 落地(events.jsonl + stage_guide + polling + last_seen_offset),但**流程层契约**(用户视角的"guide 是唯一入口")未形式化,**SKILL.md 强约束**(每个 skill 必须显式调 hook)**未实施**,**workflow_synthesizer 未消费 events.jsonl**,**guide_entry 无 background polling**。架构承诺兑现率(按用户可观察行为)= ~5%,按代码完整性 = ~85%。

## 架构依据

### 已支撑但未连接(v4.1 Wave 1 已 ship)

| 部件 | 状态 | 文件 |
|------|------|------|
| `stage_guide` kind + schema v3 | ✅ | `sessions_schema.json:46,68` |
| `events.jsonl` + flock + atomic write + 50MB cap | ✅ | `events_log.py:1-308` |
| `rddf_session_hook_entry/close` 写端 | ✅ | `rddf_session_hooks.sh:298-505` |
| `rddf_session_hook_guide_entry/close` 长生命周期 | ✅ | `rddf_session_hooks.sh:405-505` |
| `guide_polling_loop_implementation` (commit `bf6a7fc`) | ✅ | `guide_entry.sh:225-229` |
| `RddfSessionCoordinator.update_last_seen_offset` (commit `89117dc`) | ✅ | `_commands.py` |
| A+B+C 三层 e2e 验证 (REAL-2P-1/2 + MWP-1/2) | ✅ | `tests/e2e/agent/test_multi_window_poll.bats` |
| `fix-guide-close-owner-resolution` (2026-09-23) | ✅ | `guide_entry.sh:130` `export PROJECT_ROOT` + layer 5 owner fallback |
| `fix-events-log-blocking-lock` (2026-09-23) | ✅ | `events_log.py` 改 blocking flock |

### 缺失的关键回路(v4.2 Wave 2 本提案)

| 缺失部件 | 影响 | 修复位置 |
|---------|------|---------|
| **W2.0(原 P0-1 根因 — kind-enum)**: `_VALID_KINDS` 缺 `stage_builder`/`stage_verify`/`stage_quick` + `sessions_schema.json` enum + `parent_kind_map` + cross-stage 豁免。**已修复于 Step A.1** | `_types.py:28-58` + `sessions_schema.json:46,62-65` + `_commands.py:86-110` (cross-stage 豁免) |
| **W2.1(hook 错误处理 — fail-loud)**: hook entry 块只 catch ConflictError → `RddfSessionError` 静默 traceback | 即使 W2.0 加了 kind,非法 kind/SKILL.md 错误仍难诊断 | `rddf_session_hooks.sh` entry 块加 `except RddfSessionError → sys.exit(3)` 分支。**已修复于 Step A.2** |
| **W2.2**: workflow_synthesizer 不消费 events.jsonl | menu 只看 sessions.json,child 进度不可见 | `_lib/workflow_synthesizer.py` 融合 events |
| **W2.3**: guide_entry.sh 无 background polling | 多窗口必须重新调 guide 才看到进度 | 优先扩展既有 `rddf monitor --watch=N` (`monitor_cmd.py:36-61`) 而非新建 guide_entry loop |

### 修复后架构回路(目标)

```
┌─────────────────────────────────────────────────────────────────────┐
│  Window A (Guide)                                                    │
│                                                                     │
│  skill_use("guide")                                                  │
│       ↓                                                             │
│  guide_entry.sh:                                                    │
│   ├─ rddf_session_hook_guide_entry()  创建 stage_guide session    │
│   ├─ scan_state()                     读 handoff/worktree          │
│   ├─ synthesize()                     读 sessions.json + events   │
│   │                                       (融合 child progress)   │
│   ├─ poll_events_since(last_seen_offset)                            │
│   ├─ render_child_progress(events)   "rdd-builder 完成 3/5 tasks"  │
│   ├─ update_last_seen_offset()                                    │
│   └─ rddf_session_hook_guide_close()  关闭 stage_guide session     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                                  ↕ events.jsonl (fcntl lock)
┌─────────────────────────────────────────────────────────────────────┐
│  Window B (rdd-arch / rdd-builder / rdd-verifier / rdd-quick)        │
│                                                                     │
│  SKILL.md 文档级要求：source hooks.sh + rddf_session_hook_entry/close │
│  → 自动写 phase_started / phase_completed 到 events.jsonl            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## 范围

### In Scope

**W2.0(根因 — kind-enum,✅ 已完成 Step A.1, 2026-09-24)**:`_VALID_KINDS` + `sessions_schema.json` enum + `HEARTBEAT_TIMEOUT_BY_KIND` + `parent_kind_map` + cross-stage 豁免。锁定于 `tests/unit/test_valid_kinds_v4.py` (18 tests)。

**W2.1(hook 错误处理 — fail-loud,✅ 已完成 Step A.2, 2026-09-24)**:`rddf_session_hooks.sh` entry 块加 `except RddfSessionError → sys.exit(3)` 分支(非法 kind/SKILL.md 错误显式失败而非静默 traceback)。锁定于 `tests/unit/test_hook_invalid_kind.py` (14 tests)。

涉及 SKILL.md 文件(均已含 hook+trap,已存在无需新增;W2.0 加固 fail-loud + kind enum 接受):
- `skills/rdd-arch/SKILL.md`
- `skills/rdd-planner/SKILL.md`
- `skills/rdd-builder/SKILL.md`
- `skills/rdd-verifier/SKILL.md`
- `skills/rdd-quick/SKILL.md`(部分豁免,见下)

每文件增加内容(模板,5 个**位置参数**,**不是**命名标志):
```bash
# === rddf-session integration (per ADR-0056) ===
# Hybrid fallback path (per D3): try relative first, fall back to PROJECT_ROOT / global install
_HOOKS_SH="$(dirname "${BASH_SOURCE[0]:-$0}")/../rddf-session/scripts/rddf_session_hooks.sh"
[ -f "$_HOOKS_SH" ] || _HOOKS_SH="${PROJECT_ROOT:-$HOME/.agents/skills}/rddf-session/scripts/rddf_session_hooks.sh"
source "$_HOOKS_SH"

# 入口: <kind> <intent> <subject> <expected_outcome> [context_pointer]
rddf_session_hook_entry stage_${SKILL_NAME} rdd-${SKILL_NAME} "${SUBJECT}" "${EXPECTED_OUTCOME}" "${CONTEXT_POINTER:-}"

# 出口(trap): <kind> <end_reason> <intent>
trap 'rddf_session_hook_close stage_${SKILL_NAME} "${REASON}" rdd-${SKILL_NAME}' EXIT INT TERM
```

修改位置:每个 SKILL.md 的 Implementation 章节开头

**W2.2: workflow_synthesizer 消费 events.jsonl**

修改文件:`_lib/workflow_synthesizer.py`

修改逻辑:
```python
def synthesize(project_root: str) -> Recommendation:
    # 已有: 读 sessions.json → active child sessions
    # 新增: 读 events.jsonl → child progress
    
    active_children = _find_active_children(sessions)
    if active_children:
        events = _read_events_since(
            path=f"{project_root}/.rddf/state/events.jsonl",
            offset=sessions[guide].goal.last_seen_offset
        )
        # 聚合 events → "X 完成 N/M tasks"
        child_progress = _aggregate_progress(active_children, events)
    else:
        child_progress = []  # zero IO path(per ADR-0055 §polling contract)
    
    return Recommendation(
        ...,
        child_progress=child_progress,  # 新字段
    )
```

**W2.3: 监控 `--watch` 模式(优先扩展既有 monitor)**

> **决策 (per Oracle B-section)**:**不**新建 `guide_entry --watch` 模式——`rddf monitor --watch=N` (`_lib/cli/monitor_cmd.py:36-61`) 已存在且已消费 `events.jsonl`。在 monitor 上**扩展**渲染 child progress(聚合 events.jsonl 中 stage_builder/verify/quick 的 phase_started/completed),而非在 guide_entry 加第二个 watch loop(原语重叠、trap 责任模糊)。

修改文件:`_lib/cli/monitor_cmd.py` (扩展,不新建)

扩展模式:
- `--watch=N`(已有,扩展 render): 每 N 秒重读 events.jsonl,渲染"rdd-builder 完成 3/5 tasks"等聚合指标
- `--owner <OPENCODE_SESSION_ID>`(已有): 过滤特定 owner 的 session
- trap EXIT INT TERM 触发 `rddf_session_hook_guide_close`(复用 fix-guide-close-owner-resolution 经验)
- H7 singleton 不变(同一 owner 第二个 watch 返回 existing)

**若监控反馈显示用户在 guide 窗口也想要 polling**:退化为 guide_entry 加 `--watch` 调用 monitor 子进程(而非自实现 loop)。
- zero IO path:无 active child → sleep → 继续

### Out of Scope(留 Wave 3)

- P1-1: intent detection(NLP/正则识别用户意图)
- P1-2: auto-routing(guide 自动调对应 skill)
- P1-3: OpenCode 平台层 `$OPENCODE_SESSION_ID` 注入
- P2-1: background daemon(push 方案)
- P2-2: events 类型接入生产路径(`phase_heartbeat` / `guide_intent_detected` / `guide_routed` / `user_message`)
- P2-3: cross-repo guide(Hub-Spoke federation 接入 polling 循环)
- P2-4: 历史回放(`rddf session show --events`)

### 部分豁免:rdd-quick (per D4 option b)

rdd-quick (per ADR-0047) 是单窗口、单 owner 的快速执行路径。**仍**调 `rddf_session_hook_entry` / `rddf_session_hook_close` 写 `phase_started` / `phase_completed` 到 events.jsonl — 保证 guide 窗口能从 events.jsonl poll 到 rdd-quick 的进度(对齐 ADR-0056 §决策 3)。**不**创建长生命周期 child session(transient,单窗口即退出)。

**但** rdd-quick 仍需要写 phase_started / phase_completed events 到 events.jsonl,让其他窗口的 guide 能看到它。SKILL.md 仍需显式 hook 调用。

## Acceptance

### AC-G1: hook 调用真正落盘 session + events(per AC-G1 in ADR-0056)

**红→绿判据**(修复前 fail, 修复后 pass):

```bash
# 调 hook 三种新 kind 之一
rddf_session_hook_entry stage_builder rdd-builder "subj" "ok"

# 断言 1: sessions.json 含对应 session
$ jq '.sessions[].kind' .rddf/state/sessions.json | grep stage_builder
"stage_builder"

# 断言 2: events.jsonl 含 phase_started 事件
$ jq -r 'select(.event_type=="phase_started") | .context.kind' .rddf/state/events.jsonl | grep stage_builder
stage_builder
```

**W2.0+W2.1 前 fail**(kind enum 拒绝 → `RddfSessionError` 静默 → sessions.json 空 + events.jsonl 空)。**W2.0+W2.1 后 pass**(Step A.1+A.2 已实施)。锁定于 `tests/unit/test_valid_kinds_v4.py` (18 tests) + `tests/unit/test_hook_invalid_kind.py` (14 tests) + `tests/unit/test_ac_g1_red_green.py` (11 tests 端到端 red→green 验证)。

### AC-G2: events.jsonl 在生产路径非空

Fixture 测试:
- 跑完整 arch → planner → builder → verifier → archive 流程
- 期望:`.rddf/state/events.jsonl` 至少 20 行
- 期望:至少 4 个 event_type(`phase_started` × 4, `phase_completed` × 4,等)

### AC-G3: workflow_synthesizer 输出包含 child 进度

Fixture 测试:
- 模拟 2 个 active `stage_X` child(session_id 不同)
- 写 5 events(events.jsonl 含 phase_completed × 3)
- 调 `workflow_synthesizer.synthesize(project_root)`
- 期望:`child_progress` 字段非空
- 期望:`child_progress` 含 "X 完成 N/M" 格式

### AC-G4: guide_entry.sh `--watch` 模式长跑

E2E 测试:
- 启动 `guide_entry --watch --interval 0.3` (background bash &)
- 另起一个 bash & 写 events 到 events.jsonl
- 30 秒内,检查 sessions.json 的 `goal.last_seen_offset` 至少推进 1 次
- kill background bash,确认 sessions.json 的 stage_guide state=completed

### AC-G5: 用户视角 4 条契约全部可观察

Manual 测试(在 PR description 中附):
1. **G-1**: 用户开 OpenCode window A,`skill_use("guide")` → sessions.json 含 1 个 stage_guide active,owner=A
2. **G-2**: 用户开 OpenCode window B(`OPENCODE_SESSION_ID=B`),`skill_use("rdd-arch")` → events.jsonl 含 phase_started;回到 A,`skill_use("guide")` → menu 显示 B 的 progress
3. **G-3**: rdd-arch SKILL.md 含 "rddf_session_hook_entry" 字面量
4. **G-4**: AI agent 看到 RECOMMEND 后自动调对应 skill(短期) / guide 自动调(长期)

## Capabilities

### MUST(M1~M5)

- **M1**: 5 个 rdd-* SKILL.md 必须显式含 `rddf_session_hook_entry` + `rddf_session_hook_close` + `trap` 调用模板(已存在,Step A.1+A.2 加固 fail-loud + kind enum 接受所有 5 个)
- **M2**: `workflow_synthesizer.synthesize()` 返回的 `Recommendation` 必须含 `child_progress` 字段
- **M3**: `rddf monitor --watch=N` 扩展渲染 child progress(优先扩展既有原语,不新建 guide_entry --watch)
- **M4**: 所有改动必须通过 `tests/e2e/agent/test_multi_window_poll.bats` (REAL-2P-1/2) 2/2 PASS
- **M5**: 完整流程(arch→planner→builder→verifier→archive)必须产生 ≥ 20 个 events.jsonl 行

### MUST NOT(MN1~MN3)

- **MN1**: 不修改 ADR-0055 schema(本提案仅扩展消费端)
- **MN2**: 不破坏现有 H7 singleton 行为(stage_guide 与其他 stage 双向不阻塞)
- **MN3**: 不引入新的 event_type(本提案仅消费已定义的 `phase_started` / `phase_completed` / `phase_failed`)

## Impact

### 用户体验

- **提升**: 用户开 2 窗口,A 跑 guide,B 跑 rdd-builder,A **自动**看到 B 进度
- **提升**: workflow_synthesizer 输出更丰富(menu 含 child progress)
- **提升**: `--watch` 模式提供实时 dashboard 体验

### 代码量

| 改动 | 行数 |
|---|---|
| 5 个 SKILL.md | ~150 行(模板化,每文件 ~30 行) |
| `workflow_synthesizer.py` | ~80 行(新增 child_progress 计算) |
| `guide_entry.sh` `--watch` | ~40 行(新模式分支) |
| 新 fixture 测试 | ~100 行(AC-G2/G3/G4) |
| **合计** | **~370 行** |

### 测试影响

- ✅ 既有 `tests/e2e/agent/test_multi_window_poll.bats` (REAL-2P-1/2) 2/2 PASS(无回归)
- ✅ 既有 `tests/e2e/agent/test_multi_window_poll.bats` 3/3 PASS(无回归)
- 🆕 已新增 `tests/unit/test_valid_kinds_v4.py` (18 tests, 锁 W2.0 kind-enum)
- 🆕 已新增 `tests/unit/test_hook_invalid_kind.py` (14 tests, 锁 W2.1 fail-loud)
- 🆕 已新增 `tests/unit/test_ac_g1_red_green.py` (11 tests, 锁 AC-G1 端到端 red→green)
- 🆕 待新增 `tests/integration/test_workflow_synthesizer_events_integration.py`(AC-G3)
- 🆕 待新增 `tests/integration/test_monitor_watch_child_progress.bats`(AC-G4)

### 文档影响

- 🆕 `docs/adr/ADR-0056-guide-orchestrator-minimal-usage-flow.md`(主 ADR)
- 🆕 `docs/architecture/guide-orchestrator-flow.md`(完整流程架构)
- 🆕 `.rddf/improvements/complete-guide-orchestrator-flow.md`(本文件)
- 🔧 `docs/adr/README.md` ADR_INDEX 表(新增 ADR-0056)
- 🔧 `docs/architecture/multi-session.md` Cross-Container Event Bus 章节(per Wave 2 进展)

### 风险

- **R1**: SKILL.md 改错导致 hook 调用失败 → mitigation: 模板化 + grep 测试兜底
- **R2**: workflow_synthesizer 改 schema 破坏消费者 → mitigation: `.get()` 容错,不破坏既有 schema
- **R3**: `--watch` 长跑进程难调试 → mitigation: 复用 `fix-guide-close-owner-resolution` 的 trap 经验

## 实施路线(分三波)

### Wave 1(已 ship, 2026-09-22~23)

```
feat-guide-orchestrator-session-event-bus           [ship]
fix-events-log-blocking-lock                       [ship]
add-stage-guide-e2e-cross-process-coverage         [archive 2026-09-23]
add-guide-polling-loop-implementation              [archive 2026-09-23]
fix-guide-close-owner-resolution                   [ship 2026-09-23]
```

### Wave 2(本提案, 串行 11-14 天 / 并行 2 人错误见 B-W2)

```
W2.0: kind-enum 根因修复 + 关联 schema/heartbeat/parent_kind_map [1 天, ✅ 已完成 Step A.1]
       锁定于 tests/unit/test_valid_kinds_v4.py (18 tests)
W2.1: hook fail-loud 修复                      [1 天, ✅ 已完成 Step A.2]
       锁定于 tests/unit/test_hook_invalid_kind.py (14 tests) + test_ac_g1_red_green.py (11 tests)
W2.2: workflow_synthesizer 融合 events        [2 天]   → AC-G3
W2.3: 决策 + 实现 --watch 模式                 [3 天]   → AC-G4
       (优先扩展既有 rddf monitor --watch 而非新建 loop)
W2.4: fixture 测试 + 完整流程 events ≥ 20     [2 天]   → AC-G2
W2.5: rdd-builder P0 + archive + regress       [1 天]   → AC-G5
```

> **原 W2.1 (5 SKILL.md 加显式 hook,旧编号) 已删除** — 5 个 SKILL.md 全部已含 hook+trap (per `tests/unit/test_skill_md_hook_doc.py` AC-6~10);真根因是 W2.0 (kind enum 拒绝 builder/verify/quick),已修。注:本编号体系下"W2.1 = fail-loud"(与旧编号语义不同,因 arch doc §6.2 采用 W2.0=kind-enum + W2.1=fail-loud 拆分;以 arch doc 为准)。

> **串行依赖**: W2.0 → W2.1 → W2.2 → W2.3 → W2.4 → W2.5。W2.1 需要 W2.0 的 kind enum 先修;W2.2 需要 W2.1 的 fail-loud 路径确定;W2.3 需要 W2.2 的 synthesizer 输出。"2 人并行 7 天" 假设错误(W2.1 占用 fail-loud 而非原 5-SKILL-md 工作,且依赖链串行)。

总耗时:**~10 天串行**(W2.0+W2.1 已 2 天完成,剩 W2.2~W2.5 约 8 天)。无并行捷径。

### Wave 3(未来 1-2 月,需单独 ADR)

```
W3.1: intent detection(P1-1)
W3.2: auto-routing(P1-2)
W3.3: OpenCode 平台层 OPENCODE_SESSION_ID 注入(P1-3)
W3.4: background daemon + push 方案(P2-1)
W3.5: 接入 4 个未用 event_type(P2-2)
W3.6: cross-repo guide(P2-3)
W3.7: 历史回放命令(P2-4)
```

## 关联

- ADR-0055: Guide-as-Orchestrator Session + Cross-Container Event Bus(架构层)
- ADR-0056: Guide Session as 唯一交互入口(流程层 — 与本提案同步起草)
- spec: `openspec/specs/cross-container-event-bus/spec.md`
- spec: `openspec/specs/add-guide-polling-loop-implementation/spec.md`
- arch: `docs/architecture/guide-orchestrator-flow.md`
- proposal: `openspec/changes/complete-guide-orchestrator-flow/`(rdd-builder P0 批准后)

## Feedback

### feedback-20260924-001

- **source**: human
- **kind**: needs-revision
- **created_at**: 2026-09-24T04:49:59+00:00
- **resolution**: resolved

#### Body
- **resolved_at**: 2026-09-24T06:39:23+00:00
- **resolved_by**: human