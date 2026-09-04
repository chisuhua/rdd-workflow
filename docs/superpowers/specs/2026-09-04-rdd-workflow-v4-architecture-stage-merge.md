# rdd-workflow v4 Architecture: Stage Merge Proposal — Design

**Date**: 2026-09-04
**Status**: Draft (awaiting user review)
**Author**: brainstorming session output (Sisyphus orchestration)
**Supersedes (partially)**: D2a ("no design/plan merge") from `docs/superpowers/specs/2026-09-03-rdd-planner-stage1-feedback-contract.md` §1
**Extends (additive, no conflict)**:
- `docs/superpowers/specs/2026-09-03-rdd-planner-stage1-feedback-contract.md` (Stage 1, feedback contract)
- `docs/superpowers/specs/2026-09-03-rdd-planner-stage2-design.md` (Stage 2, planner status/sync)
- ADR-0037 (feedback contract)
- ADR-0038 (rdd-planner horizontal orchestrator, Stage 2)
- ADR-0041 (planner sprint lifecycle)
- ADR-0042 (rdd-arch rename + planner bidirectional feedback)
- ADR-0034 (rdd-verifier 5th phase)
- ADR-0035 (verifier-archive-gate boundary)

## 1. Problem & Motivation

### 1.1 Observed state (after Stage 1/2/3 implementation)

Per git log analysis (commit `69f1b05` is the most recent on master, 2026-09-03):

| Component | Status | Reference |
|---|---|---|
| `rdd-arch` (renamed from `guide-arch`) | ✅ Implemented | ADR-0042, commit `c6e7628` |
| `rdd-planner` lib (`_lib/planner_*.py`) | ✅ Implemented as horizontal orchestrator | ADR-0038, commit `acdb356` |
| `rdd-planner` SKILL.md / `skills/rdd-planner/` | ❌ Missing (only `_lib/` + CLI) | This spec §3.3 |
| `rddf planner` CLI subcommand | ✅ Implemented (`planner_cmd.py`) | commit `acdb356` |
| `rdd-verifier` 5th phase | ✅ Implemented | ADR-0034 |
| `guide-design` / `guide-plan` / `guide-ship` | ✅ Still active (3 separate skills) | D2a |

### 1.2 Gaps that justify proposing v4 stage merge

1. **5-phase cognitive load**: arch → design → plan → ship → verify (5 gates, 5 hand-offs, 5 stages). For small changes (1-2 file edits), this overhead is disproportionate to the work.
2. **`rdd-planner` is a phantom skill**: 6 `_lib/planner_*.py` modules + CLI exist but no `skills/rdd-planner/SKILL.md` for user-facing skill discovery. Users hit `rddf planner status` without a corresponding skill wrapper.
3. **Roadmap injection in `rdd-arch`** (per `_lib/gate.py:155-160`): `_check_roadmap_defined` couples arch-done gate to roadmap existence, blurring the boundary. Per user's first ask: split.
4. **Three sequential phase skills (`guide-design` → `guide-plan` → `guide-ship`)** all share worktree/iteration.json/proposal.md as coupling points but each emits its own handoff file. After Stage 3, design-handoff + plan-handoff + (no ship-handoff) creates a fragmented handoff chain.

### 1.3 Goal

Collapse the 5-phase architecture into a **4-stage architecture** with cleaner role boundaries:

```
v3.0+ (current):  arch → design → plan → ship → verify     [5 phases]
v4.0 (proposed):  rdd-arch → rdd-planner → rdd-builder → rdd-verifier  [4 stages]
```

- **rdd-arch** (simplified): ADR + arch docs ONLY (no roadmap injection).
- **rdd-planner** (promoted from horizontal to full stage): owns roadmap + proposal authoring + feature fragments.
- **rdd-builder** (NEW, 3-in-1): proposal approval gate + plan generation + worktree + execute + archive.
- **rdd-verifier** (unchanged): batch AC verification per ADR-0034.

### 1.4 Out of scope (explicit)

- ❌ Removing `rdd-verifier` or merging it elsewhere (per user decision Q2 = "保持独立第 4 阶段").
- ❌ Modifying `rdd-planner` Stage 1/2 contracts (feedback_appender, feedback_resolver, planner_state, planner_sync, planner_feedback, planner_attach, planner_audit, planner_history).
- ❌ Renaming `_lib/planner_*.py` modules (the `rdd-planner` horizontal-orchestrator lib stays; only its wrapper `SKILL.md` is added).
- ❌ Removing `rdd-env-check` / `rdd-doctor` / `rddf-session` (orthogonal diagnostic infra).
- ❌ Cross-repo / Hub-Spoke federation changes (ADR-0030, ADR-0031).
- ❌ Changing the feedback lifecycle (`open → acknowledged → resolved → dismissed` per ADR-0042 §2).

## 2. Direction Reversal: D2a → D2b

### 2.1 Background

`docs/superpowers/specs/2026-09-03-rdd-planner-stage1-feedback-contract.md` §1 / `Decisions Adopted` field records:

> **D2a (no design/plan merge)** + **D3a (rdd-arch slimming deferred to Stage 3)**

D2a rationale (per Stage 1 spec): merging `guide-design + guide-plan` would conflate governance gate (design approval) with planning gate (plan quality), losing human-in-loop checkpoints.

### 2.2 Why D2a is being reversed

After 1 day of observation + user's 2026-09-04 architectural review, the user identified four counter-arguments:

1. **Approval gate does not need its own skill** — a 4-option prompt (`approve / reject / defer / revise`) is a sub-step, not a stage.
2. **Plan quality gate (`evaluate_plan` in `_lib/plan_quality.py`) can run inside builder's Phase 1** — it doesn't need a separate skill invocation; the user is already in the skill when plan quality is validated.
3. **The 3 skills share too much plumbing** — `iteration.json` read/write, `proposal.md` parse, `proposal-suggestions.md` table edits are duplicated across `guide-design`/`guide-plan`/`guide-ship`. Merging collapses the duplication.
4. **`rdd-arch` slimming + planner promotion together** create a cleaner 4-stage boundary than the current 5-phase.

