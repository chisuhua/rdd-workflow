## Why

`RddfSessionCoordinator` in `skills/_lib/rddf_session.py` has grown to 507 lines — a self-admitted god class combining store operations, command routing, binding management, and type definitions. This monolithic structure makes testing harder, contributes to merge conflicts, and obscures the session lifecycle contract. Splitting it now, before v2.1 feature work adds more surface area, prevents further technical debt accumulation.

## What Changes

- Split `rddf_session.py` into 5 focused modules under `skills/_lib/rddf_session/`:
  - **`facade.py`** — Public API surface, delegates to internal modules. All existing public method signatures (`list`, `show`, `resume`, `abandon`, `archive-history`, `current`) are preserved unchanged.
  - **`_store.py`** — Session persistence: read/write `sessions.json`, atomic file operations, state validation.
  - **`_commands.py`** — Business logic for each rddf-session subcommand: lifecycle transitions, conflict detection, session selection.
  - **`_binding.py`** — Session-to-OpenCode-session binding logic: `owner_opencode_session_id` management, cross-session conflict resolution (4-option soft prompt per ADR-0017 §3).
  - **`_types.py`** — Type definitions, dataclasses, and constants used across modules.
- `facade.py` re-exports all public symbols so import paths like `from skills._lib.rddf_session import RddfSessionCoordinator` continue to work.
- Module-level `__init__.py` is **not** created — the facade file is the single public entry point, preserving the existing import contract.

## Capabilities

### New Capabilities
- `rddf-session-modular`: Modular session coordinator architecture — defines the internal module boundaries (store, commands, binding, types) and the facade re-export contract. This is a pure refactoring capability; no new user-facing features are introduced.

### Modified Capabilities
<!-- No spec-level requirement changes — this is a pure internal refactoring that preserves all public APIs and behavior. -->

## Impact

- **Affected file**: `skills/_lib/rddf_session.py` (507 lines) — split into `skills/_lib/rddf_session/facade.py`, `_store.py`, `_commands.py`, `_binding.py`, `_types.py`
- **No public API changes**: All `RddfSessionCoordinator` method signatures, class name, and import paths are preserved
- **No schema changes**: `sessions.json` schema, `iteration.json` schema unaffected
- **No test changes needed**: All existing 24+10 tests must pass with zero modification
- **No call-site changes**: All consumers (guide-arch, guide-plan, guide-ship, rddf-session skill) continue to import from the same path