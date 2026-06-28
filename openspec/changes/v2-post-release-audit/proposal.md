## Why

The v2.0.0-beta audit (2026-06-27) identified a structural doc-reality gap: v2.0 code (+169 Python tests) is fully implemented, but the documentation layer was never synchronized. Three docs (ADR README, v2-adr-summary, v2-implementation-plan) still claim v2.0 is "unimplemented." The migration guide references a non-existent `spec-workflow` CLI. INSTALL.md/USAGE.md/README.md have stale version numbers and skill counts. Separately, the audit found a tautological assertion (test_lock.py:19) and 4 production modules with zero test coverage. Without this change, users will encounter broken documentation, non-executable migration instructions, and untested code paths.

## What Changes

- **Fix** `docs/adr/README.md` — update "v2.0 not implemented" → actual per-ADR implementation status
- **Fix** `docs/v2-adr-summary.md` — ADR count 9→12, add missing ADR-0003/0011/0012, remove false "not implemented" claim
- **Fix** `docs/migration/v1-to-v2.md` — replace fictional `spec-workflow migrate/sync/report` CLI references with real skill invocations or "planned" markers
- **Fix** `skills/INSTALL.md` — sync skill count (10→12) and package.json template with current v2.0 state
- **Fix** `USAGE.md` — fix version header (v1.1→v2.0.0-beta), remove duplicate Phase 2 header, fix .zcf state files table
- **Fix** `README.md` — update directory structure to include guide-arch.md, guide-plan.md, _lib/ subdirectory
- **Fix** `tests/unit/test_lock.py:19` — replace tautological `or True` assertion with meaningful check
- **Add** unit tests for 4 untested modules: event_context.py, defaults.py, event_types.py, state.sh
- **Add** CI assertion quality gate (grep for tautological patterns)
- **Promote** 4 orphaned spec directories from archive to openspec/specs/ (release-management, migration-docs, test-suite, three-phase-skills)
- **Fix** `docs/v2-api-reference.md` — session_v20.py→session.py path
- **Fix** `docs/v2-loop-engine.md` — loop-engine.py→loop_engine.py path

## Capabilities

### New Capabilities
- `doc-truth-sync`: All v2.0 documentation reflects actual code implementation status
- `test-coverage-gap-closure`: 4 previously untested modules now covered
- `assertion-quality-gate`: CI blocks tautological assertions

### Modified Capabilities
- `migration-guide` (docs/migration/v1-to-v2.md): Removes fictional CLI, uses real skill invocations
- `lock-test` (tests/unit/test_lock.py): Replaces always-true assertion with meaningful verification
- `v2-adr-summary` (docs/v2-adr-summary.md): Accurate ADR count (12) and implementation status

## Impact

- **Zero** user-facing API changes—documentation-only + test-only fixes
- **Zero** runtime behavior changes—no production code modified
- **Positive**: Users following migration guide will no longer hit `command not found`
- **Positive**: New installs get correct metadata from INSTALL.md template