User explicitly chose "塞进 rdd-builder" for the approval gate (Q1 answer), accepting that the merged builder owns all 3 former responsibilities.

### 2.3 New decision (D2b)

**D2b (design/plan/ship merge into rdd-builder approved)**. The approval gate becomes `rdd-builder` Phase 0; plan generation becomes Phase 1; execute/archive becomes Phase 2-3.

This is a **deliberate supersession of D2a** and is recorded as such in this spec's frontmatter. It does NOT retroactively invalidate Stage 1/2 work — those contracts are orthogonal to the merge.

### 2.4 Pre-conditions for D2b to succeed

| # | Condition | Verification |
|---|---|---|
| 1 | `rdd-planner` Stage 1/2 contracts (`feedback_appender`, `planner_state`) are stable | ✅ Per ADR-0037, ADR-0038 acceptance criteria met |
| 2 | `rdd-arch` slim can be merged into a single change | ✅ ADR-0042 already renamed; remaining is removing `_check_roadmap_defined` |
| 3 | `rdd-verifier` integration point is well-defined | ✅ ADR-0035 documents boundary; builder.archive calls verifier pre-archive |
| 4 | New coexistence migration strategy approved | ✅ Per user Q3 = "新并存" |

If any condition fails, D2b is reverted to D2a and Stage 1/2 path continues.

## 3. Final Architecture (v4)

### 3.1 Stage flow

```
┌─────────────┐    ┌─────────────┐    ┌──────────────────┐    ┌──────────────┐
│  rdd-arch   │ ──▶│ rdd-planner │ ──▶│   rdd-builder    │ ──▶│ rdd-verifier │
│             │    │             │    │                  │    │              │
│ ADR + arch  │    │ roadmap +   │    │ P0: approval     │    │ batch AC     │
│ docs (no    │    │ proposal    │    │ P1: plan gen     │    │ verification │
│ roadmap     │    │ authoring   │    │ P2: worktree +   │    │ (ADR-0034)   │
│ injection)  │    │ + features  │    │     execute      │    │              │
│             │    │             │    │ P2.5: review     │    │              │
│             │    │             │    │ P3: archive      │    │              │
└─────────────┘    └─────────────┘    └──────────────────┘    └──────────────┘
       │                  │                     │                      │
       ▼                  ▼                     ▼                      ▼
.arch-handoff.json  .planner-handoff.json   .builder-handoff.json   .verifier-report.json
```

### 3.2 Component responsibilities

| Component | Files owned | Reads | Writes | Human-in-loop |
|---|---|---|---|---|
| **rdd-arch** | `docs/adr/*.md`, `docs/architecture/*.md`, `.arch-handoff.json` (per ADR-0016 v2) | (none) | `.arch-handoff.json` (ADR-0016 v2 fields only, **no roadmap_path** in v3) | High (Phase 2 ADR confirmation) |
| **rdd-planner** | `roadmap.md`, `proposal-suggestions.md`, `proposal-approved.md`, `.rddf/roadmap/features/*.md`, `.rddf/improvements/*.md` (via `add-improve`), `openspec/changes/<name>/proposal.md` (authoring only, no checkbox), `.planner-handoff.json` (NEW) | `.arch-handoff.json`, `_lib/planner_state.py` (via Stage 1/2 lib) | All roadmap files (via dual-zone strategy from ADR-0038 §6), `proposal.md` content | Medium (Phase 1 approval = "approve proposal creation") |
| **rdd-builder** | `openspec/changes/<name>/tasks.md`, `.rddf/plans/<name>.md`, worktree, branches, `.builder-handoff.json` (NEW) | `proposal.md`, `tasks.md`, `.arch-handoff.json`, `.planner-handoff.json`, `plan_quality.py::evaluate_plan` | `tasks.md`, `.rddf/plans/*.md`, worktree files, branch commits, archive | High (Phase 0 approval, Phase 2.5 review 4-option) |
| **rdd-verifier** | `.rddf/state/.verifier-report.json` (per ADR-0034) | worktree branches (diff vs main), `tasks.md`, `.rddf/plans/*.md` | `.rddf/state/.verifier-report.json` | Low (retry loop bounded to 3 per ADR-0034) |

### 3.3 `rdd-planner` promotion: from horizontal orchestrator to full stage

Currently `rdd-planner` exists only as `_lib/planner_*.py` + `_lib/cli/planner_cmd.py` (no skill wrapper). Promotion adds:

```
skills/rdd-planner/                          # NEW
├── SKILL.md                                 # NEW — stage entry/exit contract
└── scripts/
    ├── planner_stage_entry.sh               # NEW — emits .planner-handoff.json
    └── planner_stage_exit.sh                # NEW — consumes arch-handoff, emits planner-handoff

_lib/
├── planner_handoff.py                       # NEW — schema v1 for .planner-handoff.json
└── schemas/
    └── planner_handoff_schema.json          # NEW — JSON schema v1
```

**`.planner-handoff.json` schema v1** (NEW, written by `planner_stage_exit.sh`):

```json
{
  "schema": "planner-handoff-v1",
  "version": 1,
  "owner": "rdd-planner",
  "planner_complete_at": "2026-09-04T10:00:00Z",
  "arch_handoff_revision": 12,
  "planner_state_revision": 5,
  "current_sprint": "sprint-2026-09",
  "proposals_authored": ["change-foo", "change-bar"],
  "proposals_approved_count": 0,
  "features_active": ["feat-x", "feat-y"],
  "awaiting_builder": ["change-foo", "change-bar"]
}
```

**Backward compat with Stage 1/2**: `.planner-state.json` (per ADR-0038 §3.5) and `.planner-feedback.json` (per ADR-0042 §2) are **NOT** merged into `.planner-handoff.json`. Three files coexist, each with its own owner and FileLock.

