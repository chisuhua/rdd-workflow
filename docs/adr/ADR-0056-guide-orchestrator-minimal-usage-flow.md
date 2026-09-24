# ADR-0056: Guide Session 作为唯一交互入口的最小用法流程

> **状态**: 已采纳
> **日期**: 2026-09-24
> **决策者**: sisyphus (受用户委托起草)
> **依据**: ADR-0017 (rddf-session), ADR-0043 (v4 stage-merge), ADR-0048 (rdd-builder auto-pick), ADR-0055 (Guide-as-Orchestrator Session + Cross-Container Event Bus), ADR-0054 (Objective tracking)
> **版本目标**: v4.2

## Context

### 用户场景(2026-09-24 复盘)

在 OpenCode AI 编程助手上集成 rdd-workflow 时,用户的**真实使用模式**应当收敛为:

> "我**只**和 guide session 交互。guide 看得到我打开的所有窗口的进度,告诉我下一步该做什么。"

这是 v4.1 (`feat-guide-orchestrator-session-event-bus`) 的设计意图,但截至 2026-09-23 audit,生产代码路径上**架构承诺兑现率 ≈ 5%**:

- ✅ 已 ship: events.jsonl + flock + atomic write + 50MB cap + archive (`events_log.py:1-308`)
- ✅ 已 ship: 7 类 phase 事件 schema + hooks 写端 (`rddf_session_hooks.sh:298-505`)
- ✅ 已 ship: `stage_guide` kind + schema v3 (`sessions_schema.json:46,68`)
- ✅ 已 ship: `guide_polling_loop_implementation` (commit `bf6a7fc` / `89117dc`) — polling 循环 + `update_last_seen_offset` API
- ✅ 已 ship: `add-stage-guide-e2e-cross-process-coverage` A+B+C 三层 e2e 验证(REAL-2P-1/2 + MWP-1/2,2026-09-23)
- ❌ **未 ship**: rdd-arch/planner/builder/verifier/quick 的 SKILL.md **未强制** hook 调用
- ❌ **未 ship**: workflow_synthesizer **未消费** events.jsonl(menu 只看 sessions.json,过程不可见)
- ❌ **未 ship**: guide_entry 仅有 on-demand 拉取,**无 background polling**
- ❌ **未 ship**: intent detection (`guide_intent_detected` event 类型已定义但 0 实现)

### 当前 user-perception 落差

| 用户期望 | 真实行为 | 差距来源 |
|---|---|---|
| 我只和 guide 对话 | 必须人工调 rdd-arch/planner/builder/verifier | guide 不自动路由 (P1-2) |
| guide 看得到其他窗口 | 仅在 `guide_entry` 重新调用时 | 无 background polling (W2.3) |
| guide 推进我的 workflow | 仅推荐,不主动驱动 | intent detection 缺失 (P1-1) |
| 多窗口实时同步 | OK(只要 hooks 被调用) | `_VALID_KINDS` 缺 `stage_builder`/`stage_verify`/`stage_quick` + hook 只 catch ConflictError → 静默 (W2.0, ✅ 已修 Step A.1+A.2) |

### 三个层级的边界

```
┌─────────────────────────────────────────────────────────────┐
│ User                                                       │
│   "我打开 OpenCode,说'加 RBAC'"                              │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ OpenCode Window A (Guide session)                            │
│   - AI agent 收到 prompt → 自动 skill_use("guide")           │
│   - guide_entry 渲染 RECOMMEND + 菜单                        │
│   - AI agent 看到 RECOMMEND → 自动 skill_use("rdd-arch")    │
└─────────────────────────────────────────────────────────────┘
                              ↓ (parent_session_id)
┌─────────────────────────────────────────────────────────────┐
│ OpenCode Window B (可选 - 并行)                              │
│   - skill_use("rdd-builder")                                 │
│   - 子 session (kind=stage_builder) 写 events.jsonl          │
└─────────────────────────────────────────────────────────────┘
                              ↓ (shared file bus)
┌─────────────────────────────────────────────────────────────┐
│ .rddf/state/                                                │
│   - sessions.json (rddf-session state)                      │
│   - events.jsonl  (workflow event bus, 50MB cap)            │
└─────────────────────────────────────────────────────────────┘
```

