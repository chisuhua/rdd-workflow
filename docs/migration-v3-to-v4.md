# Migration Guide: v3.0 → v4.x (Stage Merge)

> **Date**: 2026-09-04
> **Audience**: Existing users of `rdd-workflow` on v3.0+ (5-phase architecture)
> **Status**: Wave 1 ✅ shipped 2026-09-04; Wave 2 (deprecation shim) in progress; Wave 3 (hard removal) planned for ≥4 weeks after Wave 1 + zero shim usage for ≥7 consecutive days

## What changed

The v3.0 5-phase architecture (`arch → design → plan → ship → verify`) was
replaced by a v4.0 4-stage architecture:

```
v3.0 (5 phases):
  arch (rdd-arch) → design (guide-design) → plan (guide-plan) → ship (guide-ship) → verify (rdd-verifier)

v4.x (4 stages):
  arch (rdd-arch slim) → rdd-planner → rdd-builder (6-phase internal state machine) → rdd-verifier
```

| v3.0 skill | v4.x replacement | Status |
|---|---|---|
| `rdd-arch` | `rdd-arch` (slim: removed 3 roadmap fields; contract v2→v3) | ✅ Active |
| `guide-design` (proposal approval) | `rdd-builder` Phase 0 (approval gate) | ⚠️ Deprecated (shim routes to `rdd-builder`; Wave 3 hard-removal planned) |
| `guide-plan` (propose + deps + plan) | `rdd-planner` (proposal authoring) + `rdd-builder` Phase 1 (plan gen) | ⚠️ Deprecated |
| `guide-ship` (worktree + execute + archive) | `rdd-builder` Phases 1.5/2/2.5/3 | ⚠️ Deprecated |
| `rdd-verifier` | `rdd-verifier` (unchanged) | ✅ Active |
| **NEW**: `rdd-planner` | Stage 2 of v4 (wraps existing `_lib/planner_*.py`) | ✅ Active |
| **NEW**: `rdd-builder` | Stage 3 of v4 (6-phase internal state machine) | ✅ Active |

## Migration steps

### 1. Update skill invocations

Replace skill calls in your custom scripts / agent prompts / docs:

| v3.0 | v4.x |
|---|---|
| `skill_use("guide-design")` | `skill_use("rdd-builder")` (then answer approval gate) |
| `skill_use("guide-plan")` | `skill_use("rdd-planner")` (author proposal) + `skill_use("rdd-builder")` (run plan) |
| `skill_use("guide-ship")` | `skill_use("rdd-builder")` (run from `phase1.5` or later) |
| `skill_use("rdd-arch")` | `skill_use("rdd-arch")` (unchanged; slim version) |
| `skill_use("rdd-verifier")` | `skill_use("rdd-verifier")` (unchanged) |

### 2. Update CLI commands

The `rddf` CLI dispatcher (`_lib/cli/__init__.py`) routes are now:

```bash
# v4.x (canonical)
rddf builder run <change> [--no-pause] [--from-phase N] [--retry-on-fail]
rddf builder phase0 <change>           # approval gate (was guide-design)
rddf builder phase1 <change>           # plan gen (was guide-plan part)
rddf builder phase1.5 <change>         # deps + execution_mode (NEW)
rddf builder phase2 <change>           # execute (was guide-ship part)
rddf builder phase2.5 <change>         # review (4-option)
rddf builder phase3 <change>           # archive (was guide-ship part)
rddf planner status                    # was rddf planner status (unchanged)
```

`rddf guide-design`, `rddf guide-plan`, `rddf guide-ship` continue to work
during Wave 2 (deprecation shim) but print stderr warning + log to
`.rddf/state/.shim-usage.jsonl`. They will be REMOVED in Wave 3 (~v4.x.2).

### 3. Update rddf-session intent mappings

If you have `rddf-session` workflows that bind to `intent: guide-design` /
`guide-plan` / `guide-ship`, you have two choices during Wave 2 coexistence:

- **Option A** (recommended): Update your session scripts to use new intents
  `rdd-builder` / `rdd-planner`. The new schema (v3) adds
  `stage_arch` / `stage_planner` / `stage_builder` / `stage_verifier` fields.
- **Option B**: Keep legacy intent names — they remain literal during Wave 2
  (shim to canonical `rdd-builder` is Wave 2 shim layer, not session layer).

### 4. Update `.arch-handoff.json` consumers (if you read it directly)

`.arch-handoff.json` contract bumped v2 → v3. Removed 3 fields:
- top-level `roadmap_path`
- top-level `roadmap_exists`
- nested `discovered.roadmap_path`

If you read these fields, **stop**. Use `.planner-handoff.json` for roadmap
state (managed by `rdd-planner`).

v1/v2 files still parse via `additionalProperties: true` (backward compat).

### 5. Update proposal-suggestions.md workflow (if applicable)

The `.rddf/improvements/*.md` workflow is unchanged. The `## Feedback` section
and `rddf feedback add` CLI work the same way. Only the source field
enumeration gains `rdd-arch` / `rdd-planner` / `rdd-builder` / `rdd-verifier`
options; legacy `guide-design` / `guide-plan` / `guide-ship` remain valid in
Wave 2.

## Deprecation timeline

- **Wave 1** (2026-09-04, this release): new skills available, old skills unchanged
- **Wave 2** (in progress): DEPRECATED banner + stderr warning + `.shim-usage.jsonl` telemetry
- **Wave 3** (~v4.x.2): hard removal of `guide-design` / `guide-plan` / `guide-ship`

### Wave 3 trigger conditions (BOTH must hold)

- **Time**: ≥4 weeks since Wave 1 ship (≥2026-10-04)
- **Usage**: zero `.shim-usage.jsonl` entries for ≥7 consecutive days
  - Verified via `_lib/shim_usage.py::count_shim_usage_recent_days(days=7) == 0`
  - OR `rddf doctor --check stage-merge` (NEW check in Wave 2) reports 0 active users

## Reference

- Spec: `docs/superpowers/specs/2026-09-04-rdd-workflow-v4-architecture-stage-merge.md`
- ADR: `docs/adr/ADR-0043-rdd-workflow-v4-stage-merge.md`
- Oracle review session: `ses_f74594271ffeqRViAn2Vd85RJ9`
- Metis review session: `ses_f9330b34bffeybmxM4J359Yjyq`

## Questions?

Open an issue at the rdd-workflow repo with label `migration-v4`. Include:
- Current v3.x usage pattern
- Which `guide-*` skill / CLI you depend on
- Telemetry from `.rddf/state/.shim-usage.jsonl` (if you have it)