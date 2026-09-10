# v4 Pipeline Data Flow Timeline (ADR-0048)

> **Source of truth** for the v4.0.1 four-stage pipeline + bypass path, post [ADR-0048](../adr/ADR-0048-v4-stage-merge-revision.md) (2026-09-09).
>
> Companion to [workflow-phases.md](workflow-phases.md) (role + ownership + gate semantics per stage). This doc focuses on:
> 1. **Complete path diagram** — full visual topology of all entries, exits, handoffs, decision points
> 2. **Stage-by-stage data flow timeline** — what flows where, when, in what format
> 3. **Advisory signal pipeline** — how `recommended_route` propagates from heuristic to rdd-quick

For the role model, role.boundaries.owns lists, and sub-skill catalog, see [workflow-phases.md](workflow-phases.md). For handoff JSON schemas, see [state-and-events.md](state-and-events.md) and [skills-and-handoff.md](skills-and-handoff.md).

---

## 1. Complete Path Diagram (v4.0.1)

```mermaid
flowchart TD
    User([User / AI agent])
    Guide[guide<br/>状态扫描推荐器<br/>无状态]

    subgraph Stage1["Stage 1: arch (slim per ADR-0048)"]
        ArchSkill[rdd-arch SKILL<br/>Phase 1-5<br/>单门控 arch-done]
    end

    subgraph Stage2["Stage 2: planner (full roadmap owner per ADR-0048)"]
        PlannerSkill[rdd-planner SKILL<br/>Phase 0-5<br/>双门控 planner-done]
        RoadmapInit[rddf roadmap init<br/>4 模板]
        SyncHeuristic[_compute_recommended_route<br/>heuristic]
    end

    subgraph Stage3["Stage 3: builder (5-option P0 per ADR-0048)"]
        BuilderSkill[rdd-builder SKILL<br/>P0-P3 6-phase]
        Phase0[phase0_approval.sh<br/>5-option HARD pause<br/>case 5: dispatch-quick]
    end

    subgraph Stage4["Stage 4: verifier (per ADR-0034+0045)"]
        VerifierSkill[rdd-verifier SKILL<br/>批量 AC 验证<br/>≤3 重试]
    end

    subgraph Bypass["Bypass: rdd-quick (per ADR-0047, AMENDED per ADR-0048)"]
        QuickSkill[rdd-quick SKILL<br/>P0-P4<br/>entry (a) from-builder / (b) direct]
    end

    %% User -> Guide
    User -->|skill_use guide| Guide

    %% Guide -> any stage
    Guide -->|⭐ 1 rdd-arch| ArchSkill
    Guide -->|⭐ 2 rdd-planner| PlannerSkill
    Guide -->|3 rdd-builder| BuilderSkill
    Guide -->|4 rdd-verifier| VerifierSkill
    Guide -->|5 rdd-quick| QuickSkill

    %% arch -> planner (handoff)
    ArchSkill -->|.arch-handoff.json<br/>schema v3| PlannerSkill

    %% planner internal
    PlannerSkill -.->|检测 .rddf/roadmap.md 缺失| RoadmapInit
    RoadmapInit -.->|创建 roadmap.md| PlannerSkill
    PlannerSkill -.->|rddf planner sync --apply| SyncHeuristic
    SyncHeuristic -.->|.planner-state.json<br/>recommended_route| PlannerSkill

    %% planner -> builder (handoff)
    PlannerSkill -->|.planner-handoff.json v1.1<br/>+ recommended_route| Phase0

    %% builder P0 5-option
    Phase0 -->|1 approve| BuilderSkill
    Phase0 -->|2 reject| FeedbackAction1[rddf feedback add<br/>--kind rejected]
    Phase0 -->|3 defer| FeedbackAction2[rddf feedback add<br/>--kind blocked]
    Phase0 -->|4 revise| FeedbackAction3[rddf feedback add<br/>--kind needs-revision]
    Phase0 -->|5 dispatch-quick<br/>recommended_route=simple| QuickSkill

    %% builder -> rdd-quick (mode a)
    Phase0 -->|.rddf/state/rdd-quick-context.json<br/>+ builder-handoff<br/>  approval_status=dispatched_to_quick| QuickSkill
    Phase0 -->|DISPATCH_TO_QUICK=1<br/>CHANGE_NAME=x| Orchestrator
    Orchestrator[/Orchestrator<br/>检测 marker<br/>调 skill_use/]
    Orchestrator -->|skill_use rdd-quick --from-builder| QuickSkill

    %% builder internal
    BuilderSkill -->|P1 → P1.5 → P2 → P2.5 → P3| VerifierSkill
    BuilderSkill -.->|.rddf/state/builder/change.json<br/>v1.1 + dispatch_quick_* fields| BuilderSkill

    %% verifier -> archive or retry
    VerifierSkill -->|all AC pass| Archive[(openspec archive<br/>changes/archive/)]
    VerifierSkill -.->|fail / retry ≤3| BuilderSkill

    %% rdd-quick internal
    QuickSkill -.->|P0 plan gen<br/>.rddf/plans/quick-x.md| QuickSkill
    QuickSkill -.->|P1 complexity triage<br/>planner-handoff::recommended_route| QuickSkill
    QuickSkill -.->|P2 in-place execute<br/>无 worktree| QuickSkill
    QuickSkill -.->|P3 AC verify<br/>verdict JSON| QuickSkill
    QuickSkill -->|P4 outcome=completed| Archive
    QuickSkill -.->|P4 outcome=escalated<br/>回到 builder P0 重新决策<br/>per ADR-0048 amendment| Phase0
    QuickSkill -.->|P4 outcome=unverified| Phase0

    %% Cross-stage feedback (advisory, per ADR-0042)
    PlannerSkill -.->|.planner-feedback.json<br/>advisory read-only| ArchSkill
    BuilderSkill -.->|Phase 2 ADR-drift detection<br/>rddf feedback add --kind ac-fail<br/>routed via builder_feedback_router| PlannerSkill

    classDef userFill fill:#f1f5f9,stroke:#475569
    classDef archFill fill:#fef3c7,stroke:#d97706
    classDef plannerFill fill:#dbeafe,stroke:#2563eb
    classDef builderFill fill:#dcfce7,stroke:#16a34a
    classDef verifierFill fill:#f3e8ff,stroke:#9333ea
    classDef quickFill fill:#fee2e2,stroke:#dc2626
    classDef handoffFill fill:#f0f9ff,stroke:#0284c7
    class User userFill
    class ArchSkill archFill
    class PlannerSkill plannerFill
    class BuilderSkill,Phase0 builderFill
    class VerifierSkill verifierFill
    class QuickSkill quickFill
    class Orchestrator,FeedbackAction1,FeedbackAction2,FeedbackAction3 userFill
```