## Decision

### 决策 1: 形式化"guide 作为唯一入口"的最小用法契约

定义"最小用法"必须满足以下 4 条契约(用户可观察的最小行为集合):

#### 契约 G-1: Long-lived orchestrator session
```
stage_guide session 在 $OPENCODE_SESSION_ID 下持续 active,
直到用户显式退出(或 8 小时无 heartbeat 才 orphaned)
```

#### 契约 G-2: 跨窗口 poll 可见
```
Window A 的 guide_entry 必须能 read events.jsonl,
且 last_seen_offset 单调推进(per-owner,不被其他 owner 干扰)
```

#### 契约 G-3: 子阶段自动写事件
```
rdd-arch / rdd-planner / rdd-builder / rdd-verifier / rdd-quick
的入口和出口必须显式调用 rddf_session_hook_entry / _close,
且在 SKILL.md 中明文要求(不只是源码里 hook 存在)
```

#### 契约 G-4: 推荐即路由(短期 AI 手动,长期 guide 自动)
```
短期(v4.2): AI agent 看到 RECOMMEND → 手动调对应 skill
长期(v4.3+): guide 通过 intent detection + auto-routing 自动调用
```

### 决策 2: 实施分三波(已 ship / 进行中 / 未来)

#### Wave 1 — Foundation (已 ship, v4.1 2026-09-22~23)
| 部件 | 文件 | 状态 |
|---|---|---|
| `stage_guide` kind | `_lib/schemas/sessions_schema.json:46` | ✅ |
| `goal.last_seen_offset` | `_lib/schemas/sessions_schema.json:68` | ✅ |
| `events.jsonl` 文件 + flock + 50MB cap | `events_log.py:1-308` | ✅ |
| `rddf_session_hook_entry/close` 写端 | `rddf_session_hooks.sh:298-505` | ✅ |
| `rddf_session_hook_guide_entry/close` 长生命周期 | `rddf_session_hooks.sh:405-505` | ✅ |
| `RddfSessionCoordinator.update_last_seen_offset` API | `_commands.py` | ✅ (2026-09-23 commit `89117dc`) |
| `guide_entry.sh` polling 循环 | `guide_entry.sh:225-229` | ✅ (2026-09-23 commit `bf6a7fc`) |
| 跨进程 e2e 验证 (A+B+C) | `add-stage-guide-e2e-cross-process-coverage` archived 2026-09-23 | ✅ |

#### Wave 2 — Completion (本 ADR 采纳, 串行 11-14 天)
| # | 缺口 | 修复 | 状态 |
|---|----|---|---|---|
| **W2.0** | `_VALID_KINDS` 缺 `stage_builder`/`stage_verify`/`stage_quick` + 关联 schema/heartbeat/parent_kind_map 缺失 + cross-stage 豁免缺失 | `_types.py` enum + `sessions_schema.json` + `HEARTBEAT_TIMEOUT_BY_KIND` + `parent_kind_map` + cross-stage 豁免 | ✅ 已修 (Step A.1, 2026-09-24) |
| **W2.1** | hook entry 块只 catch ConflictError → `RddfSessionError` 静默 traceback | `rddf_session_hooks.sh` entry 块加 `except RddfSessionError → sys.exit(3)` 分支 | ✅ 已修 (Step A.2, 2026-09-24) |
| **W2.2** | workflow_synthesizer 不消费 events.jsonl | `_lib/workflow_synthesizer.py` 读 events,融合 "child X 完成 N/M tasks" 到 menu | pending |
| **W2.3** | guide_entry.sh 无 background polling | 优先扩展既有 `rddf monitor --watch=N` (`monitor_cmd.py:36-61`) 而非新建 guide_entry loop | pending |

