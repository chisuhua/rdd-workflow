---
优先级: P0
来源: 2026-09-23 audit of feat-guide-orchestrator-session-event-bus — 8 个核心发现中 5 个 P0（核心轮询循环缺失
  / last_seen_offset 无 update API / rdd-* SKILL.md 0 hook 调用）。架构承诺"窗口 A 跑 guide 能看到窗口
  B 跑 rdd-builder 的进度"在生产代码层面完全未落地
阶段: v4.1 follow-up
分类: arch-design
类型: feature
主题: 完整多会话支持
依赖: feat-guide-orchestrator-session-event-bus (已 ship), fix-events-log-blocking-lock
  (已 ship), add-stage-guide-e2e-cross-process-coverage (已 archive)
roadmap_ref:
  project_id: 完整多会话支持
  phase: phase-1
revision_count: 1
last_feedback_id: feedback-20260923-001
last_feedback_at: '2026-09-23T10:10:44+00:00'
feedback_status: needs-revision
---

**优先级**: P0 | **来源**: 2026-09-23 audit
**阶段**: v4.1 follow-up | **分类**: arch-design
**类型**: feature | **主题**: 完整多会话支持
**依赖**: feat-guide-orchestrator-session-event-bus, fix-events-log-blocking-lock, add-stage-guide-e2e-cross-process-coverage
**主题**: 完整多会话支持

> **症状**：feat-guide-orchestrator-session-event-bus 实现了 events.jsonl 事件总线 + fcntl 锁 + 7 类 phase 事件 schema + hooks 写端，但**关键的轮询读端和 last_seen_offset 持久化 API 缺失**。`guide_entry.sh` 完全没有 polling 循环，`RddfSessionCoordinator` 无 `update_last_seen_offset` API，rdd-planner/builder/verifier/quick 的 SKILL.md 0 处提及 hook 调用。
>
> **直接证据**（2026-09-23 audit）：
> ```
> [A] guide session created: rds_9b99ec31a498 ✓
> [A] guide last_seen_offset: 0 ✓
> [B] rdd-arch hook writes 2 events to events.jsonl ✓
> [A] guide reads events via read_since(offset=0): 2 events ✓
> [A] last_seen_offset update: ✗ AttributeError
>     'RddfSessionCoordinator' object has no attribute 'update_last_seen_offset'
> [A] ARCHITECTURE PROMISE: ✗ FAILED
> ```
>
> **架构承诺兑现率 = 0%**（按生产代码路径计）：events.jsonl 永远空着（除非用户手动调用 hook），last_seen_offset 永远 = 0。

## 架构依据

### 已支撑但未连接

feat-guide-orchestrator-session-event-bus 完成了 95% 的支撑部件：

| 部件 | 状态 | 文件 |
|------|------|------|
| `events.jsonl` 文件 + flock + atomic write + 50MB cap + archive | ✅ 完整 | `events_log.py:1-308` |
| `rddf_session_hook_entry` 写 `phase_started` | ✅ 完整 | `rddf_session_hooks.sh:298-313` |
| `rddf_session_hook_close` 写 `phase_completed` | ✅ 完整 | `rddf_session_hooks.sh:374-389` |
| `rddf_session_hook_guide_entry/close` 长生命周期 | ✅ 完整 | `rddf_session_hooks.sh:405-505` |
| `stage_guide` kind schema v3 | ✅ 完整 | `sessions_schema.json:46` |
| `goal.last_seen_offset` 字段 | ✅ 完整 | `sessions_schema.json:68` |
| `monitor_cmd.py` 读 events.jsonl（静态 dashboard） | ✅ 完整 | `monitor_cmd.py:151-188` |
| `rdd-doctor` 校验 events.jsonl | ✅ 完整 | `state_schema_check.py:218-289` |

### 缺失的关键回路