### 3.4 `rdd-builder` (NEW) — 4-phase internal state machine (with deps + verifier retry loop)

```text
rdd-builder
   │
   ▼
Phase 0: Approval Gate
   ├─ input:  openspec/changes/<name>/proposal.md (from rdd-planner)
   ├─ prompt:  4-option (approve / reject / defer / revise)
   ├─ reject → rddf feedback add <proposal> --kind rejected, exit 0 (no archive)
   ├─ defer  → rddf feedback add <proposal> --kind blocked, exit 0 (no archive)
   ├─ revise → rddf feedback add <proposal> --kind needs-revision, exit 1
   └─ approve → continue to Phase 1
   │
   ▼
Phase 1: Plan Generation
   ├─ input:  approved proposal.md
   ├─ call:   rdd-workflow-writing-plans (existing, unchanged)
   ├─ write:  openspec/changes/<name>/tasks.md (NEW builder responsibility per user D)
   ├─ write:  .rddf/plans/<name>.md (existing)
   ├─ validate: _lib/plan_quality.py::evaluate_plan (FAIL → return exit 2)
   └─ success → continue to Phase 1.5
   │
   ▼
Phase 1.5: Deps + Execution Mode Decision [NEW per Oracle C2]
   ├─ reuse skills/deps/scripts/* (existing; absorbed from guide-plan per ADR-0024)
   ├─ analyze inter-change deps (incl ADR-0022 manual_deps field)
   ├─ cross-repo gate (per ADR-0031 if category=cross-repo-federation)
   ├─ STRICT_DEPS_GATE enforcement (per §13 acceptance criteria)
   ├─ decide execution_mode: worktree vs lightweight
   ├─ write execution_mode_decision to .rddf/state/builder/<change>.json
   ├─ FAIL (blockers) → exit 7 (deps gate FAIL)
   └─ success → continue to Phase 2
   │
   ▼
Phase 2: Worktree + Execute (TDD 5 步)
   ├─ COMMIT GATE: artifacts (proposal.md, tasks.md, plan.md) must be committed
   ├─ select_worktree: per execution_mode_decision (worktree/lightweight)
   ├─ execute TDD 5-step from execute skill (write failing → verify fail → implement → verify pass → commit)
   ├─ writeback tasks.md checkboxes per execute/scripts/tasks_writeback.sh
   └─ success → continue to Phase 2.5
   │
   ▼
Phase 2.5: Review (4-option dispatch)
   ├─ existing: skills/guide-ship/scripts/ship_review.sh::handle_review_action
   ├─ prompt: 4-option (merge / revise / abandon / archive)
   ├─ merge → continue to Phase 3
   └─ others → return with state preserved
   │
   ▼
Phase 3: Archive [with Verifier Retry Loop per Oracle C1]
   │
   ├── pre-call: rdd-verifier (per ADR-0035; verifier runs first, then archive)
   │
   ├── verifier verdict dispatch (per ADR-0034 §7):
   │   ├─ PASS (0)            → continue to archive commit
   │   ├─ implementation_gap (1) → back-route to Phase 2 (re-execute; plan is fine)
   │   ├─ ac_fail (2)         → back-route to Phase 1 (re-plan; criteria need revision)
   │   └─ needs_human (3)     → halt, exit 4 (escalate to human)
   │
   ├── retry counter (in per-change handoff):
   │   ├─ retry_count starts at 0
   │   ├─ increments on every back-route (Phase 3 → Phase 1 or 2)
   │   ├─ max_retries = 3 (mirrors ADR-0034 §8 verifier ceiling)
   │   └─ on retry_count > max_retries: halt, exit 4
   │
   ├── archive: openspec archive <name> --yes
   │
   └── post-archive: commit_archive_moves + _lib/post_archive_cleanup.sh (existing)

[RETRY LOOP — back-routes from Phase 3 → Phase 1 or Phase 2, capped at 3 retries]
```

**Key design points** (all addressing Oracle findings):

1. **Phase 1.5 inserted** to absorb guide-plan's deps + execution_mode responsibilities (per ADR-0024). Without this, Wave 3 retirement of `.plan-handoff.json` orphans the execution_mode_decisions field that drives worktree vs lightweight selection in Phase 2.

2. **Phase 0 reject/defer/revise paths now route through `rddf feedback add`** (per ADR-0037 single-writer contract). Removes builder→`proposal-suggestions.md` direct write, fixing the ADR-0028 role boundary violation (Oracle M2 — addressed in batch 3).

3. **Verifier verdict routing table** (Phase 3) preserves ADR-0034's 5-value exit semantics (0/1/2/3/4) instead of collapsing to a single exit 6. Each verdict has a deterministic destination:
   - `implementation_gap` (verifier exit 1) → Phase 2 (re-execute)
   - `ac_fail` / `proposal_drift` (verifier exit 2) → Phase 1 (re-plan)
   - `needs_human` (verifier exit 3) → halt, exit 4
   - `halted` max_retries=4 → halt, exit 4 (verifier halt supersedes builder halt)
   - `pass` (verifier exit 0) → continue to archive

4. **Retry counter** lives in `.rddf/state/builder/<change>.json` (per-change layout, see §6.3). Capped at 3 retries per ADR-0034 ceiling. On exceeded → halt with exit 4, requiring human intervention.

5. **Phase 2 COMMIT GATE** is explicit: artifacts must be committed before `git worktree add`. Prevents TOCTOU race with planner attach dirtying main repo (Oracle Q6 finding).

## 4. Migration Plan: 3-Wave "新并存" Strategy

Per user Q3 answer = "新并存". Zero-pressure adoption: new skills added alongside old, deprecated last.

### 4.1 Wave 1 — New skills added, old skills untouched