### Path diagram legend

- **Solid arrows**: control flow (skill calls, handoff file writes, dispatch markers)
- **Dashed arrows**: data flow (handoff JSON files read/written, feedback channels)
- **Yellow box (rdd-arch)**: arch stage (v4.0.1 slim — no roadmap)
- **Blue box (rdd-planner)**: planner stage (v4.0.1 full roadmap owner)
- **Green box (rdd-builder)**: builder stage (v4.0.1 P0 5-option)
- **Purple box (rdd-verifier)**: verifier stage (unchanged from v4.0)
- **Red box (rdd-quick)**: bypass path (v4.0.1 two entry modes)

---

## 2. Stage-by-Stage Data Flow Timeline

This section walks through the **happy path** end-to-end, step by step. All file paths are relative to project root.

### Stage 1 — rdd-arch

```
[Step 1.1] User: skill_use("rdd-arch")
[Step 1.2] rdd-arch SKILL.md:
          - rddf_session_hook_entry stage_arch  (ADR-0017 rddf-session bind)
          - arch_env_check (Phase 1 setup)
[Step 1.3] Phase 2 adr-create: create ADR-NNNN-slug.md (kebab-case, ≤ 50 chars)
[Step 1.4] Phase 3 architecture: optional gap analysis in docs/architecture/
[Step 1.5] Phase 5 arch validation: SINGLE GATE (per ADR-0048)
          check: ls $PROJECT_ROOT/docs/adr/ADR-*.md | grep -v template | wc -l >= 1
[Step 1.6] Phase 6 arch-done:
          - write_arch_handoff.py writes .rddf/state/.arch-handoff.json
            (schema v3 per ADR-0043; NO roadmap fields)
          - rddf_session_hook_close stage_arch
          - prints: "💡 Next: skill_use('rdd-planner')"
[Step 1.7] ⚠️ MANUAL SWITCH (per AGENTS.md L597):
          User must explicitly invoke rdd-planner.
          arch does NOT auto-call planner.
```