| 缺失部件 | 影响 | 修复位置 |
|---------|------|---------|
| `RddfSessionCoordinator.update_last_seen_offset()` API | guide 无法持久化 poll 进度 | `_commands.py` |
| `guide_entry.sh` polling 循环（read_since → render → update） | guide 看不到 child 进度 | `guide_entry.sh` |
| `rdd-arch/planner/builder/verifier/quick` SKILL.md 文档级 hook 调用 | hooks 几乎不被调用 | 4 个 SKILL.md |
| E2E 真 subprocess 验证 `guide_entry.sh` 读 events.jsonl | AC-9 是 fake pass | rdd-workflow-e2e |

### 修复后架构回路（目标）

```
┌─────────────────────────────────────────────────────────────────────┐
│  Window A (Guide)                                                    │
│                                                                     │
│  skill_use("guide")                                                  │
│       ↓                                                             │
│  guide_entry.sh:                                                    │
│   ├─ rddf_session_hook_guide_entry()  创建 stage_guide session    │
│   ├─ scan_state()                     读 handoff/worktree          │
│   ├─ synthesize()                     读 sessions.json             │
│   ├─ poll_events_since(last_seen_offset) ← 本提案新增              │
│   ├─ render_child_progress(events)   ← 本提案新增                │
│   ├─ update_last_seen_offset()        ← 本提案新增                │
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
- `_commands.py`: 新增 `update_last_seen_offset(session_id, offset)` 方法
- `guide_entry.sh`: 新增 polling 循环（4 步：read → render → update → trap on exit）
- `rdd-arch/SKILL.md`: 文档级 hook 调用（已存在但需明确为强制）
- `rdd-planner/SKILL.md`: **新增** hook 调用文档
- `rdd-builder/SKILL.md`: **新增** hook 调用文档
- `rdd-verifier/SKILL.md`: **新增** hook 调用文档
- `rdd-quick/SKILL.md`: **新增** hook 调用文档
- `tests/unit/test_update_last_seen_offset.py`: 4-6 个单元测试（新建）
- `rdd-workflow-e2e/tests/integration/test_guide_polling_loop_e2e.bats`: 3 个真 subprocess E2E
  - AC-G1: guide 在窗口 A 看到窗口 B 的 events
  - AC-G2: last_seen_offset 单调推进
  - AC-G3: archive 后 last_seen_offset 重置且 guide 重新读全量
- 文档同步：`docs/architecture/multi-session.md` + CHANGELOG.md

### Out Scope
- ❌ 不修改 `events_log.py`（storage 层已完成）
- ❌ 不修改 `rddf_session_hooks.sh` 写端（已完成）
- ❌ 不引入新依赖（用现有 stdlib）
- ❌ 不改 schema（goal.last_seen_offset 字段已存在）
- ❌ 不修改 `monitor_cmd.py`（它是独立的 dashboard，不参与 polling 回路）
- ❌ 不修改 `_lib/cli/` 其他命令
- ❌ 不强制 bash 包装层（非 bash 调用方，如直接调 Python API 的场景，保持可选）

## Why

**为什么 P0**：
1. **架构承诺完全未兑现**：feat-guide-orchestrator-session-event-bus 卖的是"跨 OpenCode 窗口协同"，但生产代码路径走不到 → 用户付费功能 0 价值
2. **死代码风险**：events.jsonl 在生产中永远空着（无 caller 写），last_seen_offset 永远 = 0（无 caller 读），所有写端测试虽然 PASS 但**生产路径不触发**
3. **silent failure**：现有 3032 测试通过给假信心，掩盖架构层未连接的事实
4. **已有基础 95%**：所有部件都在，只缺"导线"——本提案是低成本高收益的最后一步

**为什么不走 rdd-quick**：涉及 4 个新文件 + 4 个 SKILL.md 编辑 + 2 套测试（unit + e2e），规模 > 3 tasks，按 ADR-0047 走完整 rdd-builder 路径。

## What Changes

### 1. `_commands.py` 新增方法

```python
def update_last_seen_offset(self, session_id: str, new_offset: int) -> None:
    """Update goal.last_seen_offset for a stage_guide session (per AC-9).

    Used by guide polling loop: after reading events from offset N to
    current end, advance last_seen_offset to N+len(events). Allows
    next poll to skip already-read events.

    No-op if session is not stage_guide or new_offset <= current.
    Writes sessions.json atomically under FileLock.
    """
    def _do_update():
        data = self._store.read_unlocked()
        for s in data["sessions"]:
            if s.get("session_id") != session_id:
                continue
            if s.get("kind") != "stage_guide":
                raise RddfSessionError(
                    f"Cannot update last_seen_offset on non-stage_guide session "
                    f"(kind={s.get('kind')!r})"
                )
            current = s.get("goal", {}).get("last_seen_offset", 0)
            if new_offset <= current:
                return  # monotonic, no rollback
            s.setdefault("goal", {})["last_seen_offset"] = new_offset
            data["updated_at"] = _now()
            self._store.atomic_write(data)
            return
        raise RddfSessionError(f"Unknown session: {session_id}")
    self._store.with_file_lock(_do_update)
