# Workflow Stages

rdd-workflow v4.0+ runs every change through **four stages** in order (per [ADR-0043](../adr/ADR-0043-rdd-workflow-v4-stage-merge.md), superseding the v3.0 five-phase model from [ADR-0034](../adr/ADR-0034-rdd-verifier-verify-phase-architecture.md)).

**v4.0.1 (per [ADR-0048](../adr/ADR-0048-v4-stage-merge-revision.md), 2026-09-09)** introduces three structural refinements to the four-stage model:
1. **rdd-arch 完全脱离 roadmap** (single-gate arch-done; Phase 4 deleted)
2. **rdd-planner 完全接管 roadmap** (new Phase 0 roadmap-bootstrap + Phase 5 dual-gate)
3. **rdd-builder P0 触发 rdd-quick** (5-option HARD pause + recommended_route advisory signal)

Plus **rdd-quick** as a parallel bypass path (per [ADR-0047](../adr/ADR-0047-rdd-quick-bypass-path.md), AMENDED per ADR-0048).

For the complete path diagram and data-flow timeline, see **[v4-pipeline-data-flow.md](v4-pipeline-data-flow.md)** — this doc focuses on role + ownership + gate semantics per stage.

## High-Level Stage Flow (v4.0.1)

```mermaid
graph LR
    A[arch<br/>rdd-arch<br/>slim per ADR-0048] -->|.arch-handoff.json| P[planner<br/>rdd-planner<br/>full roadmap owner]
    P -->|.planner-handoff.json<br/>+recommended_route| B[builder<br/>rdd-builder<br/>6-phase P0-P3<br/>P0 5-option]
    B -->|builder state| V[verifier<br/>rdd-verifier<br/>batch AC check]
    V -->|all pass| ARC[(archived<br/>openspec/changes/archive/)]
    V -.->|fail → bounded retry<br/>max 3 iterations| B
    Q([rdd-quick<br/>bypass path]) -.->|entry (a) from-builder P0<br/>entry (b) direct guide| ARC

    classDef archFill fill:#fef3c7,stroke:#d97706
    classDef plannerFill fill:#dbeafe,stroke:#2563eb
    classDef builderFill fill:#dcfce7,stroke:#16a34a
    classDef verifierFill fill:#f3e8ff,stroke:#9333ea
    classDef quickFill fill:#fee2e2,stroke:#dc2626
    class A archFill
    class P plannerFill
    class B builderFill
    class V verifierFill
    class Q quickFill
```

Each stage:
- Has **one entry skill** (a `rdd-*` skill in v4; the deprecated `guide-*` skills were hard-removed in Wave 3 per [ADR-0044](../adr/ADR-0044-v4-stage-merge-wave3-hard-removal.md)).
- Writes a **handoff file** that the next stage reads.
- Has a **gate** at its exit (warnings + errors per [gates-and-quality.md](gates-and-quality.md)).

`rdd-quick` is a parallel **bypass path** for small, well-scoped changes (per ADR-0047 + ADR-0048 amendment). After ADR-0048, it has **two entry modes**:
- **(a) from rdd-builder P0 选项 5** (主路径): reads `.planner-handoff.json::recommended_route` as the primary advisory signal
- **(b) from `guide` recommender** (旁路): self-triage fallback per original ADR-0047 D1

## Stage 1 — `arch` (slim per ADR-0048)