#### Wave 3 — Augmentation (未来 1-2 月)
| # | 缺口 | 修复 |
|---|---|---|
| **P1-1** | intent detection | NLP/正则识别用户意图 ("加 RBAC" → rdd-arch) |
| **P1-2** | auto-routing | guide_intent_detected → guide_routed event chain 自动调对应 skill |
| **P1-3** | OpenCode 平台层 OPENCODE_SESSION_ID 注入 | 当前 4 层 fallback,真多窗口需 OpenCode 平台把 session UUID 注入 $OPENCODE_SESSION_ID |
| **P2-1** | background daemon | OpenCode 解锁 promptAsync 后的真正 push 方案 |
| **P2-2** | events 类型未充分使用 | `phase_heartbeat` / `guide_intent_detected` / `guide_routed` / `user_message` 接入生产路径 |
| **P2-3** | cross-repo guide | Hub-Spoke federation 接入 polling 循环 |
| **P2-4** | 历史回放 | `rddf session show --events` 命令 |

### 决策 3: 与 rdd-quick 的关系

`rdd-quick` (per ADR-0047) 是**单窗口、单 owner** 的快速执行路径。它**仍然**通过 guide session 进入,但本身不创建 `stage_guide` 子 session(无长生命周期需求)。当用户从 guide 转 rdd-quick:

```
guide (long-lived stage_guide session)
   ↓
rdd-quick (transient execution, 无 stage_guide child)
   ↓
完成 → 回 guide → 写 phase_completed → guide 下次 poll 看到
```

### 决策 4: 文档与代码同步

**Contract**: 任何 `rddf_session_hook_*` 调用必须满足以下三条之一:
1. SKILL.md **显式**要求 (用户文档级可见)
2. `_lib/` 中函数**自动**调用 (e.g., `RddfSessionCoordinator.create_session` 自动写 phase_started)
3. **rdd-quick 折中**: 仍调 `rddf_session_hook_entry` / `rddf_session_hook_close` 写 `phase_started` / `phase_completed`,**但**不创建长生命周期 child session (单窗口、单 owner 完成即退出)。这保证 guide 窗口能从 events.jsonl poll 到 rdd-quick 的进度,与决策 3 的"完成 → 写 phase_completed → guide 下次 poll 看到"自洽。

**违反任一条即视为架构承诺未兑现**,需立即修复或显式 ADR-0056 例外。

### 决策 5: 与 ADR-0055 的关系

ADR-0055 是 **架构层决策**(创建 stage_guide + events.jsonl)。
ADR-0056 是 **流程层决策**(guide 作为用户唯一入口的契约 + 三波实施)。

ADR-0056 **不** 改变 ADR-0055 的任何 schema / 字段。**仅** 增补:
- 用户视角的 4 条契约 (G-1 ~ G-4)
- 实施路线 (Wave 1/2/3)
- SKILL.md 必须显式调用 hook 的强约束

### 决策 6: 验收标准

Wave 2 完成时,必须满足以下 5 条验收(每条独立可测):

| AC | 描述 | 验证方法 |
|---|---|---|
| AC-G1 | `rddf_session_hook_entry` 调用 builder/verifier/quick 时,session 真的落盘且 events.jsonl 写 phase_started | pytest: 调 `rddf_session_hook_entry stage_builder rdd-builder ...` 3 种 kind 各自断言 `.rddf/state/sessions.json` 含对应 session **且** `.rddf/state/events.jsonl` 含 `event_type=phase_started` + 该 session_id。W2.0+W2.1 前 fail,W2.0+W2.1 后 pass。 |
| AC-G2 | events.jsonl 在生产路径非空 | fixture: 跑完整 arch → planner → builder → verifier → archive,events.jsonl ≥ 20 行 |
| AC-G3 | workflow_synthesizer 输出包含 child 进度 | fixture: 2 个 stage_X child active + 5 events,synthesizer output 含 "X 完成 N/M" |
| AC-G4 | `monitor --watch=N` 模式正确长跑 | e2e: `rddf monitor --watch=1` 长跑 30s 内至少重渲染 2 次 **且** Panel 5 反映新写入的 event(W2.3 优先扩展既有 monitor 而非新建 guide_entry --watch)。**注**: `last_seen_offset` 由 stage_guide 的 `rddf_session_hook_poll_events` 推进(非 monitor);该判据移至 AC-G5(multi-window 可观察)。 |
| AC-G5 | 4 条契约 (G-1~G-4) 全部可观察 | 自动化 e2e fixture:开 2 个 owner 跑 guide + rdd-builder,30s 后 last_seen_offset 推进 ≥1 且 guide output 含 builder 进度 |

