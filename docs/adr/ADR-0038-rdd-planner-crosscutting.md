# ADR-0038: rdd-planner Horizontal Orchestrator (Stage 2)

> **状态**: 已采纳 (2026-09-03)
> **日期**: 2026-09-03
> **决策者**: sisyphus

## Status

Accepted (2026-09-03) — Stage 2 of `rdd-planner` design, implemented per
`docs/superpowers/specs/2026-09-03-rdd-planner-stage2-design.md`.

> **Stage 2.5 (2026-09-03): P0-1 single AUTO-SPRINT writer.**
> `_lib/roadmap_sprint.update_roadmap` is the sole writer of the
> AUTO-SPRINT block. Planner sync (`_lib.planner_sync.apply_state`)
> delegates via the `table='project'` dispatch. `_lib/loop/actions.py
> ::action_update_roadmap` writes `.rddf/state/roadmap-state.json`
> (no sentinel, no roadmap write) and is **not** a roadmap writer.

> **Stage 2.5 (2026-09-03): P0-3 explicit `planner attach` write path.**
> `rddf planner attach <proposal> --project-id X --phase Y [--theme Z]`
> is the only command besides `rddf feedback add` that may modify
> `.rddf/improvements/*.md`. It operates on **exactly one** file
> under per-file `FileLock` + `atomic_write`, validates `project_id`
> against Phase Skeleton Theme column (and `phase` against Phase
> column / fragment ids via `.rddf/roadmap/phases/*.md` `id`), is
> idempotent for identical mappings, and refuses to overwrite an
> existing divergent mapping without an explicit flag. No bulk
> rewrite is permitted.

## Context

After Stage 1 (ADR-0037 feedback contract) shipped, the codebase has:

- 226 `.rddf/improvements/*.md` files (mostly without `roadmap_ref`)
- `.rddf/roadmap.md` with manual Phase Skeleton but no AUTO-SPRINT block
- No central state for sprint progress or proposal↔roadmap mapping
- 30+ `iteration.corrupt.*` residual files (Oracle review evidence of multi-writer race risk)

A planner/orchestrator role was requested to:
- Maintain roadmap ↔ proposal mapping
- Manage sprint lifecycle
- Read feedback and trigger revisions

## Decision

Implement `rdd-planner` as a **horizontal orchestrator** (NOT a sixth phase):

1. **Position**: Cross-cutting, callable from any phase. Does NOT replace or
   extend the 5-phase architecture (arch → design → plan → ship → verify).

2. **Commands in Stage 2 MVP**:
   - `rddf planner status` — read-only sprint snapshot
   - `rddf planner sync [--apply|--dry-run]` — default dry-run

3. **State file**: New `.rddf/state/.planner-state.json` (gitignored,
   schema v1). Atomic writes via `_lib/core/atomic_write` + `FileLock`.

4. **Roadmap write strategy**: Dual-zone — preserve user-edited Phase
   Skeleton table; only overwrite the AUTO-SPRINT block (between
   `<!-- AUTO-SPRINT-START -->` and `<!-- AUTO-SPRINT-END -->` sentinels).

5. **Improvement file policy**: Read-only on `.rddf/improvements/*.md`.
   All 226 existing files continue to work without migration.

6. **Feedback integration**: Read-only consumer of Stage 1's
   `## Feedback` section via the ADR-0037 contract. No writes to
   improvement files.

7. **Roadmap writer matrix (Stage 2.5)**:
   - `_lib/roadmap_sprint.update_roadmap(roadmap_path, data, *, table="changes"|"project")`
     is the **only** writer of the AUTO-SPRINT block. It acquires a
     per-file `FileLock(<roadmap_path>.lock, timeout=10)` and writes
     atomically (.tmp + rename).
   - `_lib/planner_sync.apply_state` delegates to
     `update_roadmap(..., table="project")`. It does **not** render
     the sprint block itself nor hold its own roadmap lock.
   - `_lib/loop/actions.py::action_update_roadmap` writes
     `.rddf/state/roadmap-state.json` (`{phase, category, updated_at}`)
     and does **not** touch `.rddf/roadmap.md`. It is **not** a
     roadmap writer and shares no lock.

## Consequences

### Positive

- ✅ Sprint concept now first-class (was implicit in roadmap_sprint.py).
- ✅ Single source of truth for active projects.
- ✅ Dual-zone write preserves user manual edits to Phase Skeleton.
- ✅ Zero migration burden on 226 existing improvement files.
- ✅ Idempotent (default dry-run; --apply writes are atomic).
- ✅ Follows 5-phase architecture (no phase pollution).

### Negative

- ⚠️ Adds ~700 lines of Python (state + sync + CLI + ~25 tests).
- ⚠️ `revise` and `audit` subcommands deferred to Stage 2.5.
- ⚠️ `--apply` requires manual flag — accidental writes are avoided but
  user must remember to add flag.

### Neutral

- Stage 3 (`rdd-arch` rename) builds on this contract.
- Stage 4 (no-merge) does not affect this contract.

## Alternatives Considered

1. **Sixth phase `rdd-planner`** — rejected (per Oracle review, 5-phase
   architecture is stable; adding a phase creates governance debt).
2. **Inline planner in `guide-arch`** — rejected (creates 2 writers of
   `.rddf/roadmap.md`, exactly the multi-writer corruption scenario).
3. **SQLite-backed state** — rejected (out of scope for Stage 2; adds
   heavy dependency for ~100 lines of JSON state).

## References

- Spec: `docs/superpowers/specs/2026-09-03-rdd-planner-stage2-design.md`
- Plan: `docs/superpowers/plans/2026-09-03-rdd-planner-stage2.md`
- ADR-0037: feedback contract (Stage 1, hard dependency)
- ADR-0028: role-model per phase
- `_lib/core/atomic_write.py` and `_lib/core/lock.py` (proven primitives)
- `_lib/roadmap_sprint.py` (AUTO-SPRINT block renderer, reused)
- `.rddf/state/iteration.corrupt.*` (the failure mode this ADR prevents)

## Supersedes

None. Additive contract. Stage 1 ADR-0037 remains in force.