---
name: rdd-planner
description: |
  Stage 2 of v4 architecture (rdd-arch → rdd-planner → rdd-builder → rdd-verifier).
  Improvement authoring / review / approve + proposal lifecycle.

  Invoke when canonical preconditions hold:
    1. rdd-arch arch-done emitted `.rddf/state/.arch-handoff.json`
    2. New improvement needed OR existing improvement in `improvement-suggestions.md` to review

  Default: auto-decision per ADR-0050; writes `.rddf/state/.planner-handoff.json` at stage exit.

  Boundary ownership: see role.boundaries.owns / not_owns.
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
      - ".rddf/roadmap/objectives/*.md"
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

## Stage 1 Hook（强制前置步骤, per add-guide-polling-loop-implementation AC-7）

进入 Planner 阶段前必须调用 hooks，写 `phase_started` 到 `events.jsonl` 让 guide session 可观察：

```bash
source "$(dirname "${BASH_SOURCE[0]:-$0}")/../rddf-session/scripts/rddf_session_hooks.sh"

# 进入前 (写 phase_started)
rddf_session_hook_entry stage_design rdd-planner "planner-phase" "design-done" \
    .rddf/state/.planner-handoff.json

# 阶段完成时 (写 phase_completed, INT/TERM/EXIT 均触发)
trap 'rddf_session_hook_close stage_design design-done rdd-planner' EXIT INT TERM
```

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

## Objectives 治理（跨 sprint 复杂目标跟踪，per ADR-0054）

rdd-planner owns `.rddf/roadmap/objectives/*.md`（**唯一写入方**，per ADR-0028 role boundary + ADR-0054 D5）。Objective 是跨 sprint 复杂目标（多 feature + 多 openspec change 协同）的 source-of-truth 工件，与 feature fragment（derived view，零手工）互补。

### 何时建 feature vs objective

| 场景 | 用 |
|------|----|
| 跨 phase 聚合当前状态（零手工、自动派生） | **feature fragment** (`rddf roadmap add-feature`) |
| 跨 sprint 目标叙事 + 复盘台账 + deferral rationale | **objective** (`rddf roadmap add-objective`) |
| 纯单 change 改进 | **improvement** 5 段草稿 → rdd-builder P0 |
| 单 change 执行视角 | **openspec change** |

### 写入门控

- objective 文件写入权 **仅 rdd-planner**；builder / execute / verifier **不写** objective 文件
- stage exit 自动刷新 `AGENTS.md` `<!-- AUTO: objectives -->` 哨兵段（planner_stage_exit.sh 内嵌，与 feature fragments 同模式）
- sprint 复盘仪式: `bash skills/rdd-planner/scripts/planner_objective_revise.sh <id> --kind sprint-review --content "..." --decision "..." --reason "..."`
- §11 台账 append-only；kind ∈ {deferral-rationale, go-decision, sprint-review, scope-change, adr-amendment}
- deferred objective 的 §10 允许 `N/A — <理由>`，禁止静默留空
- review_by 默认 created + 90 天；grace 到期由 `rddf doctor --category objective-lifecycle` 告警

### 参考

- `skills/roadmap/` — objective CLI（list/show/add/revise/archive/deps/snapshot）
- `docs/adr/ADR-0054-objective-tracking.md` — 完整决策 + 4 工件区分矩阵

## Objective-Aware Planning Guidance（v1.2, per add-objective-aware-planner）

**触发**：进入 rdd-planner Phase 1 setup 时，AI agent 必须先**主动检查活跃 objective 状态**，再决定本阶段的 proposal 起草与推荐。

**数据源（priority order）**：
1. **PRIMARY**: `.rddf/state/.planner-handoff.json::active_objectives`（每 stage entry/exit 自动写入，含每个 active/deferred objective 的 `id/priority/status/review_by/theme/next_sprint_candidates`）
2. **FALLBACK**: `bash skills/roadmap/scripts/objective_show.sh <id>`（per-objective 详细视图，含 §10 next_sprint_candidates checklist）

### LLM 推理任务

每个 active objective 的 `next_sprint_candidates` 是 LLM 推荐的**候选任务**——agent 必须：
- 评估该候选是否对应**用户当前问题/上下文**
- 评估该候选是否**已部分推进**（读 `.rddf/improvements/` 中是否存在同名草稿）
- 输出 **recommended_actions** 列表（≤3 个，附 objective id + 候选文本 + 推进建议：起草新草稿 / 复用现有草稿 / 延后）

### 行为契约（prompt-not-auto）

**严禁自动生成 improvement 草稿**——违反 objective D5 role boundary（planner 不写 openspec proposal）。Agent 必须：
- 推荐候选后**明确提示用户**：「该候选可作为下一个 improvement，建议走 `skill_use("add-improve")` HARD-GATE 起草」
- 用户确认后，agent **手动委托** `skill_use("add-improve")` —— 这是另一 skill 的入口，不在 rdd-planner 直写路径
- 若 objective `status: deferred`，提示「deferred 中，跳过；如需激活请先 `skill_use("rdd-planner")` 走 §11 台账登记 deferral-rationale 决策」

### 输出格式（prose 中）

```
=== Objective-Aware Plan (per add-objective-aware-planner) ===
Active objectives: N | Deferred: M
  - [objective-onboard-new-skill] (P1 active, review_by 2026-12-21)
    主题: 新增 skill 的标准化 onboarding 流程
    Candidates: 3
      • 起草 add-skill-onboarding 入口 SKILL.md + 5 段 improvement 草稿 — 推进建议: 起草新草稿 (skill_use("add-improve"))
      • 复用 add-improve/SKILL.md 的 pre_create_brainstorm_check.sh HARD-GATE — 推进建议: 复用现有草稿
      • 与 rdd-env-bootstrap 的 guided-fix 阶段对接 — 推进建议: 延后 (依赖 rdd-env-bootstrap v0.x 立项)
  - [objective-bypass-audit-hub-governance] (P2 deferred, review_by 2026-12-21)
    主题: 统一 bypass audit + hub federation governance
    Candidates: 0 (deferred — N/A — 维持 v3.2 deferred 决策)

🤖 Recommended action (this turn): 起草 add-skill-onboarding 草稿 (走 add-improve HARD-GATE)
```

### 与现有 4 工件区分矩阵的关联

| 维度 | objective | improvement | feature fragment | openspec change |
|------|-----------|-------------|------------------|-----------------|
| scope | 跨 sprint 复杂目标 | 单 change 改进提案 | 跨 phase proposal 分组 | 单 change 执行视角 |
| 数量 | 少（~2） | 多（~248） | 中（~5） | 多（archive 累计） |
| LLM 推荐 | **prompt-not-auto**（rdd-planner 读 + 推荐） | 直接生成 | 派生视图（无手工） | builder P0 |
| 写入门控 | rdd-planner（仅） | rdd-planner / add-improve | rdd-arch / rdd-planner | rdd-builder |

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