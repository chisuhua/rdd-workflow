# ADR-0041: Planner Sprint Lifecycle and History Storage

> **状态**: 已采纳 (2026-09-03)
> **日期**: 2026-09-03
> **决策者**: sisyphus

## Context

Stage 2.5 introduced sprint tracking, proposal attach, and diff capabilities. However:
1. `current_sprint` had no explicit lifecycle transition mechanism.
2. Sprint closure risked losing audit trail without persistent snapshot storage.
3. Concurrent sprint advance operations faced lost-update risks.

## Decision

1. **Sprint Advancement (`advance-sprint`)**:
   - Enforce forward-only progression (`new_sprint > old_sprint`) by default.
   - Atomic state transitions via `update_state` read-modify-write under `FileLock`.
   - On advance, write pre-closure snapshot to history before mutating state.
   - Reset `sprint_started_at` to the advancement timestamp.
   - Automatically refresh roadmap AUTO-SPRINT section via canonical writer.

2. **History Storage (`planner history`)**:
   - Store historical sprint records in `.rddf/state/.planner-history.jsonl` (gitignored).
   - Append-only write under FileLock.
   - Line-by-line parsing with corruption tolerance (skip & warn on corrupt records).
   - Unlimited retention by default; explicit pruning via `--prune-keep N [--apply]`.

3. **Authority Hierarchy**:
   - `## Phase Skeleton` Theme column remains primary.
   - Phase fragment `主题` serves as fallback, emitting a warning upon conflict.

## Consequences

- ✅ Full audit trail for past sprint performance and project allocations.
- ✅ Zero state corruption from concurrent advance or sync operations.
- ✅ Preserves schema version 1 backward compatibility.
- ⚠️ Adds `.planner-history.jsonl` file management.
