## Why

The rddf-session module uses `_with_file_lock` with `LOCK_NB` (non-blocking fail-fast) for file-level concurrency control, but there are no tests verifying this behavior. Concurrent session creation and cross-session recovery after timeout/orphan scenarios are untested, creating risk of silent data corruption or deadlock-like failures in multi-agent/multi-session workflows.

## What Changes

- Add `tests/integration/test_rddf_session_concurrency.py`: multiprocessing-based concurrency test that spawns 100 parallel `create_session` calls to verify LOCK_NB fail-fast semantics (no queueing, no infinite retry, no corruption)
- Add `tests/integration/test_rddf_session_cross_session_recovery.py`: end-to-end test for session timeout → orphaned session → `find_next_recommendation` + `transfer_ownership` recovery chain
- No changes to `rddf_session.py` logic — strictly test coverage

## Capabilities

### New Capabilities
- `rddf-concurrency-testing`: Multiprocessing-based concurrency test harness for LOCK_NB file locking semantics, covering session creation, state transitions, and cross-session recovery under load

### Modified Capabilities
- `rddf-session`: Extend test coverage to include concurrent access patterns and cross-session recovery lifecycle; requirements remain unchanged but verification scope is expanded

## Impact

- **Tests**: 2 new integration test files under `tests/integration/`
- **Dependencies**: Uses Python built-in `multiprocessing` only — no new external dependencies
- **Runtime**: No changes to production code; test-only change
- **Effort**: ~1.5 days, P1 priority, v2.1 phase, core category