```
add:
  skills/rdd-arch/         # slim version (Phase 1 setup only, no roadmap injection)
                           # Note: skills/rdd-arch/ already exists from ADR-0042;
                           #       this wave only adds the slim-removal patches
  skills/rdd-planner/SKILL.md     # NEW wrapper (already has _lib/planner_*.py)
  skills/rdd-planner/scripts/     # NEW (entry/exit scripts + handoff writer)
  skills/rdd-builder/             # NEW (4-phase internal state machine)
  skills/rdd-builder/scripts/     # NEW (5 phase scripts: phase0_approval, phase1_plan,
                                   #     phase1_5_deps, phase2_execute, phase2_5_review, phase3_archive)
  _lib/cli/planner_cmd.py         # EXISTS, extend with `planner-handoff` sub-subcommand
  _lib/cli/builder_cmd.py         # NEW (rddf builder ... dispatcher)
  _lib/planner_handoff.py         # NEW
  _lib/builder_handoff.py         # NEW [per-change handoff r/w + FileLock per Oracle H3]
  _lib/builder_deps.py            # NEW [Phase 1.5 deps + execution_mode decision per Oracle C2]
  _lib/builder_retry.py           # NEW [verifier verdict → Phase routing + retry counter per Oracle C1]
  _lib/schemas/planner_handoff_schema.json    # NEW v1
  _lib/schemas/builder_handoff_schema.json    # NEW v1 (per-change layout, NOT single file)
  _lib/schemas/builder_retry_schema.json      # NEW v1 (verifier verdict + routing table)
  tests/unit/test_planner_handoff.py          # NEW
  tests/unit/test_builder_handoff.py          # NEW (per-change layout, no global file race)
  tests/unit/test_builder_deps.py             # NEW (Phase 1.5 logic, deps blockers)
  tests/unit/test_builder_retry.py            # NEW (verifier verdict routing + retry cap)
  tests/unit/test_builder_*.py                # NEW (~30 tests across phase scripts)
  tests/integration/test_rdd_builder_*.bats   # NEW (~8 bats tests)
  docs/adr/ADR-0043-rdd-workflow-v4-stage-merge.md  # NEW

unchanged (remain active):
  skills/guide-design/    # ⚠ will mark DEPRECATED banner in Wave 2
  skills/guide-plan/      # ⚠ will mark DEPRECATED banner in Wave 2
  skills/guide-ship/      # ⚠ will mark DEPRECATED banner in Wave 2
  _lib/cli/{design,plan,ship}_cmd.py
```

**B tests in Wave 1**: Total runtime doubles (old + new both run). Acceptable for 1-2 weeks.

**Regression gate**: `./test.sh --full --regression` must show **zero new failures** vs `KNOWN_FAILURES.txt` baseline (per AGENTS.md "Archive 前全量回归门" rule).

### 4.2 Wave 2 — Old skills marked DEPRECATED

After Wave 1 ships and is used ≥1 week without major issues:

```
modify:
  skills/guide-design/SKILL.md      # top 5 lines: DEPRECATED, use rdd-builder
  skills/guide-plan/SKILL.md        # top 5 lines: DEPRECATED, use rdd-builder
  skills/guide-ship/SKILL.md        # top 5 lines: DEPRECATED, use rdd-builder
  _lib/cli/design_cmd.py            # print stderr warning, route to rdd-builder
  _lib/cli/plan_cmd.py              # print stderr warning, route to rdd-builder
  _lib/cli/ship_cmd.py              # print stderr warning, route to rdd-builder
  docs/migration-v3-to-v4.md        # NEW

add:
  tests/integration/test_legacy_guide_*_shim.bats    # NEW, locks shim contract
```

**Behavior**: Calling `rddf guide-design` prints:
```
⚠️ DEPRECATED: rddf guide-design → rddf builder. Shim will be removed in v4.x.2.
```

Then routes to `rddf builder` with appropriate args.

### 4.3 Wave 3 — Hard removal (v4.x.2 or later, ≥4 weeks after Wave 1)

```
remove:
  skills/guide-design/    # DELETE entirely
  skills/guide-plan/      # DELETE entirely
  skills/guide-ship/      # DELETE entirely
  _lib/cli/design_cmd.py  # DELETE
  _lib/cli/plan_cmd.py    # DELETE
  _lib/cli/ship_cmd.py    # DELETE
  tests/integration/test_guide_*.bats     # DELETE (~40-50 tests)

modify:
  docs/adr/README.md                     # update ADR list
  AGENTS.md                              # update phase references
  README.md                              # update stage table
```

**Compatibility breaks**: `skill_use("guide-design")` returns "skill not found". Users must migrate to `skill_use("rdd-builder")`.

## 5. CLI Surface

### 5.1 `rddf planner` (extend existing)

```bash
# Stage 2 commands (existing, unchanged)
rddf planner status                          # read-only sprint snapshot
rddf planner sync [--apply|--dry-run]        # default dry-run
rddf planner feedback [--status|--kind|--acknowledge|--resolve|--dismiss|--prune-resolved]
rddf planner attach <proposal> [--project-id X --phase Y [--theme Z]]
rddf planner audit
rddf planner history
rddf planner advance-sprint [--to-sprint <name>]

# NEW in Wave 1 (this spec)
rddf planner stage-entry                     # write .planner-handoff.json, exit 0
rddf planner stage-exit                      # consume .arch-handoff.json, emit planner-handoff
rddf planner handoff [--json]                # dump .planner-handoff.json (read-only)
```

### 5.2 `rddf builder` (NEW)

```bash
rddf builder run <change-name>               # full 4-phase run (Phase 0 → 3)
rddf builder phase0 <change-name>            # approval gate only
rddf builder phase1 <change-name>            # plan generation only
rddf builder phase2 <change-name>            # worktree + execute only
rddf builder phase2.5 <change-name>          # review only
rddf builder phase3 <change-name>            # archive only (calls verifier first)
rddf builder list                            # list builder-eligible changes
rddf builder status <change-name>            # show current phase
rddf builder --help
```