```

### 2. `guide_entry.sh` 新增 polling 块

```bash
# After scan_state + synthesize, BEFORE final print

# v3.1 (add-guide-polling-loop-implementation): polling loop
if type rddf_session_hook_poll_events &>/dev/null; then
  rddf_session_hook_poll_events || true  # best-effort
fi
```

新函数 `rddf_session_hook_poll_events` 在 `rddf_session_hooks.sh` 中定义：

```bash
rddf_session_hook_poll_events() {
  local project_root="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  local owner="${OPENCODE_SESSION_ID:-${RDDF_OWNER:-}}"
  local sessions_file="$project_root/.rddf/state/sessions.json"
  local events_file="$project_root/.rddf/state/events.jsonl"

  # 1. Find this owner's active stage_guide session
  local current_offset=0
  local guide_sid
  PYTHONPATH="$project_root" python3 <<PYEOF
import os, json, sys
sys.path.insert(0, "$project_root")
from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file="$sessions_file")
sess = coord.find_current_binding("$owner")
if sess and sess.kind == "stage_guide":
    print(sess.session_id, sess.goal.get("last_seen_offset", 0))
PYEOF
  read -r guide_sid current_offset
  [[ -z "$guide_sid" ]] && return 0  # no stage_guide, skip

  # 2. Read events since last_seen_offset
  [[ -f "$events_file" ]] || return 0  # no events yet
  local new_count
  new_count=$(PYTHONPATH="$project_root" python3 -c "
import os, sys
sys.path.insert(0, '$project_root')
from skills.rddf_session.scripts.events_log import EventsLog
events = EventsLog('$events_file').read_since(offset=$current_offset)
print(len(events))
for e in events[-10:]:
    print(f\"  {e['ts'][:16]} [{e['event_type']}] {e.get('message', '')[:60]}\")
")

  # 3. Advance last_seen_offset
  if [[ "$new_count" -gt 0 ]]; then
    PYTHONPATH="$project_root" python3 -c "
import os, sys
sys.path.insert(0, '$project_root')
from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file='$sessions_file')
coord.update_last_seen_offset('$guide_sid', $current_offset + $new_count)
"
  fi
}
```

### 3. `rdd-arch/SKILL.md` 强化 hook 文档

现有 line 133-135 已有示例，但需补充为**强制前置步骤**：

```markdown
## Stage 1 Hook（强制前置）

```bash
# 必须先 source hook library（路径相对 skills/rdd-arch/SKILL.md）
source "$(dirname "${BASH_SOURCE[0]:-$0}")/../rddf-session/scripts/rddf_session_hooks.sh"

# 进入阶段前必须调用（写 phase_started 到 events.jsonl）
rddf_session_hook_entry stage_arch rdd-arch "arch-phase" "arch-done" \
    .rddf/state/.arch-handoff.json

# Stage 完成时调用（写 phase_completed）
trap 'rddf_session_hook_close stage_arch arch-done rdd-arch' EXIT INT TERM
```
```

### 4. `rdd-planner/SKILL.md` 新增 Hook 节（同样模板）

```markdown
## Stage 1 Hook（强制前置）

