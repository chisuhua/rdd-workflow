# fix-rdd-verifier-lifecycle-dashboard Implementation Plan

**Goal:** Connect rdd-verifier to real lifecycle discovery, per-change state, commit-bound caches, archive readiness, and dashboard verification state.

**Architecture:** Canonical Python implementation lives under `_lib/verifier/`; iteration summary is optional and backward-compatible. The CLI performs serial batch verification and writes loop state, cache, summary, and audit records. Archive and dashboard consume the same contract.

**Tech Stack:** Python 3.11+, jsonschema, pytest, bash, git.

## Execution Tasks

- [ ] Task 1: Add iteration schema v7 verification object and preserve v3-v6 compatibility.
- [ ] Task 2: Move verifier loop state to per-change files with legacy migration.
- [ ] Task 3: Extend verdict cache to schema v2.
- [ ] Task 4: Add append-only per-change audit events.
- [ ] Task 5: Resolve implementation commit from openspec/<change>.
- [ ] Task 6: Discover implemented, task-complete, non-archived changes.
- [ ] Task 7: Execute real serial batch rdd-verify orchestration.
- [ ] Task 8: Persist production verdict cache fields.
- [ ] Task 9: Route classifications and halt at retry limit.
- [ ] Task 10: Require and record audited verifier bypass reason.
- [ ] Task 11: Enforce verifier contract in archive readiness.
- [ ] Task 12: Use canonical main-repository cache lookup.
- [ ] Task 13: Support structured direct-verifier fallback cache writes.
- [ ] Task 14: Keep archive and cleanup ownership in guide-ship.
- [ ] Task 15: Preserve verification during archive iteration sync.
- [ ] Task 16: Validate audit event schema and retention behavior.
- [ ] Task 17: Add verification data to dashboard ChangeEntry.
- [ ] Task 18: Render verification state in terminal, plain, and JSON output.
- [ ] Task 19: Cover all eight derived dashboard states.
- [ ] Task 20: Update ADR and skill lifecycle documentation.
- [ ] Task 21: Replace fabricated fixtures with valid lifecycle fixtures.
- [ ] Task 22: Run focused tests and repository regression gate.

Each task follows TDD: write a focused failing test, verify failure, implement the smallest change, verify pass, and defer commit until the user explicitly requests integration.