**Exit codes**:
- `0` — phase completed successfully (or skipped)
- `1` — approval rejected/deferred, no archive
- `2` — plan quality gate FAIL
- `3` — worktree creation failed
- `4` — execute TDD step failed
- `5` — review chose revise/abandon
- `6` — archive gate FAIL (verifier rejected)

### 5.3 `rddf roadmap` (deprecated alias in Wave 2)

```bash
# Existing rddf roadmap commands (migrate to rddf planner):
rddf roadmap migrate                  → rddf planner roadmap migrate (or stay if Stage 2 only)
rddf roadmap validate-fragments      → rddf planner roadmap validate
rddf roadmap add-feature             → rddf planner roadmap add-feature

# Behavior in Wave 2+: print ⚠️ DEPRECATED, route to rddf planner roadmap *
```

## 6. State Files

### 6.1 Summary

| File | Owner (per ADR-0028) | New in v4? | Schema version |
|---|---|---|---|
| `.rddf/state/.arch-handoff.json` | rdd-arch | Modified (remove roadmap_path from contract v3) | v3 (new in this spec) |
| `.rddf/state/.planner-handoff.json` | rdd-planner | **NEW** | v1 |
| `.rddf/state/.planner-state.json` | rdd-planner | No (Stage 2) | v1 |
| `.rddf/state/.planner-feedback.json` | rdd-planner | No (ADR-0042) | v1 |
| `.rddf/state/.design-handoff.json` | (none, retiring) | **RETIRE** in Wave 3 | n/a |
| `.rddf/state/.plan-handoff.json` | (none, retiring) | **RETIRE** in Wave 3 | n/a |
| `.rddf/state/builder/<change>.json` | rdd-builder | **NEW** (per-change layout, not single file) | v1 |
| `.rddf/state/.verifier-report.json` | rdd-verifier | No (ADR-0034) | v1 |

### 6.2 `.arch-handoff.json` v3 schema (modified)

**Removed field** (per user first ask: rdd-arch slim):
- `roadmap_path` (per ADR-0016 v2) — rdd-arch no longer writes this. Consumers fallback to `roadmap.md` default.

**Retained fields** (unchanged from v2):
- `adr_dir`, `adr_pattern`, `architecture_dir`, `discovered`, `arch_complete_revision` (per ADR-0042)
- `roadmap_fragments_dir`, `adr_regex` (per ADR-0016 v2 additive)

**Schema version bump**: `1 → 3` (skipping 2 because v2 already used by ADR-0042). Per `_lib/schemas/arch_handoff_schema.json` precedent: bump version forces consumer validation.

**Migration**: existing v2 handoff files auto-upgrade on read (add `arch_complete_revision: 0` default if missing). v1 files require manual upgrade.

### 6.3 `.rddf/state/builder/<change>.json` schema v1 (NEW, per-change layout per Oracle H3)

**File layout** — one file per change under `.rddf/state/builder/` directory. **Not** a single `.builder-handoff.json` file. This prevents the global-file serial-write regression that ADR-0034 §2 fixed for `.verifier-loop.json`.

```text
.rddf/state/builder/
├── change-foo.json    # phase: phase-2, retry_count: 0
├── change-bar.json    # phase: phase-0, retry_count: 0
└── change-baz.json   # phase: phase-3, retry_count: 1 (post-verifier implementation_gap)
```

**Schema v1**:

```json
{
  "schema": "builder-handoff-v1",
  "version": 1,
  "owner": "rdd-builder",
  "change_name": "change-foo",
  "current_phase": "phase-0|phase-1|phase-1.5|phase-2|phase-2.5|phase-3",
  "approval_status": "pending|approved|rejected|deferred|revising",
  "plan_quality_status": "pending|valid|invalid",
  "execution_mode_decision": {
    "mode": "worktree|lightweight",
    "reason": "files<=2 AND tasks<=3",
    "decided_at": "2026-09-04T10:00:00Z",
    "decided_by": "phase-1.5-deps-analyzer"
  },
  "deps_status": {
    "blockers": [],
    "manual_deps": [],
    "cross_repo_pending": [],
    "decided_at": "2026-09-04T10:00:00Z"
  },
  "worktree_path": "/abs/path/.rddf/wt/change-foo",
  "branch": "openspec/change-foo",
  "execution_status": "pending|running|failed|completed",
  "review_status": "pending|merge|revise|abandon",
  "retry_count": 0,
  "max_retries": 3,
  "retry_history": [
    {
      "from_phase": "phase-3",
      "to_phase": "phase-1",
      "verifier_exit_code": 2,
      "verifier_kind": "ac_fail",
      "at": "2026-09-04T11:00:00Z"
    }
  ],
  "archive_status": "pending|verifying|archived|failed",
  "verifier_report_path": ".rddf/state/.verifier-report.json",
  "updated_at": "2026-09-04T10:00:00Z"
}
```

**Key fields per Oracle findings**:

- `change_name` (replaces `current_change` — implied by filename, but explicit for JSON schema clarity)
- `current_phase` — supports the new Phase 1.5 (Oracle C2)
- `execution_mode_decision` — drives Phase 2 worktree selection (Oracle C2: absorbs `execution_mode_decisions` from retired `.plan-handoff.json`)
- `deps_status` — explicit blocker tracking for STRICT_DEPS_GATE (Oracle C2)
- `retry_count` + `max_retries` + `retry_history` — required for verifier回环 (Oracle C1)
- All exit-code-bearing fields use enum string, not concatenated pipe (cleaner than original draft)

**File lock**: `_lib/builder_handoff.py` uses per-file `FileLock(.rddf/state/builder/<change>.json.lock)` with 10s timeout. Multiple changes can be in flight simultaneously without contention.