**Files written by rdd-arch**:
- `docs/adr/ADR-NNNN-*.md` (new / updated)
- `docs/architecture/*-gap-analysis.md` (optional)
- `.rddf/state/.arch-handoff.json` (schema v3)

**Handoff output** (`.arch-handoff.json` v3):
```json
{
  "schema": "arch-handoff-v3",
  "version": 3,
  "owner": "rdd-arch",
  "adr_dir": "docs/adr",
  "adr_pattern": "ADR-*.md",
  "architecture_dir": "docs/architecture",
  "discovered": {
    "adr_files": ["ADR-0001", "ADR-0002", ...],
    "gap_analyses": [...]
  },
  "arch_complete_revision": 12
}
```

**NOT written by rdd-arch (per ADR-0048 §Decision 1)**:
- ❌ `roadmap.md`
- ❌ `.rddf/roadmap/{features,phases}/*.md`
- ❌ `.rddf/state/.populate-state.json`

---

### Stage 2 — rdd-planner

```
[Step 2.1] User: skill_use("rdd-planner")
[Step 2.2] Phase 0 roadmap-bootstrap (NEW per ADR-0048):
          - check: test -f .rddf/roadmap.md
          - if MISSING: skill_use("roadmap", "init")
            choose 1 of 4 templates:
              - C++ 库项目 (基础 → 核心 → 高级)
              - Web 应用 (MVP → 功能 → 优化)
              - 空白模板 (自定义)
              - 基于现有 ADR 生成
          - after init success → Phase 1 setup
[Step 2.3] Phase 1 setup:
          - rddf_session_hook_entry stage_planner
          - read .arch-handoff.json as input
[Step 2.4] Phase 2 sprint governance:
          - rddf planner advance-sprint [--to-sprint X]
          - writes .rddf/state/.planner-history.jsonl
[Step 2.5] Phase 3 proposal lifecycle:
          - rddf planner attach <name> --project-id X --phase Y [--theme Z]
            (single-file, idempotent; per ADR-0038 Stage 2.5 P0-3)
          - writes .rddf/improvements/<name>.md frontmatter
          - writes proposal-suggestions.md / proposal-approved.md tables
          - optional: rddf feedback add <name> --kind ...
[Step 2.6] Phase 4 audit / sync:
          - rddf planner sync --apply
            reads .rddf/improvements/*.md, .rddf/roadmap.md (AUTO-SPRINT block)
            writes .rddf/state/.planner-state.json
            writes .rddf/roadmap.md AUTO-SPRINT block (delegated to _lib.roadmap_sprint)
            runs _compute_recommended_route heuristic
[Step 2.7] Phase 5 planner validation: DUAL GATE (per ADR-0048 §Decision 2)
          Gate 1: test -f .rddf/roadmap.md
          Gate 2: jq -r .recommended_route .planner-state.json != "unknown"
          if BOTH pass → planner-done
[Step 2.8] Phase 6 planner-done:
          - bash skills/rdd-planner/scripts/planner_stage_exit.sh <change-name>
            reads RECOMMENDED_ROUTE from planner-state
            writes .planner-handoff.json (schema v1.1)
            env vars: PROPOSALS_READY, PROPOSALS_APPROVED_COUNT,
                       FEATURES_ACTIVE, CURRENT_SPRINT, AWAITING_BUILDER,
                       RECOMMENDED_ROUTE (NEW per ADR-0048)
          - rddf_session_hook_close stage_planner
          - prints: "💡 Next: skill_use('rdd-builder') (or 'rdd-quick' if simple)"
[Step 2.9] ⚠️ MANUAL SWITCH:
          User must explicitly invoke rdd-builder.
```