```bash
source "$(dirname "${BASH_SOURCE[0]:-$0}")/../rddf-session/scripts/rddf_session_hooks.sh"
rddf_session_hook_entry stage_design rdd-planner "planner-phase" "design-done" \
    .rddf/state/.planner-handoff.json
trap 'rddf_session_hook_close stage_design design-done rdd-planner' EXIT INT TERM
```
```

### 5. `rdd-builder/SKILL.md` / `rdd-verifier/SKILL.md` / `rdd-quick/SKILL.md` 同上

### 6. 单元测试（新建 `tests/unit/test_update_last_seen_offset.py`）

- `test_update_advances_offset`: 创建 stage_guide @ offset=0 → update to 5 → 验证 sessions.json
- `test_update_rejects_non_stage_guide`: 用 stage_arch session 调用 → raise RddfSessionError
- `test_update_monotonic_no_rollback`: offset=10 → update to 5 → 不变（保持 10）
- `test_update_unknown_session_raises`: session_id 不存在 → raise
- `test_concurrent_update_serializes`: 2 subprocess 并发 update → 最终值是 max(两个值)

### 7. E2E 测试（新建 `rdd-workflow-e2e/tests/integration/test_guide_polling_loop_e2e.bats`）

```bash
# AC-G1: guide 在窗口 A 看到窗口 B 的 events
@test "AC-G1: guide_entry in window A reads events.jsonl from window B's writes" {
    # Setup: FAKE_ROOT with rdd-workflow + symlinked
    # Window B: subprocess that calls rddf_session_hook_entry + writes 3 events
    # Window A: subprocess that sources guide_entry.sh + calls guide_entry --no-binding
    # Assert: window A's output contains the 3 event messages
    # Assert: A's stage_guide.goal.last_seen_offset == 3
}

# AC-G2: last_seen_offset 单调推进
@test "AC-G2: multiple guide_entry calls advance offset monotonically" {
    # Call guide_entry 3 times, write 2 events between each
    # After call 1: offset=2
    # After call 2: offset=4
    # After call 3: offset=6
}