**Backward compat with `.plan-handoff.json`**: During Wave 1 "新并存" period, builder Phase 1.5 also reads `.plan-handoff.json::execution_mode_decisions` if present (legacy fallback for changes produced by guide-plan). After Wave 3 hard-removal, this fallback path is deleted.

## 7. Testing Strategy

### 7.1 Unit tests (pytest)

| File | Test count target | Coverage |
|---|---|---|
| `test_planner_handoff.py` | ≥6 | schema validation, write/read/upgrade v1 → v1 |
| `test_builder_handoff.py` | ≥8 | per-change layout (`<change>.json` not single file), FileLock acquire/release, schema v1 round-trip, no global-file regression |
| `test_builder_deps.py` | ≥8 | Phase 1.5: deps analysis, manual_deps merge (ADR-0022), execution_mode decision matrix (file count × task count × risk keyword), STRICT_DEPS_GATE enforcement, cross-repo pending check (ADR-0031) |
| `test_builder_retry.py` | ≥10 | verifier verdict routing table: PASS(0) → archive; implementation_gap(1) → Phase 2; ac_fail(2) → Phase 1; needs_human(3) → halt exit 4; halted(4) → halt exit 4. Retry counter increments only on back-route; halt at retry_count > max_retries; retry_history append |
| `test_builder_phase0.py` | ≥8 | approval gate dispatch (4-option), reject/defer/revise → `rddf feedback add` integration (single-writer contract), approval persist + replay skip |
| `test_builder_phase1.py` | ≥6 | plan generation, plan_quality evaluation, tasks.md write, integration with Phase 1.5 |
| `test_builder_phase1_5.py` | ≥4 | execution_mode_decision persistence in per-change handoff, deps_status population |
| `test_builder_phase2.py` | ≥8 | worktree select per execution_mode (worktree/lightweight), COMMIT GATE enforcement, TDD 5-step dispatch, tasks.md writeback |
| `test_builder_phase3.py` | ≥6 | archive dispatch, verifier hook integration, **verifier exit code preserved (0/1/2/3/4, not collapsed to single 6)**, post-archive cleanup |
| `test_builder_cli.py` | ≥5 | CLI arg parsing, phase dispatch, **5-value exit code matrix** |

**Total: ≥69 unit tests** (was ≥39 in pre-batch-1 spec)

### 7.2 Integration tests (bats)

| File | Test count target | Coverage |
|---|---|---|
| `test_rdd_builder_phase0_approval.bats` | ≥3 | end-to-end approval gate flow |
| `test_rdd_builder_phase1_1_5_deps.bats` | ≥3 | deps + execution_mode end-to-end (no real openspec needed) |
| `test_rdd_builder_phase2_execute.bats` | ≥3 | worktree creation, TDD execution, tasks writeback |
| `test_rdd_builder_phase3_archive.bats` | ≥3 | archive + verifier hook integration |
| `test_rdd_builder_verifier_retry.bats` | ≥3 | verifier verdict routing end-to-end: implementation_gap → Phase 2 back-route, retry_count increment; ac_fail → Phase 1 back-route; halted → exit 4 halt |
| `test_rdd_builder_parallel_isolation.bats` | ≥3 | two changes in flight simultaneously (change-foo + change-bar): per-change handoff files isolated, no global-file race (regression test for ADR-0034 §2 fix pattern) |
| `test_rdd_planner_skill_entry.bats` | ≥3 | skill entry/exit contract, handoff emission |
| `test_legacy_guide_*_shim.bats` (Wave 2) | ≥3 | backward compat shim (Wave 2 only) |

**Wave 1 total: ≥21 bats tests** (Wave 2 adds 3 shim tests for total ≥24). The pre-batch-1 spec said ≥20; revised count is ≥21 (consistent within Wave 1 scope).

### 7.3 Idempotency tests (critical)

```python
def test_builder_phase0_replay_is_idempotent(tmp_path):
    """Re-running Phase 0 after approval does not re-prompt user."""
    # First run: approval accepted, plan generated
    builder.phase0(change="change-foo", input="approve")
    # Second run: should detect existing approval, skip prompt
    result = builder.phase0(change="change-foo", input="anything")
    assert result.exit_code == 0
    assert result.skipped_reason == "already_approved"


def test_builder_retry_loop_caps_at_max(tmp_path):
    """Retry counter must halt at max_retries=3 (per ADR-0034)."""
    # First run: verifier implementation_gap → back-route to Phase 2, retry_count=1
    # ... after 4 total back-routes, exit 4 + halt
    assert final.retry_count == 4  # one more than max
    assert final.exit_code == 4
    assert final.state == "halted_requires_human"


def test_builder_parallel_changes_isolated(tmp_path):
    """Two changes in flight use independent per-change handoff files."""
    # Simulate two changes executing in parallel
    # Assert no global-state race (regression test for ADR-0034 §2 pattern)
    assert (tmp_path / ".rddf/state/builder/change-foo.json").is_file()
    assert (tmp_path / ".rddf/state/builder/change-bar.json").is_file()
    # No .builder-handoff.json (single file) — must NOT exist
    assert not (tmp_path / ".rddf/state/.builder-handoff.json").exists()
```

### 7.4 Regression gate

Per AGENTS.md "Archive 前全量回归门" rule. Each Wave runs:
- `./test.sh --full --regression` — no new failures vs `KNOWN_FAILURES.txt` baseline
- `./test.sh --python` — all unit + integration pass
- `./test.sh --bats --regression` — bats no new failures

## 8. Acceptance Criteria

Wave 1 is **done** when all are true:

### Core deliverables (16 items)