**Purpose**: define the architecture (ADRs + arch gap analysis only — roadmap is now planner's responsibility).

**Entry skill**: `rdd-arch`.

### v4.0.1 boundary cleanup (per ADR-0048 §Decision 1)

rdd-arch is **completely detached from roadmap** in v4.0.1. The v4.0 arch still owned Phase 4 roadmap-define; v4.0.1 removes it. Roadmap creation + maintenance moves to rdd-planner Phase 0.

| Owned (v4.0.1) | Owned (v4.0, REMOVED) |
|---|---|
| `docs/adr/ADR-*.md` | ~~`roadmap.md`~~ |
| `docs/architecture/*-gap-analysis.md` | ~~`.rddf/roadmap/phases/*.md`~~ |
| `.rddf/state/.arch-handoff.json` | ~~`.rddf/roadmap/features/*.md`~~ |
| | ~~`.rddf/state/.populate-state.json`~~ |

### Single-gate arch-done (per ADR-0048 §Decision 1)

arch-done no longer requires `roadmap.md`. **Only one gate** remains: **ADR ≥ 1**.

```text
arch-done gate: ADR >= 1   (was: ADR >= 1 AND roadmap.md exists)
```

The removed roadmap check is now enforced at **planner-done gate** instead (Phase 5 dual-gate below).

### Inputs / Outputs

- **Inputs**: project state (`.rddf/state/`), `docs/adr/` (read), `roadmap.md` (read-only advisory).
- **Outputs**:
  - New / updated ADRs in `docs/adr/`.
  - Optional gap analysis in `docs/architecture/*-gap-analysis.md`.
  - `.rddf/state/.arch-handoff.json` (ADR-0016 v2 schema, no roadmap fields per ADR-0043).
- **Human load**: high. ADR creation is a deliberate authoring task; arch-done is a hard human gate.

### Sub-skills

- `rdd-env-check` (Phase 1 health snapshot).
- (Removed: `roadmap` sub-skill delegation — moved to rdd-planner).

## Stage 2 — `planner` (full roadmap owner per ADR-0048)

**Purpose**: roadmap + proposal authoring orchestrator. In v4.0.1, planner is the **sole owner of roadmap** (per ADR-0048 §Decision 2). Owns proposal lifecycle (create → review → approve/reject/defer → planner-done) plus roadmap CRUD + sprint governance.

**Entry skill**: `rdd-planner`.

### v4.0.1 expansion (per ADR-0048 §Decision 2)

rdd-planner now has **6 phases** (was 5 in v4.0):

| Phase | v4.0.1 (ADR-0048) | v4.0 (pre-ADR-0048) |
|---|---|---|
| 0 | **roadmap-bootstrap** (NEW) | — (arch owned roadmap) |
| 1 | setup | setup |
| 2 | sprint governance | sprint governance |
| 3 | proposal lifecycle | proposal lifecycle |
| 4 | audit / sync | audit / sync |
| 5 | **planner validation (DUAL-GATE)** | planner validation (single-gate) |

### Phase 0 — roadmap-bootstrap (NEW per ADR-0048)

When user invokes `rdd-planner`:
1. Detect `.rddf/roadmap.md` existence
2. If missing: guide user through `rddf roadmap init` (4 templates per `skills/roadmap/SKILL.md`)
3. After bootstrap succeeds → Phase 1 setup

This ensures roadmap is **always** present before planner work begins (replacing arch's old Phase 4 responsibility).

### Phase 5 — dual-gate planner validation (per ADR-0048 §Decision 2)

planner-done now requires **two gates** (was one):

```text
Gate 1: .rddf/roadmap.md exists
Gate 2: .planner-state.json::recommended_route != "unknown"
```

If either gate fails, `planner_stage_exit.sh` exits 2 with a stderr message identifying the missing gate. Both gates must pass before `.planner-handoff.json` is written.

### `recommended_route` advisory signal (REQUIRED per ADR-0048)

`recommended_route` is now a **required** field in both `planner-state-schema.json` (v1.1) and `planner-handoff-schema.json` (v1.1). It signals to rdd-builder P0 whether the change is suitable for `rdd-quick` fast-path.

Computed by `_lib/planner_sync.py::_compute_recommended_route` heuristic:

- **simple**: all active_projects have priority=P3 AND no complex keywords AND no `_lib/core/`/`_lib/schemas/` involvement
- **complex**: any priority∈{P0,P1} OR touching `_lib/core/`/`_lib/schemas/` OR breaking-change/public-interface keyword
- **unknown**: empty active_projects OR mixed signals (heuristic cannot decide)

Excluded from `state_revision` semantic hash (advisory recompute alone must not bump revision). Excluded from `_lib/planner_handoff.py` FileLock TODO (see KNOWN LIMITATION).

### Inputs / Outputs

- **Inputs**: `.arch-handoff.json` + `proposal-suggestions.md` / `proposal-approved.md`.
- **Outputs**:
  - New `.rddf/improvements/<name>.md` files.
  - Updated `proposal-suggestions.md` / `proposal-approved.md`.
  - Updated `roadmap.md` + `.rddf/roadmap/features/*.md` (NEW in v4.0.1).
  - `.rddf/state/.planner-state.json` (schema v1.1, includes `recommended_route`).
  - `.rddf/state/.planner-handoff.json` (schema v1.1, includes `recommended_route` + `awaiting_builder`).
  - (Optional) feedback channel: `.rddf/state/.planner-feedback.json` (advisory, per [ADR-0042](../adr/ADR-0042-rdd-arch-rdd-planner-bidirectional-feedback.md)).

### Two-tier content review (inherited from v3.0)

- **Tier 1**: `arch_quality_gate.py` — alignment / debt / clarity / actionable.
- **Tier 2**: `change_alignment.py` — refs_valid / no_contradiction / task_traceability.

### Sub-skills

`add-improve`, `rdd-workflow-brainstorm`, `roadmap` (init/edit/validate/advance), `rdd-env-check`.

## Stage 3 — `builder` (5-option P0 per ADR-0048)

**Purpose**: proposal approval + plan generation + execution + archive. v4.0.1 changes **P0 from 4-option to 5-option HARD pause** (per [ADR-0048](../adr/ADR-0048-v4-stage-merge-revision.md) §Decision 3).

**Entry skill**: `rdd-builder`.

### v4.0.1 — P0 5-option (HARD pause, per ADR-0048 §Decision 3)

The P0 approval gate now offers 5 choices (was 4 in v4.0):

```
══════════════════════════════════════════════
rdd-builder Phase 0: Approval Gate (HARD pause, LLM-augmented per ADR-0049)
══════════════════════════════════════════════
变更: <change-name>
Planner advisory: recommended_route = simple|complex|unknown
LLM assessment: simple|complex|unknown (per ADR-0049 Pre-flight Reasoning)
AC 数量: N 个 (from .rddf/improvements/<change>.md ## Acceptance, primary data source)

💡 推荐选项 (per planner advisory + LLM agreement):
   - 三者一致 (advisory=simple AND LLM=simple AND AC ≤ 2)
     → 💡 推荐选项 5 (dispatch-to-quick)
   - LLM=complex 或 advisory=complex
     → 选项 1 (approve) 是常规路径, 仔细评估 LLM concerns
   - LLM 标记 conflict (Agreement: no)
     → 用户应仔细 review LLM concerns 后再决策

1. ✅ approve       → 继续 Phase 1 plan gen
2. ❌ reject        → rddf feedback add --kind rejected (LLM-generated body), exit 0
3. ⏸ defer         → rddf feedback add --kind blocked (LLM-generated body), exit 0
4. 🔄 revise        → rddf feedback add --kind needs-revision (LLM-generated body), exit 1
5. ⚡ dispatch-quick → 转 rdd-quick (per ADR-0047 + ADR-0048)
   + LLM hidden complexity check (per ADR-0049)
   仅当 recommended_route=simple 时启用 (会警告但允许 user override)
══════════════════════════════════════════════
```

### v4.0.2 (planned) — LLM-augmented P0 (per ADR-0049)

Per [ADR-0049](../adr/ADR-0049-rdd-builder-phase0-llm-integration.md), P0 引入 LLM Pre-flight Reasoning：

**LLM 数据源** (per ADR-0049 Decision 4)：
- **PRIMARY**: `.rddf/improvements/<change>.md` 5 段 (Why/What/How/Acceptance/Capabilities)
- **SECONDARY**: `.rddf/state/.planner-handoff.json::recommended_route`
- **TERTIARY**: `.rddf/state/.planner-state.json::active_projects`
- **FALLBACK**: `openspec/changes/<change>/proposal.md` (仅当 improvement 缺失)
- **ALWAYS**: `docs/adr/ADR-*.md` (架构约束检查)

**触发边界** (Decision 1)：
- case 1 approve → ❌ 不调 LLM (用户已显式选择)
- case 2/3/4 → ✅ 调 LLM 生成 feedback body
- case 5 dispatch-quick → ✅ 调 LLM hidden complexity check

**Conflict 兜底** (Decision 3)：
- planner advisory > LLM assessment (advisory 优先)
- `--dispatch-quick` CLI flag 仍要求 `recommended_route=simple` (不变)
- LLM 与 advisory 冲突时 prose 显式标记但不改变 routing
- 用户始终是最终决策者 (HARD pause 不变)

**LLM 输出落点** (Decision 5)：
- Pre-flight → prose 展示 (不入文件)
- case 2/3/4 → `rddf feedback add --body "<LLM-generated>"` → `.rddf/state/.planner-feedback.json`
- case 5 → `.rddf/state/builder/<change>.json::dispatch_quick_review` → rdd-quick P1 读取

**LLM 架构** (Decision 2)：
- executing AI agent IS the LLM (per ADR-0045 模式)
- 无 ANTHROPIC_API_KEY / OPENAI_API_KEY env var
- 无 llm_client 模块 / SDK 依赖
- SKILL.md 用自然语言指示 AI 代理执行 LLM 推理

### Option 5 (dispatch-quick) behavior

When user picks option 5:

1. **Pre-flight LLM hidden complexity check** (per ADR-0049):
   - AI 代理读 `.rddf/improvements/<change>.md` 5 段
   - 检查 `_lib/core/` / `_lib/schemas/` 路径、跨模块、AC 数量、env 依赖
   - 写入 `.rddf/state/builder/<change>.json::dispatch_quick_review`
   - 若 `complexity_confirmed == "complex"`, echo warning 但不阻断
2. **Write context**: `.rddf/state/rdd-quick-context.json` (NEW schema, contains `change_name`, `proposal_path`, `from_builder=true`, `planner_advisory`, `llm_advisory`, etc.)
3. **Write handoff**: `.rddf/state/builder/<change>.json::approval_status="dispatched_to_quick"` + `dispatch_quick_at` timestamp
4. **Delegate**: emit `DISPATCH_TO_QUICK=1 CHANGE_NAME=<change>` marker; orchestrator calls `skill_use("rdd-quick") --from-builder`
5. **Outcome handling** (rdd-quick P4):
   - `completed` → directly `openspec archive <change> --yes` (skipping builder P1-P3)
   - `escalated` → return to builder P0 with options 1-4 (per ADR-0048 amendment; was rdd-planner in pre-amendment ADR-0047)
   - `unverified` → return to builder P0 (similar to escalated)

### `--dispatch-quick` CLI flag

Auto-selects option 5 when `recommended_route=simple` (CI / scripted use case). Refuses to run when `recommended_route != simple` (user must explicitly use the interactive `5` choice to override).

### 6-phase internal state machine (unchanged from v4.0)

```
P0 (5-option approval) → P1 (plan) → P1.5 (deps + exec_mode) → P2 (execute) → P2.5 (review) → P3 (archive with verifier retry)
└─── verifier retry loop (P3 → P1 or P2, max 3) ───┘
```

### Inputs / Outputs

- **Inputs**: `.planner-handoff.json` (now includes `recommended_route` advisory) + `openspec/changes/<name>/` (created during planner approval).
- **Outputs**:
  - 6-phase internal transitions + per-change `.rddf/state/builder/<name>.json` (v1.1: adds `dispatch_quick_at` + `dispatch_quick_outcome` fields).
  - `.rddf/plans/<name>.md` (TDD 5-step plan).
  - Worktree at `.rddf/wt/<name>/` (worktree mode) or commits directly on branch (lightweight mode).
  - `openspec/specs/<name>/spec.md` (when approved proposal includes it).
  - `openspec/changes/archive/<date>-<name>/` on P3 archive.
  - **NEW (v4.0.1)**: `.rddf/state/rdd-quick-context.json` (when option 5 dispatched).

### Hard gates (unchanged from v4.0)

- `archive_gate_check`: worktree branch must have commits; lightweight mode must have ≥1 new commit.
- Post-archive cleanup hook (idempotent).

### Sub-skills

`rdd-workflow-writing-plans` (P1), `execute` (P2), `status` (archive, P3), `feature` (per-feature view), `rddf-session` (binding).

## Stage 4 — `verifier` (per ADR-0034 + ADR-0045)

**Purpose**: before archive, batch-verify all implemented, task-complete, non-archived changes against their acceptance criteria. Classify failures heuristically (`implementation_gap` vs `proposal_drift`). Route failures back to builder with a bounded retry loop (max 3 iterations per change).

**Entry skill**: `rdd-verifier`.

Unchanged from v4.0; v2.0 self-contained LLM verification (per [ADR-0045](../adr/ADR-0045-inline-ac-verifier-into-rdd-verifier.md)) removed the external `ac-verifier` subprocess.

### Inputs / Outputs

- **Inputs**: scan of `openspec/changes/` for `status=implemented + tasks complete + not archived`, plus `.rddf/state/iteration.json` for cycle context.
- **Outputs**:
  - Per-change `.rddf/state/verifier/<change>.json` (loop state, classification history, route, halt reason).
  - Verdict cache at `.rddf/state/.ac-verdict-<name>.json` (SHA-fingerprint, prevents double LLM calls).
  - Audit log at `.rddf/state/verifier/<change>.audit.jsonl` (append-only).
  - Failure classification (`implementation_gap` → builder retry; `proposal_drift` → planner re-evaluate via feedback channel, per ADR-0042).
  - Bounded retry counter, max 3 iterations per change.
  - Final `pass` flag enables archive; `fail` or `halted` flag blocks archive.

### Human load

Low. The executing AI agent is the LLM verifier (per ADR-0045). Human only intervenes when classification is ambiguous or retry budget exhausted.

### Sub-skills

`rdd-doctor --category state` (cross-check handoff consistency).

## Bypass — `rdd-quick` (per ADR-0047, AMENDED per ADR-0048)

**Purpose**: parallel bypass path for small, well-scoped changes that don't warrant the full 4-stage ceremony. Skips `openspec/changes/<name>/` creation and `.rddf/wt/<name>/` worktrees.

**Entry skill**: `rdd-quick`.

### v4.0.1 — two entry modes (per ADR-0048 §Decision 3)

**Entry Mode (a) — from rdd-builder P0 (主路径, NEW in v4.0.1)**:

```bash
skill_use("rdd-quick") --from-builder
# Reads .rddf/state/rdd-quick-context.json (passed from builder P0)
# Reads .planner-handoff.json::recommended_route as P1 primary signal
```

When invoked this way:
- P1 complexity triage **reads `recommended_route` as primary signal** (not self-triage)
- `simple` → only confirm with user (skip Metis/Oracle review)
- `complex` → mandatory Metis + Oracle + user confirm (per ADR-0047)
- `unknown` → fallback to original 5-signal heuristic

**Entry Mode (b) — direct from `guide` recommender (旁路, fallback)**:

```bash
skill_use("rdd-quick")
# Self-triage per ADR-0047 D1 original
```

When invoked this way, original self-triage logic applies (no planner advisory available).

### State machine (P0-P4, modeled on `rdd-verifier` v2.0 self-contained pattern)

- **P0** — plan generation: produces `.rddf/plans/quick-<name>.md` (TDD 5-step + `## Acceptance` checkboxes)
- **P1** — complexity triage: AI agent judges simple vs complex; complex branch triggers Metis + Oracle review
- **P2** — in-place execution: runs on current branch, no worktree
- **P3** — AC verification: from plan `## Acceptance` section, emits verdict JSON matching `rdd-verifier`'s `VERDICT_ITEM_SCHEMA`
- **P4** — completion / retry / escalation: 3-retry cap, then stdout upgrade summary

### v4.0.1 — upgrade contract amendment (per ADR-0048 §Decision 3)

The P4 escalation recommendation **changed from** `skill_use("rdd-planner")` (pre-amendment ADR-0047) **to** `skill_use("rdd-builder")` (post-amendment ADR-0048).

**Reason**: pre-amendment contract created a potential loop `planner → builder → quick → planner`. Post-amendment contract routes the escalation back to the builder P0 5-option (where the user re-decides between options 1-5).

### Hard invariants (enforced by `test_rdd_quick_isolation.bats` sha256 locks)

- MUST NOT create `openspec/changes/<name>/` or `openspec/specs/<name>/`
- MUST NOT create `.rddf/wt/<name>/`
- MUST NOT invoke `git worktree add` or `openspec archive`
- MUST NOT write to `iteration.json` / `sessions.json` / `roadmap-state.json`
- MUST NOT read `openspec/changes/<name>/proposal.md` for AC extraction
- MUST NOT read or write the rdd-builder-reserved env vars (`QUICK_FINISH_DETECTED`, `SKIP_PROMETHEUS_PLANNING`)

### Audit log

`.rddf/state/.quick-history.jsonl` (11-field atomic append). Now also records `dispatched_from_builder` outcome for mode (a) entries.

## Stage Recap (v4.0.1 per ADR-0048)

| Stage | Entry skill | Handoff out | Hard gate(s) | Human load |
|-------|-------------|-------------|---------------|------------|
| arch | `rdd-arch` | `.arch-handoff.json` | arch-done: ADR ≥ 1 (single-gate, no roadmap check) | high |
| planner | `rdd-planner` | `.planner-handoff.json` (v1.1, includes `recommended_route`) | planner-done: roadmap.md exists AND recommended_route ≠ unknown (dual-gate) | medium |
| builder | `rdd-builder` | archive event | per-phase: P0 approval (5-option HARD), P1 plan quality, P1.5 deps, P2 worktree+COMMIT, P2.5 review, P3 archive | medium → low |
| verifier | `rdd-verifier` | (no handoff out — gate to archive) | verify-done: all AC pass + retry ≤ 3 | low |
| _bypass_ | `rdd-quick` | `.quick-history.jsonl` (audit only) | n/a (in-place) | medium |

## Why This Order

Each stage **consumes a contract** the previous stage wrote. A stage cannot start until its predecessor wrote the handoff file (or it falls through to the entry skill to bootstrap the missing stage). This is why a fresh project starts with `guide` (the recommender), which inspects which handoff files exist and routes the user to the earliest missing stage.

The `rdd-quick` bypass deliberately skips the stage chain — it has its own entry contracts (mode a: rdd-quick-context.json; mode b: P0 plan file) and its own audit log (`.quick-history.jsonl`), distinct from the main 4-stage pipeline.

## What Changed in v4.0.1 (ADR-0048)

| Area | Before (v4.0) | After (v4.0.1) |
|------|---------------|------------------|
| **rdd-arch owns** | roadmap.md + .rddf/roadmap/features + .populate-state.json | **none of the above** (transferred to rdd-planner) |
| **rdd-arch Phase 4** | roadmap-define (last phase) | **deleted** |
| **arch-done gate** | ADR ≥ 1 AND roadmap.md exists (dual) | **ADR ≥ 1 only** (single) |
| **rdd-planner phases** | 5 (1-5) | **6** (0 roadmap-bootstrap + 1-5) |
| **rdd-planner Phase 5 gate** | single (state_revision bump) | **dual** (roadmap exists + recommended_route) |
| **recommended_route field** | optional, dead field | **required** (planner-state + planner-handoff schemas v1.1) |
| **rdd-builder P0** | 4-option (approve/reject/defer/revise) | **5-option** (+ dispatch-quick) |
| **rdd-quick entry** | guide only (self-triage) | **guide + builder P0 选项 5** (with planner advisory) |
| **rdd-quick upgrade** | → rdd-planner (loop risk) | **→ rdd-builder P0** (no loop) |
| **rdd-quick-context.json** | does not exist | **NEW** (builder→quick handoff) |

## Cross-references

- **Complete path diagram + data flow timeline**: [v4-pipeline-data-flow.md](v4-pipeline-data-flow.md)
- Loop engine: [loop-engine.md](loop-engine.md) — explains how stages are orchestrated.
- State and events: [state-and-events.md](state-and-events.md) — handoff file format.
- Skills + handoff protocol: [skills-and-handoff.md](skills-and-handoff.md).
- v3 → v4 migration: [../migration-v3-to-v4.md](../migration-v3-to-v4.md) — the full v3 5-phase → v4 4-stage migration map.
