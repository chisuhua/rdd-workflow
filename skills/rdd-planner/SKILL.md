---
name: rdd-planner
description: |
    Roadmap + sprint proposal orchestrator (Stage 2 of v4 architecture).
    Wraps existing `_lib/planner_*.py` lib (per ADR-0037/0038/0042) and adds
    stage entry/exit contract. Per spec 2026-09-04-rdd-workflow-v4-architecture-stage-merge.md
    §3.3 (promotion from horizontal orchestrator to full stage).

    Owns:
    - roadmap.md (完全独占 per ADR-0048, 从 rdd-arch 移交)
    - .rddf/roadmap/{features,phases}/*.md
    - .rddf/state/.populate-state.json
    - improvement-suggestions.md / improvement-approved.md
    - .rddf/improvements/*.md (via add-improve)

    Existing horizontal-orchestrator commands remain available:
    status / sync / feedback / attach / audit / history / advance-sprint

    Stage entry: planner_stage_entry.sh (emits .planner-handoff.json)
    Stage exit: planner_stage_exit.sh (consumes arch-handoff, emits planner-handoff
                with required `recommended_route` field per ADR-0048 §Decision 2)

    Backward compat: legacy .plan-handoff.json::execution_mode_decisions
    is read as fallback in rdd-builder Phase 1.5 during Wave 1 coexistence.
license: MIT
compatibility: requires openspec CLI v1.3.1+, Python 3.11+, git 2.25+
metadata:
  author: rdd-workflow
  version: 2.1
  evolved-from: "guide-design + roadmap"
  user-invocable: true
role:
  title: "Planner (路线图 + 提案治理者)"
  perspective: "Think in terms of roadmap coverage, proposal authoring workflow, and sprint lifecycle. Bridge arch definitions (rdd-arch) with execution (rdd-builder)."
  boundaries:
    owns:
      - "roadmap.md"
      - ".rddf/roadmap/features/*.md"
      - ".rddf/roadmap/phases/*.md"
      - ".rddf/state/.populate-state.json"
      - "improvement-suggestions.md"
      - "improvement-approved.md"
      - ".rddf/improvements/*.md"
      - ".rddf/state/.planner-state.json"
      - ".rddf/state/.planner-feedback.json"
      - ".rddf/state/.planner-handoff.json"
    not_owns:
      - "docs/adr/ADR-*.md"
      - "openspec/changes/<name>/proposal.md"
      - "openspec/changes/<name>/{design,tasks}.md"
      - ".rddf/wt/<name>/"
      - ".rddf/plans/<name>.md"
      - ".rddf/state/builder/<name>.json"
    human_involvement: "medium"
---

> 📖 **术语澄清**: 本 skill 管理的是 **improvement**(改进提案,`.rddf/improvements/<name>.md` 5 段草稿)和 `improvement-suggestions.md` / `improvement-approved.md` 两个索引文件;**不创建 openspec proposal**。openspec proposal 由 rdd-builder P0 创建。详见 [AGENTS.md 关键术语对照表](../../AGENTS.md)。

# rdd-planner Skill

Stage 2 of v4 architecture (per spec §3.3 + ADR-0048 §Decision 2). 4-stage flow:

```
rdd-arch (slim, 单门控 per ADR-0048) → rdd-planner (Phase 0 roadmap-bootstrap + 1-5)
                                       → rdd-builder (P0/P1/P1.5/P2/P2.5/P3) → rdd-verifier
```

> **ADR-0048 (2026-09-09) 关键变更**:
> - 新增 Phase 0 roadmap-bootstrap: 检测 `.rddf/roadmap.md` 缺失 → 引导 `rddf roadmap init`
> - Phase 5 升级为双门控: ① roadmap 存在 ② `.planner-state.json::recommended_route` 已写入
> - `recommended_route` 字段从 optional → required (per fix-v4-rdd-planner-scope-over-assignment AC-13)
> - `.planner-handoff.json` schema v1 → v1.1, 新增 `recommended_route` 字段 (供 rdd-builder P0 dispatch-quick 决策)

## Phase 0: roadmap-bootstrap (NEW per ADR-0048)

**入口条件**: 用户调用 `skill_use("rdd-planner")` 立即执行。

**行为**: 检测 `.rddf/roadmap.md` 是否存在。

**roadmap 存在** → 直接进入 Phase 1 setup。

**roadmap 缺失** → 引导用户走 `rddf roadmap init`:

```
→ roadmap.md 不存在,进入初始化流程
→ 委托 skill_use("roadmap", "init")
  提供 4 模板选择 (per roadmap skill):
  1. C++ 库项目 (基础 → 核心 → 高级)
  2. Web 应用 (MVP → 功能 → 优化)
  3. 空白模板 (自定义)
  4. 基于现有 ADR 生成
→ 用户确认后, .rddf/roadmap.md 创建成功 → Phase 1 setup
```

**关键约束**:
- 任何时刻 `.rddf/roadmap.md` 是 rdd-planner 的**唯一**roadmap 写入入口
- rdd-arch 不再 owns roadmap.md (per ADR-0048 §Decision 1)
- 首次进入项目时, 必须先经过 Phase 0 bootstrap 才能进入 Phase 1

## Entry / Exit Contract

**Stage entry** (run after rdd-arch done):
```bash
bash skills/rdd-planner/scripts/planner_stage_entry.sh [change-name]
# Writes .rddf/state/.planner-handoff.json (schema v1.1, per ADR-0048)
```

**Stage exit** (run before rdd-builder starts):
```bash
bash skills/rdd-planner/scripts/planner_stage_exit.sh [change-name]
# Emits .planner-handoff.json v1.1 with:
#   - proposals_ready
#   - features_active
#   - awaiting_builder
#   - recommended_route (REQUIRED per ADR-0048, enum: simple|complex|unknown)
#   ^^^ 供 rdd-builder P0 dispatch-quick 决策使用
```

**planner-done 双门控** (per ADR-0048 §Decision 2):
- 门控 1: `.rddf/roadmap.md` 存在 (Phase 0/4 必须产出)
- 门控 2: `.planner-state.json::recommended_route` 已写入 (不是 `"unknown"`)

**门控失败**: planner_stage_exit 拒绝写 handoff, 提示用户回 Phase 3 调整.

## Cross-stage feedback channel

Per ADR-0042: planner writes feedback to `.rddf/state/.planner-feedback.json`
(schema `planner-feedback-v1`). Architect (rdd-arch) reads via `rddf arch feedback`
(advisory, read-only).

Per spec §3.5.2 (batch 4): rdd-builder Phase 2 ADR-drift can promote feedback
(kind=ac-fail + ref_change match) to `.planner-feedback.json` via
`_lib/builder_feedback_router.py`. Default ON in v4; architect opt-in via
`rddf planner feedback --accept-builder-source {yes|no}`.

## See also

- `skills/roadmap/` — roadmap CRUD (rddf roadmap add-feature, etc.)
- `skills/add-improve/` — proposal authoring entry
- `_lib/planner_*.py` — Stage 1/2 lib (unchanged)
- `_lib/planner_handoff.py` — NEW in Wave 1: stage handoff r/w
- `skills/rdd-quick/` — bypass-path orchestration for small changes (per ADR-0047, complements but does not replace this skill)

## Phase Exit — Post-Flow Analysis (Agent 平面, ADR-0027 §1.0)

### Checklist (must satisfy exactly one)

- [ ] **Normal exit** → call `orchestrator_finalize` (always, on every exit)
- [ ] **Abnormal exit** → call `orchestrator_finalize` + `rddf report-issue --phase rdd-planner --exit-code <code> "<one-line>"`

### Triggers for "abnormal exit" (non-exhaustive)

- planner-done 双门控失败（`.rddf/roadmap.md` 缺失或 `recommended_route=unknown`）且修复失败
- proposal 反复被同一质量门拒，跨多 phase 阻塞
- state machine branch enters an unexpected case (e.g. recommended_route 状态翻转异常)
- agent cannot continue after 3 retries on the same step
- user explicitly says "this is wrong" while phase reports success

### NOT abnormal (do NOT report-issue)

- User-initiated SIGINT / SIGTERM (exit 130/143)
- Missing tools, network errors, permission errors (environment-error)
- Bad CLI flags, missing required arguments (usage-error)
- planner-done 双门控失败的**首次**失败（提示用户回 Phase 3 调整即可，不立即上报）