- [ ] `skills/rdd-planner/SKILL.md` exists with stage entry/exit contract
- [ ] `skills/rdd-planner/scripts/{planner_stage_entry,planner_stage_exit}.sh` exist
- [ ] `skills/rdd-builder/SKILL.md` exists with state machine contract (now 6 phases incl. Phase 1.5)
- [ ] `skills/rdd-builder/scripts/{phase0_approval,phase1_plan,phase1_5_deps,phase2_execute,phase2_5_review,phase3_archive}.sh` exist
- [ ] `_lib/planner_handoff.py` exists with `write_planner_handoff()`, `read_planner_handoff()`, schema v1 validation
- [ ] `_lib/schemas/planner_handoff_schema.json` v1 exists
- [ ] `_lib/cli/builder_cmd.py` registered in `_lib/cli/__init__.py::_ROUTES` as `rddf builder ...`
- [ ] `.arch-handoff.json` contract v3 implemented: `roadmap_path` field removed (with v2 → v3 auto-upgrade on read) — **addressed in batch 2 (Oracle H1)**
- [ ] `_lib/gate.py::_check_roadmap_defined` removed (no longer called by arch-done gate) — **addressed in batch 2 (Oracle H1)**
- [ ] `tests/unit/test_{planner_handoff,builder_*}.py` ≥69 tests (revised from ≥39 per batch 1 expansion), all green under `RDD_PLANNER_MOCK=yes`
- [ ] `tests/integration/test_rdd_{planner,builder}_*.bats` ≥21 tests (revised from ≥20), all green
- [ ] `./test.sh --full --regression` exits 0 (no new failures)
- [ ] `ADR-0043-rdd-workflow-v4-stage-merge.md` written and committed (this spec's ADR twin)
- [ ] Old skills (`guide-design`, `guide-plan`, `guide-ship`) UNTOUCHED — shim banners only in Wave 2
- [ ] Demo run recorded in §9
- [ ] All file paths in §4.1 exist on disk (verified via `ls` + git status, no orphans)

### Oracle C1 — Verifier retry loop (8 items)

- [ ] `_lib/builder_retry.py` exists with verifier verdict routing table
- [ ] `_lib/schemas/builder_retry_schema.json` v1 exists
- [ ] **Verifier exit codes 0/1/2/3/4 all preserved** in `rddf builder` exit codes (NOT collapsed to single 6)
- [ ] `retry_count` field exists in `.rddf/state/builder/<change>.json` schema v1
- [ ] Retry counter increments only on back-route (not on forward progression)
- [ ] Halt at `retry_count > max_retries=3` (mirrors ADR-0034 §8)
- [ ] `tests/unit/test_builder_retry.py` ≥10 tests, covers all 5 verdict codes
- [ ] `tests/integration/test_rdd_builder_verifier_retry.bats` ≥3 tests, end-to-end back-route flow

### Oracle C2 — Deps absorbed into rdd-builder (8 items)

- [ ] `_lib/builder_deps.py` exists with Phase 1.5 deps analysis + execution_mode decision
- [ ] Phase 1.5 skill script `phase1_5_deps.sh` exists and is invoked from builder Phase 1 → Phase 2 boundary
- [ ] `execution_mode_decision` field exists in per-change handoff schema (drives Phase 2 worktree selection)
- [ ] `deps_status` field exists with `blockers`/`manual_deps`/`cross_repo_pending` arrays
- [ ] ADR-0024 deps-driven execution mode contract migrated: `.plan-handoff.json::execution_mode_decisions` consumers in `_lib/builder_deps.py` (legacy fallback during Wave 1)
- [ ] `tests/unit/test_builder_deps.py` ≥8 tests, covers STRICT_DEPS_GATE, manual_deps merge, cross-repo check
- [ ] `tests/integration/test_rdd_builder_phase1_1_5_deps.bats` ≥3 tests, end-to-end deps flow
- [ ] Pre-condition in §2.4 row 1 updated to reflect C2 fix (deps no longer orphan)

### Oracle H3 — Per-change handoff layout (5 items)

- [ ] `.rddf/state/builder/<change>.json` directory + per-change file layout implemented
- [ ] **Single-file `.rddf/state/.builder-handoff.json` must NOT exist** (regression assertion)
- [ ] Per-file `FileLock(.rddf/state/builder/<change>.json.lock, timeout=10)` used for all writes
- [ ] `tests/unit/test_builder_handoff.py` ≥8 tests, includes parallel-isolation test (two changes in flight, no global race)
- [ ] `tests/integration/test_rdd_builder_parallel_isolation.bats` ≥3 tests, end-to-end parallel build

**Total: 37 AC items** (16 core + 8 C1 + 8 C2 + 5 H3) — **all must be `[x]` before Wave 1 ships.**

## 9. Demo Run (record after implementation)

```bash
# Setup: clean project state
cd /tmp/opencode/rdd-workflow-demo
git init && touch roadmap.md

# === Phase 1: rdd-arch (slim) ===
$ rddf arch status
# rdd-arch: phase-1 | 5 ADRs | Planner: 0 critical, 0 warning

# === Phase 2: rdd-planner ===
$ rddf planner status
# Sprint: sprint-2026-09
# Active: 0
# Unmapped: 0

# Author a new proposal
$ rddf planner new --theme "demo" --priority P2
# ✓ Created proposal-suggestions.md entry: demo-change

# Brainstorm + accept
$ rddf planner brainstorm demo-change
# (interactive Q&A)

$ rddf planner accept demo-change
# ✓ proposal.md written
# ✓ tasks.md scaffolded (no checkboxes yet)
# ✓ .planner-handoff.json emitted

# === Phase 3: rdd-builder ===
$ rddf builder run demo-change
# Phase 0: 4-option prompt → approve
# Phase 1: plan generated, plan_quality PASS
# Phase 2: worktree created, TDD 5-step completed
# Phase 2.5: review → merge
# Phase 3: verifier passed, archive committed
# ✓ demo-change archived

# === Phase 4: rdd-verifier ===
$ rddf verifier run --change demo-change
# ✓ AC verified: 5/5
```

## 10. Risks & Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| Three former skills share `iteration.json` writes → merge introduces race | High | Use `FileLock(.iteration.json.lock)` with 10s timeout, retry once |
| `rdd-arch` v3 contract removal of `roadmap_path` breaks consumers | High | Auto-upgrade v2 → v3 on read; v1 → v3 manual upgrade documented |
| `rdd-builder` 4-phase complexity exceeds user mental model | Medium | Phase 0 is the only human-in-loop; Phase 1-3 are auto. Document as "1 user decision + 3 mechanical phases" |
| Loss of `guide-design` 4-option approval review | Medium | The 4-option prompt moves verbatim into `rdd-builder` Phase 0; same UX, just different skill name |
| Wave 3 hard removal breaks user scripts calling `skill_use("guide-design")` | Medium | Wave 2 shim with stderr warning; users have ≥4 weeks to migrate |
| `rdd-planner` promotion from horizontal to stage may conflict with ADR-0028 role boundaries | Medium | Re-affirm role boundaries: planner still does NOT write `.arch-handoff.json`; only `.planner-handoff.json` (NEW, separate file) |
| `rdd-builder` approval gate may prematurely kill low-quality proposals that planner could revise | Low | Phase 0 reject → `rddf feedback add --kind rejected`; planner can pick up via `rddf planner revise` (Stage 2.5+) |

## 11. Non-Goals (explicit)

- ❌ Removing `rdd-verifier` (per user Q2 = "保持独立第 4 阶段").
- ❌ Removing `_lib/planner_*.py` (Stage 1/2 contracts stay; only `SKILL.md` wrapper added).
- ❌ Renaming `rdd-arch` (already renamed per ADR-0042).
- ❌ Changing `proposal-suggestions.md` or `proposal-approved.md` table format.
- ❌ Auto-resolving feedback on approval (still manual per ADR-0042 lifecycle).
- ❌ Touching `rdd-env-check` / `rdd-doctor` / `rddf-session` (orthogonal).
- ❌ Cross-repo / Hub-Spoke federation changes.
- ❌ Modifying `rdd-workflow-writing-plans` (consumed by `rdd-builder` Phase 1, unchanged).

## 12. Related Files

- `_lib/planner_*.py` (Stage 1/2 contracts, unchanged)
- `_lib/cli/planner_cmd.py` (extended in Wave 1)
- `_lib/plan_quality.py::evaluate_plan` (consumed by `rdd-builder` Phase 1)
- `_lib/gate.py::_check_roadmap_defined` (removed in Wave 1)
- `_lib/schemas/arch_handoff_schema.json` (bumped v2 → v3)
- `skills/_lib/archive.sh` (consumed by `rdd-builder` Phase 3)
- `_lib/post_archive_cleanup.sh` (unchanged)
- `skills/_lib/ship_execution_mode.sh` (consumed by `rdd-builder` Phase 2)
- `skills/execute/scripts/select_worktree.sh` (consumed by `rdd-builder` Phase 2)
- `skills/execute/scripts/tasks_writeback.sh` (consumed by `rdd-builder` Phase 2)
- `skills/guide-ship/scripts/ship_review.sh::handle_review_action` (consumed by `rdd-builder` Phase 2.5)
- `tests/_lib/test_helper.bash` (bats helper integration)
- AGENTS.md "Archive 前全量回归门" (regression gate rule)
- ADR-0016 (arch-handoff contract, v3 supersedes v2)
- ADR-0028 (role model per phase, reaffirmed)
- ADR-0034 (rdd-verifier 5th phase, unchanged)
- ADR-0035 (verifier-archive-gate boundary, builder integration)
- ADR-0037 (feedback contract, unchanged)
- ADR-0038 (rdd-planner horizontal orchestrator, extended in §3.3)
- ADR-0041 (planner sprint lifecycle, unchanged)
- ADR-0042 (rdd-arch rename + planner feedback, unchanged; this spec §6.2 references its `arch_complete_revision` field)

## 13. Self-Review Notes (post-write, all resolved)

- [x] No "TBD" / "TODO" placeholders in main body.
- [x] File paths are repo-relative and refer to existing modules (verified via `ls` + `git log`).
- [x] D2a → D2b reversal is explicit and justified (Section 2).
- [x] Backward compat with Stage 1/2 contracts is preserved.
- [x] Migration uses "新并存" with 3-wave timeline matching user Q3 answer.
- [x] Out-of-scope items are explicit (Section 1.4 + Section 11).
- [x] No ambiguous requirements; each acceptance criterion is testable.
- [x] Wave 1 acceptance criteria are bounded (~39 unit + ~20 bats tests).
- [x] Risks are severity-rated with concrete mitigations.
- [x] **Ambiguity resolved** — exit code semantics for Phase 0 reject/defer: exit 0 means "skill completed its job (presented prompt, recorded decision)"; proposal outcome (approve/reject/defer) is recorded in `.builder-handoff.json::approval_status`, not in exit code. User can re-invoke `rddf builder phase0` to change decision. This is consistent with current `guide-design` 4-option dispatch (no failure exit on reject).
- [x] **Wave 3 timing** — explicitly tied to user-observable signal: "zero `⚠️ DEPRECATED` warnings in CI logs for ≥1 consecutive week" as the empirical trigger. If user base is small and CI doesn't run, fall back to "≥4 calendar weeks after Wave 1 ship". Documented in Wave 3 commit message and AGENTS.md update.
- [x] **Scope bounded** — Wave 1 is a single PR scope (rdd-planner SKILL.md + rdd-builder SKILL.md + handoff schema + slim arch + tests). Wave 2/3 are separate changes with their own ADRs; this spec only governs Wave 1 implementation. Acceptance criteria Section 8 explicitly reference Wave 1 only.

---

## Post-Spec Plan

After Wave 1 ships and is observed for ≥1 week in production:
- **Wave 2**: Add DEPRECATED banners + shim routes to `guide-design`/`guide-plan`/`guide-ship`.
- **Wave 3**: Hard removal (separate spec, separate ADR).
- **Future**: `rdd doctor --category stage-merge` to detect users still on guide-* skills.