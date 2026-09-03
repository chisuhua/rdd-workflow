# ADR-0037: Feedback Contract for `.rddf/improvements/*.md`

> **状态**: 已采纳 (2026-09-03)
> **日期**: 2026-09-03
> **决策者**: sisyphus

## Status

Accepted (2026-09-03) — Stage 1 of `rdd-planner` design, implemented per
`docs/superpowers/specs/2026-09-03-rdd-planner-stage1-feedback-contract.md`.

> **Stage 2.5 (2026-09-03): P0-2 in-place resolution + latest-entry parser.**
> `rddf feedback resolve <proposal> <feedback_id>` mutates only the
> selected entry's `resolution: open` to `resolved`, adding `resolved_at`
> and `resolved_by`. The append-only contract applies to **creation** of
> new entries, not to resolution status updates. The parser derives
> `feedback_status` by reading frontmatter `last_feedback_id` and
> selecting that exact `### feedback-<id>` block; missing pointer →
> `none`. Precedence is resolution before kind. Status enum: `none |
> needs-revision | rejected | resolved | noted`. `noted` covers
> `blocked` and `noted` kinds.

## Context

Current `.rddf/improvements/*.md` files (226 in the codebase) lack:

1. Stable ID linking improvement ↔ OpenSpec change ↔ AC verdict.
2. A defined mechanism for downstream skills (`guide-design`, `guide-plan`,
   `guide-ship`, `rdd-verifier`) to write back feedback.
3. A loop-termination guard for iterative revision cycles.

This caused `iteration.corrupt.*` residual files in `.rddf/state/`
(multi-writer race on shared state) and made cross-phase feedback
propagation ad-hoc.

The new `rdd-planner` skill (Stage 2 of the rdd-workflow 4-phase migration)
needs a single writer contract to avoid further state corruption.

## Decision

Adopt an **append-only feedback contract** with the following properties:

1. **Single writer**: All `## Feedback` writes go through
   `_lib.feedback_appender.append_feedback()`, exposed as
   `rddf feedback add` CLI.

2. **Stable IDs**: Each entry has `feedback-YYYYMMDD-NNN` ID; counters
   persist in `.rddf/improvements/.feedback-counters.json` (one JSON
   map keyed by file basename).

3. **ID resolution**: Proposal → change-name via 3-tier priority:
   explicit `--ref-change` > frontmatter `change:` > basename equality.

4. **Loop guard**: Frontmatter `revision_count` increments on
   `needs-revision` / `ac-fail`; cap `max_revisions=3` (mirrors
   ADR-0034 verifier ceiling). Exceeding cap raises
   `LoopExceededError` and forces human escalation.

5. **Atomic writes**: All writes via `_lib/core/atomic_write` +
   `_lib/core/lock.FileLock` (timeout=10s) to prevent the
   iteration-corrupt failure mode observed in `.rddf/state/`.

6. **Backward compatible**: All new frontmatter fields are opt-in;
   existing 226 files continue to work unchanged.

## Consequences

### Positive

- Stable cross-phase feedback propagation.
- No multi-writer corruption (proven pattern from state-vector).
- Loop termination enforced (matches verifier 3-retry ceiling).
- Zero impact on existing files.

### Negative

- Adds ~700 lines of Python (resolver + appender + CLI + 39 tests).
- Future stages (2-4) build on this contract; if contract needs
  revision, downstream skills must be re-tested.
- Counter file `.feedback-counters.json` is per-improvement-dir;
  cross-project collision possible if not scoped to `project_root`.

### Neutral

- Stage 2 (`rdd-planner`) will consume this contract as its primary input.
- Stage 3 (`rdd-arch` rename) and Stage 4 (no-merge) do not affect
  this contract.

## Alternatives Considered

1. **Per-skill direct file writes** — rejected (multi-writer corruption,
   ADR-0028 role-model violation).
2. **Centralized database (SQLite)** — rejected (out of scope for
   Stage 1; adds heavy dependency).
3. **Read-only feedback (no write)** — rejected (does not solve the
   cross-phase propagation gap).

## Implementation

- **Resolver**: `_lib/feedback_resolver.py::resolve_change_id()` (read-only)
- **Appender**: `_lib/feedback_appender.py::append_feedback()` (single writer)
- **CLI**: `_lib/cli/feedback_cmd.py::cmd_feedback()` (dispatcher)
- **Schemas**: `_lib/schemas/feedback_entry_schema.json` v1,
  `_lib/schemas/improvement_frontmatter_schema.json` v2 (additive)
- **Tests**: `tests/unit/test_feedback_{resolver,appender,cli}.py` (30 tests),
  `tests/integration/test_feedback_cmd.bats` (9 tests)

## References

- Spec: `docs/superpowers/specs/2026-09-03-rdd-planner-stage1-feedback-contract.md`
- Plan: `docs/superpowers/plans/2026-09-03-rdd-planner-stage1-feedback-contract.md`
- ADR-0034: rdd-verifier 3-retry ceiling
- ADR-0028: role-model per phase
- `_lib/core/atomic_write.py` and `_lib/core/lock.py` (proven primitives)
- `.rddf/state/iteration.corrupt.*` (the failure mode this ADR prevents)

## Supersedes

None. Additive contract.