## Consequences

### Positive

1. **用户视角收敛**: 用户只与 guide 交互,认知负担降至最低
2. **多窗口协作落地**: Wave 2 完成后,A/B 窗口进度实时可见(前提 OPENCODE_SESSION_ID 不同)
3. **代码-文档一致性**: SKILL.md 强制 hook 调用 + 显式 trap + kind enum 校验闭环 = 不会 "代码有 hook 但 SKILL.md 不说" 或 "hook 调了但 kind 校验吞掉" 导致的 events.jsonl 空

### Negative

1. **W2.0+W2.1 kind-enum+fail-loud 修复工作量**: ~10 行 enum 扩展 + ~20 行 fail-loud = 一次性提交,无回归风险(由 `tests/unit/test_valid_kinds_v4.py` 18 + `test_hook_invalid_kind.py` 14 + `test_ac_g1_red_green.py` 11 测试锁定)
2. **`monitor --watch=N` 扩展复杂度**: 长跑 poll + 用户 Ctrl-C 清理需谨慎(复用既有 `fix-guide-close-owner-resolution` 经验,commit `bf6a7fc`)
3. **workflow_synthesizer 改 schema**: 需确认 events 字段兼容(已有 `.get()` 容错模式,可平滑迁移)

### Mitigations

- **W2.0** kind-enum 修复**仅改 _types.py + sessions_schema.json + heartbeat + 冲突豁免 + parent_kind_map** + 18 个测试锁定(零回归风险)
- **W2.1** hook fail-loud 修复**仅改 rddf_session_hooks.sh entry 块 + import RddfSessionError** + 14 + 11 个测试锁定(零回归风险)
- W2.3 复用 `add-guide-polling-loop-implementation` 的 trap + H7 singleton 经验(commit `bf6a7fc`),**优先扩展**既有 `rddf monitor --watch` 而非新建 `guide_entry --watch`(避免原语重叠)
- W2.2 用 `.get()` 容错,不改 schema

## Rollback

每个 Wave 独立可回滚:

```bash
# Wave 2 回滚
git revert <wave-2-commit>
```

Wave 1 已 ship,无法回滚(除非通过新 ADR 替换)。

如果 Wave 2 完成后用户仍不满意,可:
- 关闭 stage_guide session 创建:`export RDDF_GUIDE_SESSION_ENABLED=false`
- 关闭 events 写入:`export RDDF_EVENTS_LOG_ENABLED=false`
- 回退到 v4.0 之前的 5-stage 架构(per ADR-0044 Wave 3)

## Cross-references

- ADR-0017 rddf-session:用户视角会话
- ADR-0043 v4 stage-merge:四阶段架构
- ADR-0055 Guide-as-Orchestrator + Cross-Container Event Bus:本 ADR 的上游架构决策
- ADR-0054 Objective tracking:跨 sprint 复杂目标(可与 guide 集成)
- ADR-0048 v4 stage-merge revision:rdd-builder P0 自动 rdd-quick(guide 与 rdd-quick 协同)
- spec: `openspec/specs/cross-container-event-bus/spec.md`
- spec: `openspec/specs/add-guide-polling-loop-implementation/spec.md`
- arch: `docs/architecture/guide-orchestrator-flow.md` (本次新建)
- impl: `.rddf/improvements/complete-guide-orchestrator-flow.md` (本次新建)