## Context

`RddfSessionCoordinator` in `skills/_lib/rddf_session.py` has grown to 507 lines — a god class combining store operations, command routing, binding management, and type definitions. This monolithic structure complicates testing, increases merge conflicts, and obscures the session lifecycle contract. Splitting before v2.1 feature work prevents further technical debt accumulation.

## Goals/Non-Goals

**Goals**: Split into 5 focused modules under `skills/_lib/rddf_session/`:
- `facade.py` — Public API surface, delegates to internal modules
- `_store.py` — Session persistence (read/write `sessions.json`, atomic ops, state validation)
- `_commands.py` — Business logic (lifecycle transitions, conflict detection, selection)
- `_binding.py` — Session-to-OpenCode-session binding (`owner_opencode_session_id` management, cross-session conflict resolution per ADR-0017 §3)
- `_types.py` — Type definitions, dataclasses, constants

**Non-Goals**: No schema changes to `sessions.json`/`iteration.json`. No public API signature changes. No test changes needed. No call-site changes.

## Decisions

- **Facade pattern**: `facade.py` re-exports all public symbols so existing import paths (`from skills._lib.rddf_session import RddfSessionCoordinator`) continue to work. No `__init__.py` — the facade file is the single public entry point.
- **Internal module prefix**: Underscore-prefixed names (`_store.py`, `_commands.py`, `_binding.py`, `_types.py`) signal internal-only modules.
- **Responsibility split by lifecycle concern**: Store (persistence) → Commands (business logic) → Binding (cross-session) → Types (shared data) — clean separation that maps to ADR-0017's session lifecycle stages.

## Risks/Trade-offs

- **Medium risk**: Pure refactoring with zero behavioral change — requires regression of all 24+10 existing tests. Any missed import in the facade re-export will cause runtime `ImportError`.
- **Benefit**: Reduced per-file complexity (~100-150 lines each vs 507) makes v2.1 feature work (e.g., new subcommands, enhanced conflict resolution) significantly easier to implement and review.
- **Effort**: ~1.5 days. Risk mitigated by executing the split in a single atomic commit with the facade re-export verified first.