**Files written by rdd-planner**:
- `.rddf/roadmap.md` (NEW in v4.0.1 — was arch's job)
- `.rddf/roadmap/features/*.md` (NEW in v4.0.1)
- `.rddf/improvements/<name>.md` (new / updated via planner_attach)
- `proposal-suggestions.md` / `proposal-approved.md`
- `.rddf/state/.planner-state.json` (schema v1.1, includes `recommended_route`)
- `.rddf/state/.planner-history.jsonl`
- `.rddf/state/.planner-feedback.json` (optional, per ADR-0042)
- `.rddf/state/.planner-handoff.json` (schema v1.1)

**Handoff output** (`.planner-handoff.json` v1.1):
```json
{
  "schema": "planner-handoff-v1",
  "version": 1,
  "owner": "rdd-planner",
  "planner_complete_at": "2026-09-09T10:00:00Z",
  "current_sprint": "sprint-2026-09",
  "proposals_ready": ["change-foo", "change-bar"],
  "proposals_approved_count": 0,
  "features_active": ["feat-x"],
  "awaiting_builder": ["change-foo"],
  "recommended_route": "simple"   // NEW per ADR-0048 §Decision 2 (REQUIRED)
}
```

---

### Stage 3 — rdd-builder (5-option P0 per ADR-0048)

```
[Step 3.1] User: skill_use("rdd-builder")
[Step 3.2] P0 approval gate: 5-option HARD pause (per ADR-0048 §Decision 3)

          ┌─────────────────────────────────────────────────────────────────┐
          │ rdd-builder Phase 0: Approval Gate (HARD pause)                  │
          ├─────────────────────────────────────────────────────────────────┤
          │ 变更: change-foo                                                  │
          │ Planner advisory: recommended_route = simple                      │
          │ AC count: 2 (from proposal.md ## 验收标准)                         │
          │                                                                    │
          │ 💡 Planner advisory=simple + AC ≤ 2 → option 5 recommended       │
          │                                                                    │
          │ 1. approve       2. reject       3. defer       4. revise       5. dispatch-quick │
          └─────────────────────────────────────────────────────────────────┘

          Read input (1-5) from user (or --auto-approve / --dispatch-quick)

[Step 3.3] P0 case 1 (approve):
          - bash phase0_approval.sh change-foo
            reads proposal.md (or generates via generate_full_proposal.py
            from .rddf/improvements/<change>.md per ADR-0025 D1/D2)
            writes .rddf/state/builder/change-foo.json
              approval_status = "approved"
              current_phase = "phase-1"
            exit 0
[Step 3.4] P0 case 2/3/4: rddf feedback add (single-writer per ADR-0037)
          - case 2: rejected (exit 0, no archive)
          - case 3: blocked   (exit 0, no archive)
          - case 4: needs-revision (exit 1)
          - **NEW per ADR-0049**: AI agent reads .rddf/improvements/<change>.md 5 段,
            generates LLM feedback body with Concern/Severity/Suggested action/Related ADR,
            then invokes rddf feedback add --body "<LLM-generated>"
[Step 3.5] P0 case 5 (dispatch-quick, NEW per ADR-0048 §Decision 3):
          - bash phase0_approval.sh change-foo --dispatch-quick
          - read .planner-handoff.json::recommended_route
            warn-but-continue if != "simple" (user override path)
          - **NEW per ADR-0049**: AI agent reads .rddf/improvements/<change>.md 5 段,
            generates LLM dispatch_quick_review JSON:
              {
                complexity_confirmed: "simple|complex|unknown",
                concerns: ["bullet", ...],
                suggested_action: "proceed|escalate",
                reviewed_at: <ISO>,
                data_source: "<absolute path of improvement file>"
              }
            Writes to .rddf/state/builder/change-foo.json::dispatch_quick_review
            (via env-var pattern, per Oracle C1)
          - phase0_approval.sh reads dispatch_quick_review from builder-handoff,
            emits warning if complexity_confirmed=="complex" but does NOT block
            (HARD pause = user is final decision-maker)
          - NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
          - write .rddf/state/rdd-quick-context.json:
              {
                "change_name": "change-foo",
                "proposal_path": "openspec/changes/change-foo/proposal.md",
                "from_builder": true,
                "dispatched_at": <NOW>,
                "expected_outcome": "completed",
                "planner_advisory": {
                  "recommended_route": "simple",
                  "rationale": "planner-handoff.json::recommended_route at dispatch time"
                },
                "llm_advisory": {                    // NEW per ADR-0049
                  "complexity_confirmed": "complex",
                  "concerns": "data migration",
                  "rationale": "builder-handoff::dispatch_quick_review at dispatch time"
                },
                "ac_count": 2
              }
          - write .rddf/state/builder/change-foo.json:
              approval_status = "dispatched_to_quick"
              dispatch_quick_at = <NOW>
          - emit marker: "DISPATCH_TO_QUICK=1 CHANGE_NAME=change-foo"
          - exit 0

          ➡️ Orchestrator sees marker → skill_use("rdd-quick") --from-builder
              → jumps to Stage 4: rdd-quick (Bypass)
              → rdd-quick P4 outcome handling:
                  completed  → openspec archive change-foo --yes (skip P1-P3)
                  escalated  → back to P0 case 1-4
                  unverified → back to P0 case 1-4

[Step 3.6] P1 plan generation (case 1 path):
          - bash phase1_plan.sh change-foo
          - call rdd-workflow-writing-plans (TDD 5-step plan)
          - validate _lib.plan_quality.evaluate_plan
            exit 2 if FAIL
          - write openspec/changes/change-foo/tasks.md
          - write .rddf/plans/change-foo.md

[Step 3.7] P1.5 deps + execution_mode:
          - bash phase1_5_deps.sh change-foo
          - call _lib.builder_deps.decide_execution_mode (worktree vs lightweight)
            reads .planner-handoff.json::recommended_route (NEW advisory usage)
            file_count / task_count / risk_keywords
          - write .rddf/state/builder/change-foo.json::execution_mode_decision
          - exit 6 if STRICT_DEPS_GATE fails

[Step 3.8] P2 worktree + execute:
          - bash phase2_execute.sh change-foo
          - COMMIT GATE: artifacts (proposal.md, tasks.md, plan.md) committed
          - select_worktree.sh (worktree mode) OR direct commit (lightweight)
          - execute TDD 5-step from .rddf/plans/change-foo.md
          - writeback tasks.md checkboxes via execute/scripts/tasks_writeback.sh
          - exit 3 if COMMIT GATE fails

[Step 3.9] P2.5 review (HARD pause, 4-option):
          - bash phase2_5_review.sh change-foo
          - 4-option: merge / revise / abandon / archive
          - exit 5 if revise/abandon

[Step 3.10] P3 archive:
          - bash phase3_archive.sh change-foo
          - pre-call rdd-verifier (per ADR-0035)
            verifier verdict: 0=pass / 1=impl_gap / 2=ac_fail / 3=needs_human / 4=halted
            back-route: 1→P2 / 2→P1 (max 3 retries per change)
          - openspec archive change-foo --yes
          - post-archive cleanup: archive.sh + post_archive_cleanup.sh
          - exit 4 if verifier halted; exit 7 if archive gate fails
```

**Files written by rdd-builder (main path, case 1)**:
- `openspec/changes/<change>/proposal.md` (via generate_full_proposal.py or skeleton)
- `openspec/changes/<change>/tasks.md`
- `openspec/specs/<change>/spec.md` (if proposal includes it)
- `.rddf/state/builder/<change>.json` (per-change state, v1.1)
- `.rddf/plans/<change>.md`
- `.rddf/wt/<change>/` (worktree mode only)

**Files written by rdd-builder (case 5 dispatch-quick)**:
- `.rddf/state/rdd-quick-context.json` (NEW schema per ADR-0048)
- `.rddf/state/builder/<change>.json::approval_status="dispatched_to_quick"`
- `.rddf/state/builder/<change>.json::dispatch_quick_at` (timestamp)

**Builder-handoff schema v1.1 (per-change)**:
```json
{
  "schema": "builder-handoff-v1",
  "version": 1,
  "owner": "rdd-builder",
  "change_name": "change-foo",
  "current_phase": "phase-0|phase-1|phase-1.5|phase-2|phase-2.5|phase-3",
  "approval_status": "pending|approved|rejected|deferred|revising|dispatched_to_quick",
  "plan_quality_status": "pending|valid|invalid",
  "execution_mode_decision": {"mode": "worktree|lightweight", "reason": "..."},
  "deps_status": {"blockers": [...], "manual_deps": [...], "cross_repo_pending": [...]},
  "worktree_path": "/abs/path/.rddf/wt/change-foo",
  "branch": "openspec/change-foo",
  "execution_status": "pending|running|failed|completed",
  "review_status": "pending|merge|revise|abandon",
  "retry_count": 0,
  "max_retries": 3,
  "retry_history": [...],
  "phase_pause_history": [...],
  "archive_status": "pending|verifying|archived|failed",
  "verifier_report_path": ".rddf/state/.verifier-report.json",
  "dispatch_quick_at": "2026-09-09T...",        // NEW per ADR-0048
  "dispatch_quick_outcome": "completed|escalated|unverified",  // NEW
  "updated_at": "..."
}
```

---

### Bypass: rdd-quick (per ADR-0047, AMENDED per ADR-0048)

#### Entry Mode (a) — from rdd-builder P0 (主路径, NEW per ADR-0048)

```
[Step 4a.1] Orchestrator sees DISPATCH_TO_QUICK=1 marker
[Step 4a.2] Orchestrator: skill_use("rdd-quick") --from-builder
[Step 4a.3] rdd-quick reads .rddf/state/rdd-quick-context.json (from P0)
[Step 4a.4] P0 plan generation:
          - SKIP scaffold (use existing proposal.md from planner attach)
          - generate quick-<change>.md template from proposal.md ## Acceptance
[Step 4a.5] P1 complexity triage (NEW per ADR-0048 §Decision 3):
          - READ .planner-handoff.json::recommended_route as PRIMARY signal
            simple  → confirm with user, skip Metis/Oracle review
            complex → mandatory Metis + Oracle + user confirm (per ADR-0047)
            unknown → fallback to original 5-signal heuristic
[Step 4a.6] P2 in-place execute (NO worktree):
          - run on current branch
          - run TDD 5-step from .rddf/plans/quick-<change>.md
          - update plan file checkboxes (NOT tasks.md)
          - git commit on current branch when done
[Step 4a.7] P3 AC verify:
          - read AC from .rddf/plans/quick-<change>.md ## Acceptance
          - DO NOT read openspec/changes/<change>/proposal.md for AC
          - emit verdict JSON (rdd-verifier VERDICT_ITEM_SCHEMA format)
[Step 4a.8] P4 outcome handling:
          - completed → append .rddf/state/.quick-history.jsonl line
                        outcome=completed
                        ➡️ Orchestrator: openspec archive <change> --yes
                          (SKIPS builder P1-P3 entirely)
          - escalated → append history line outcome=escalated
                        ➡️ Back to rdd-builder P0 case 1-4 (per ADR-0048 amendment)
          - unverified → similar to escalated (P0 case 1-4)
[Step 4a.9] Builder-handoff dispatch_quick_outcome updated:
          - rdd-builder (orchestrator) writes
            .rddf/state/builder/change.json::dispatch_quick_outcome = <outcome>
```

#### Entry Mode (b) — direct from guide (旁路, fallback per ADR-0047 D1)

```
[Step 4b.1] User: skill_use("rdd-quick") directly (no builder P0)
[Step 4b.2] Agent confirms kebab-case name with user
[Step 4b.3] P0: bash skills/rdd-quick/scripts/scaffold_plan.sh --name X --proposal "..."
          - writes .rddf/plans/quick-X.md with TDD 5-step + ## Acceptance
          - user MUST edit plan file with concrete TDD step bodies + AC bullets
[Step 4b.4] P1: self-triage per ADR-0047 original (5-signal heuristic)
[Step 4b.5] P2: in-place execute
[Step 4b.6] P3: AC verify
[Step 4b.7] P4: append .quick-history.jsonl line outcome=completed/escalated/unverified
          - completed → exit (no openspec archive; user may optionally do it)
          - escalated → stdout upgrade summary recommending
                        skill_use("rdd-builder") (per ADR-0048 amendment;
                        was skill_use("rdd-planner") in pre-amendment ADR-0047)
```

**Audit log schema v1** (`.quick-history.jsonl` 11-field atomic append):
```json
{
  "name": "quick-<name>",
  "started_at": "2026-09-07T10:00:00Z",
  "ended_at": "2026-09-07T10:25:00Z",
  "plan_file": ".rddf/plans/quick-<name>.md",
  "complexity": "simple|complex",
  "reviewed_by": ["metis", "oracle"],
  "verdict_summary": {"total": 3, "pass": 3, "fail": 0},
  "retry_count": 0,
  "outcome": "completed|escalated|unverified",
  "commit_sha": "abc1234",
  "upgraded_to_change": null,
  "dispatched_from_builder": true  // NEW per ADR-0048 (only set in mode a)
}
```

---

### Stage 4 — rdd-verifier

```
[Step 5.1] User: skill_use("rdd-verifier")
[Step 5.2] scan openspec/changes/ for status=implemented + tasks complete + not archived
[Step 5.3] for each qualifying change:
          - read openspec/changes/<change>/proposal.md ## 验收标准
          - read .rddf/state/.ac-verdict-<change>.json (SHA-fingerprint cache)
          - if cache miss → run LLM verification (self-contained per ADR-0045)
          - classify: implementation_gap (→P2 retry) | ac_fail (→P1 retry) | needs_human (halt)
          - retry_count += 1; if > max_retries (3) → halt exit 4
[Step 5.4] write .rddf/state/verifier/<change>.json (loop state + history)
[Step 5.5] append .rddf/state/verifier/<change>.audit.jsonl (audit log)
[Step 5.6] final pass flag → enable archive; fail/halted → block archive
```

**Files written by rdd-verifier**:
- `.rddf/state/verifier/<change>.json`
- `.rddf/state/.ac-verdict-<change>.json` (cache)
- `.rddf/state/verifier/<change>.audit.jsonl`

---

## 3. Advisory Signal Pipeline (`recommended_route` flow)

```
planner_sync.discover_projects (reads .rddf/improvements/*.md)
        │
        ▼
planner_sync.render_state (computes active_projects array)
        │
        ▼
planner_sync._compute_recommended_route (heuristic)
        │   priority P0/P1 → "complex"
        │   priority P3 + _lib/core/_lib/schemas_ mention → "complex"
        │   breaking-change/public-interface keyword → "complex"
        │   priority P3 + no complex keywords → "simple"
        │   empty active_projects → "unknown"
        ▼
planner_state.json (schema v1.1, recommended_route REQUIRED)
        │
        ▼
planner_stage_exit.sh (reads planner-state, writes handoff)
        │ env var RECOMMENDED_ROUTE
        ▼
planner-handoff.json (schema v1.1, recommended_route REQUIRED)
        │
        ▼
builder P0 (reads planner-handoff.json::recommended_route)
        │
        ├─ if simple → 💡 hint + dispatch-quick recommended
        │
        ▼
[user picks option 5]
        │
        ▼
phase0_approval.sh writes rdd-quick-context.json with
planner_advisory.recommended_route = "simple"
        │
        ▼
rdd-quick P1 (mode a, reads planner-handoff.json::recommended_route)
        │
        ├─ simple  → confirm with user, skip Metis/Oracle
        ├─ complex → mandatory Metis + Oracle + user confirm
        └─ unknown → fallback 5-signal heuristic
```

**Data integrity contract**:
- `recommended_route` is excluded from `_lib/planner_state.py` `_SEMANTIC_HASH_EXCLUDE` (advisory recompute alone does NOT bump `state_revision`)
- `recommended_route` is excluded from `.planner-state.json` content checksums
- `recommended_route` change does NOT trigger `_lib/roadmap_sprint.update_roadmap` re-render (AUTO-SPRINT block unchanged)

---

## 4. Stage Transition Reference Table

| Transition | Trigger | Mechanism | File(s) read | File(s) written |
|------------|---------|-----------|--------------|------------------|
| User → Guide | `skill_use("guide")` | bash + json output | `.rddf/state/*.json`, `openspec/changes/`, `roadmap.md` | (none — read-only) |
| Guide → rdd-arch | `skill_use("rdd-arch")` | user choice | project state | rddf-session entry |
| rdd-arch (Phase 1-5) | internal phases | bash menu | existing `docs/adr/` | `docs/adr/ADR-*.md` |
| rdd-arch → rdd-planner | arch-done gate pass | `write_arch_handoff.sh` | `docs/adr/ADR-*.md` (gate check) | `.rddf/state/.arch-handoff.json` |
| rdd-planner (Phase 0) | entry to planner | bash detection | `.rddf/roadmap.md` exists? | (none, or `roadmap.md` if init) |
| rdd-planner (Phase 1-5) | internal phases | bash menu + rddf planner * | `.arch-handoff.json`, `.rddf/improvements/*.md` | `.rddf/state/.planner-state.json`, etc. |
| rdd-planner → rdd-builder | planner-done dual-gate pass | `planner_stage_exit.sh` | `.planner-state.json` (gate check) | `.rddf/state/.planner-handoff.json` |
| rdd-builder P0 case 1 | user picks 1 (approve) | `phase0_approval.sh` | `openspec/changes/<change>/proposal.md` | `.rddf/state/builder/<change>.json` |
| rdd-builder P0 case 5 | user picks 5 (dispatch-quick) | `phase0_approval.sh` | `.planner-handoff.json` (recommended_route) | `.rddf/state/rdd-quick-context.json` + builder-handoff |
| rdd-builder P0 → P1 | case 1 (approve) | internal state machine | `.rddf/state/builder/<change>.json` | (same file updated) |
| rdd-builder P3 → openspec archive | archive_gate pass | `archive.sh` | worktree commits, tasks.md | `openspec/changes/archive/<date>-<name>/` |
| rdd-builder P3 ↔ rdd-verifier | verifier verdict routing | `_lib/builder_retry.py` | `.rddf/state/verifier/<change>.json` | `.rddf/state/builder/<change>.json::retry_count` |
| rdd-quick mode (a) entry | orchestrator sees marker | orchestrator decision | `DISPATCH_TO_QUICK=1` marker | (calls rdd-quick) |
| rdd-quick P4 → builder P0 | outcome=escalated/unverified | upgrade contract (per ADR-0048 amendment) | `.rddf/state/.quick-history.jsonl` | `.rddf/state/builder/<change>.json::dispatch_quick_outcome` |
| rdd-quick P4 → openspec archive | outcome=completed | `openspec archive <change> --yes` | `.rddf/state/.quick-history.jsonl` | `openspec/changes/archive/<date>-<name>/` |
| rdd-planner → rdd-arch (advisory) | `rddf arch feedback` | read-only | `.planner-feedback.json` | (none) |
| rdd-builder → rdd-planner (advisory) | Phase 2 ADR-drift detection | `rddf feedback add --kind ac-fail` + builder_feedback_router | worktree commits vs ADR assumptions | `.planner-feedback.json` |

---

## 5. Failure Modes & Recovery

| Failure | Detection | Recovery |
|---------|-----------|----------|
| rdd-arch: no ADR exists | arch-done gate fails | user goes back to Phase 2 adr-create |
| rdd-planner: no roadmap.md | Phase 0 bootstrap | Phase 0 detects + runs `rddf roadmap init` |
| rdd-planner: recommended_route=unknown | Phase 5 gate 2 fails | user runs `rddf planner sync --apply` to recompute |
| rdd-planner: roadmap exists but planner-state missing | Phase 5 gate 1 passes, gate 2 fails (no planner-state at all) | user runs `rddf planner status` to bootstrap empty state with `recommended_route=unknown` |
| rdd-builder P0: recommended_route != simple but user picks 5 | warn-but-continue | `.rddf-quick-context.json.planner_advisory.rationale` records user override |
| rdd-builder P0 (per ADR-0049): LLM dispatch_quick_review detects "complex" | phase0_approval.sh case 5 emits warning | user already chose 5; HARD pause preserved; `forced_by_user=true` recorded |
| rdd-builder P0 (per ADR-0049): LLM disagrees with planner advisory | prose marks `Agreement: no` | routing unchanged (advisory priority); user reviews LLM concerns before decision |
| rdd-builder P0 (per ADR-0049): improvement file missing | AI agent reports missing primary data source | user must run `rddf planner attach <change>` first to create improvement 5-段 |
| rdd-quick P1: planner-handoff missing | mode (a) entry | falls back to mode (b) self-triage |
| rdd-quick P2: needs worktree but can't | TDD step fails | abort, escalate to builder P0 |
| rdd-verifier: implementation_gap | verdict = 1 | back-route to builder P2 (retry, max 3) |
| rdd-verifier: ac_fail | verdict = 2 | back-route to builder P1 (retry, max 3) |
| rdd-verifier: needs_human | verdict = 3 | halt, exit 4, user must intervene |
| rdd-verifier: retry budget exhausted | retry_count > 3 | halt, exit 4 |

---

## 6. Cross-references

- **Per-stage role + ownership + gate semantics**: [workflow-phases.md](workflow-phases.md)
- **State and events**: [state-and-events.md](state-and-events.md) — handoff JSON schemas
- **Skills + handoff protocol**: [skills-and-handoff.md](skills-and-handoff.md)
- **Loop engine**: [loop-engine.md](loop-engine.md)
- **Gates and quality**: [gates-and-quality.md](gates-and-quality.md)
- **Multi-session**: [multi-session.md](multi-session.md) — rddf-session lifecycle
- **Extension points**: [extension-points.md](extension-points.md) — how to add new skills/ADRs
- **ADR-0048**: [../adr/ADR-0048-v4-stage-merge-revision.md](../adr/ADR-0048-v4-stage-merge-revision.md)
- **ADR-0049**: [../adr/ADR-0049-rdd-builder-phase0-llm-integration.md](../adr/ADR-0049-rdd-builder-phase0-llm-integration.md) (LLM-augmented P0)
- **ADR-0043**: [../adr/ADR-0043-rdd-workflow-v4-stage-merge.md](../adr/ADR-0043-rdd-workflow-v4-stage-merge.md) (baseline v4 architecture)
- **ADR-0047**: [../adr/ADR-0047-rdd-quick-bypass-path.md](../adr/ADR-0047-rdd-quick-bypass-path.md) (rdd-quick original design, AMENDED per ADR-0048)