# AC-G3: archive 后 last_seen_offset 重置
@test "AC-G3: after archive_events, guide re-reads from offset 0" {
    # Write 30 events, advance offset to 30
    # Trigger archive (keep=10)
    # Verify offset reset to 0
    # Call guide_entry, verify all 10 events read fresh
}
```

## Acceptance

- [ ] **AC-1**: `RddfSessionCoordinator.update_last_seen_offset(session_id, offset)` 方法存在且工作
- [ ] **AC-2**: `guide_entry.sh` 实际调用 polling 循环（grep 验证 `rddf_session_hook_poll_events` 在 guide_entry.sh 中）
- [ ] **AC-3**: `rdd_session_hook_poll_events` 函数读取 events.jsonl from last_seen_offset 到当前行
- [ ] **AC-4**: `rdd_session_hook_poll_events` 渲染 child session 进度到 stdout
- [ ] **AC-5**: `rdd_session_hook_poll_events` 调用 `update_last_seen_offset` 持久化进度
- [ ] **AC-6**: `rdd-arch/SKILL.md` 显式声明 hook entry/close 为 Stage 1 强制步骤
- [ ] **AC-7**: `rdd-planner/SKILL.md` 新增 hook entry/close 章节
- [ ] **AC-8**: `rdd-builder/SKILL.md` 新增 hook entry/close 章节
- [ ] **AC-9**: `rdd-verifier/SKILL.md` 新增 hook entry/close 章节
- [ ] **AC-10**: `rdd-quick/SKILL.md` 新增 hook entry/close 章节
- [ ] **AC-11**: 单元测试 `test_update_advances_offset` pass
- [ ] **AC-12**: 单元测试 `test_update_rejects_non_stage_guide` pass
- [ ] **AC-13**: 单元测试 `test_update_monotonic_no_rollback` pass
- [ ] **AC-14**: 单元测试 `test_concurrent_update_serializes` pass
- [ ] **AC-15**: E2E AC-G1 pass（guide 真 subprocess 读 events.jsonl）
- [ ] **AC-16**: E2E AC-G2 pass（offset 单调推进）
- [ ] **AC-17**: E2E AC-G3 pass（archive 后 reset + 重新读）
- [ ] **AC-18**: 主仓 `./test.sh --quick` 通过（确认无 regression）
- [ ] **AC-19**: rdd-workflow-e2e `bats tests/` 全绿（42 → 45 cases）
- [ ] **AC-20**: 文档同步（multi-session.md + CHANGELOG.md）

## Capabilities

### MUST

- `update_last_seen_offset` 必须 thread-safe（FileLock）
- `update_last_seen_offset` 必须拒绝非 stage_guide session
- `update_last_seen_offset` 必须保持 monotonic（不 rollback）
- polling 循环必须 best-effort（hook error 不阻塞 guide_entry）
- polling 循环只在 owner 有 active stage_guide session 时才读 events.jsonl
- polling 循环只在 events.jsonl 存在时才读
- guide_entry.sh 必须保留原 scan_state + synthesize 行为（不破坏现有 36 e2e case）
- SKILL.md 的 hook 示例必须 source hooks.sh（不内联代码）

### MUST NOT

- 不修改 `events_log.py`（storage 层不变）
- 不修改 `rddf_session_hooks.sh` 的写端（phase_* 写已实现）
- 不改 `sessions_schema.json`（goal.last_seen_offset 已存在）
- 不强制 hooks 必须在 bash 中调用（Python 用户走 RddfSessionCoordinator API 即可）
- 不引入新依赖
- 不改现有 36 个 rdd-workflow-e2e case 的任何代码
- 不为追求"全自动"而绕过 OPENCODE_SESSION_ID 检查（owner 必须明确）

## Impact

### 收益

- **架构承诺兑现**：feat-guide-orchestrator-session-event-bus 从"95% 部件已就位"变成"端到端可用"
- **跨窗口协同真可用**：用户在窗口 A 跑 guide 能看到窗口 B 跑 rdd-builder 的进度（事件流）
- **测试覆盖完整**：36 → 45 e2e cases，新增 AC-G1/G2/G3 验证真回路
- **死代码激活**：events.jsonl 现在有真实写入 + 真实读取
- **silent failure 消除**：所有"看似 OK"的路径都被新测试覆盖

### 风险

- **回归风险**：guide_entry.sh 改了输出格式（多了 child progress 段），可能影响现有依赖 guide 输出的下游脚本
  - 缓解：child progress 段前缀明显（`📊 Child Sessions:`），易于 grep / parse
- **性能开销**：每次 guide_entry 读 events.jsonl 全文（offset 之后）
  - 缓解：用 last_seen_offset 跳过已读，行数 ≤ 50MB cap
- **owner 解析边界**：rddf_session_hook_guide_entry 用 `_rddf_resolve_owner`（已有缓存 + fallback）
  - 缓解：与原 hook 复用同一 owner 解析

### 依赖

- 上游：feat-guide-orchestrator-session-event-bus（已 ship）
- 上游：fix-events-log-blocking-lock（已 ship，AC-1 依赖 lock + 唯一 ID）
- 上游：add-stage-guide-e2e-cross-process-coverage（已 archive，提供 fixture 模板）
- 同仓：rdd-workflow-e2e（独立仓，需开 PR）

## Feedback

### feedback-20260923-001

- **source**: rdd-builder
- **kind**: needs-revision
- **created_at**: 2026-09-23T10:10:44+00:00
- **resolution**: open

#### Body

## LLM-generated feedback
Concern: AC-14 (test_concurrent_update_serializes) 未实现 — plan Task 1 用 test_update_unknown_session_raises 替代,但 improvement AC-14 明确要求并发 update 序列化测试。范围漂移。
Concern: AC-3/4/5 假覆盖 — test_poll_events_render.py 只 grep 函数存在,未测实际 read_since/render/update 行为 (与 improvement 动机 'AC-9 is fake pass' 相悖)。
Concern: rddf_session_hook_poll_events 未调用 _rddf_resolve_owner — 与其他 hook (entry/close/heartbeat) 的 3-layer owner fallback 不一致。
Severity: warning
Suggested action: P2 修复 — (1) 补 test_concurrent_update_serializes; (2) 强化 test_poll_events_render 为真行为测试; (3) poll_events 调 _rddf_resolve_owner。
Related ADR: ADR-0017 (rddf-session), ADR-0045 (self-contained verification)
