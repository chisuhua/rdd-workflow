## Implementation Tasks

### Schema, State, and Storage Contract

- [ ] 1. Bump iteration schema to v7. Allow `version` to include `7` while keeping v3–v6 readable. Add an optional `verification` object under `changes.items.properties` with explicit enum and nullability for `state`, `verdict_sha`, `checked_at`, `route`, `loop_count`, `failed_acs`, `bypass_reason`, `bypass_source`, and `archive_ready`. Reject invalid values. Update `iteration_schema.json` and schema-version tests.
- [ ] 2. Replace the global `.verifier-loop.json` with per-change loop state under `.rddf/state/verifier/<change-name>.json`. Migrate legacy single-file state only when the legacy `change` field matches the sole eligible change. Add atomic write helpers and tests proving two changes cannot overwrite each other's retry history.
- [ ] 3. Add storage-layer ownership helpers for iteration summary fields, per-change loop fields, canonical cache fields, and audit events. Enforce the write order: loop → cache → iteration summary → audit. Ensure no layer is silent about which fields it owns.
- [ ] 4. Extend the canonical verdict cache schema and `_lib/verifier/cache.py` to add `verification_state`, `failed_acs`, `source`/`ran_by`, `schema_version`, and optional `implementation_ref`. Ensure cache reads/writes use argv or environment variables, never shell-to-Python interpolation.

### Discovery and Branch Identity

- [ ] 5. Replace `ship-done` queue discovery in `scan_queue.sh` and `rdd_verify_cmd.py` with real eligible-change discovery based on non-archived lifecycle status plus complete task counters. Add tests using valid `in_worktree`/`completed` fixtures.
- [ ] 6. Implement the implementation-commit resolver that returns the `openspec/<change>` branch tip when present, or the lightweight current branch when it matches. Fail closed when the branch is missing, detached, or mismatched. Add tests covering branch-missing, detached-HEAD, and lightweight-mismatch scenarios.

### Verifier Execution

- [ ] 7. Implement real `rddf rdd-verify` orchestration: discover candidates, mark verification running, invoke ac-verifier on cache miss/stale results, persist verdict cache and verification state, classify failures using the existing pure classifier, compute aggregate exit code (`halted > error > failed > bypassed/passed`), and return non-zero on any failure.
- [ ] 8. Wire `run_verification.sh` and the CLI to write production verdict caches through `_lib/verifier/cache.py` with `verification_state`, `failed_acs`, `codebase_commit`, `ran_by`, and `schema_version`. Align usage/skip/error exit codes across CLI, helper, and ac-verifier.
- [ ] 9. Implement user-confirmed heuristic failure routing with `implementation_gap` → `guide-ship` and `proposal_drift` → `guide-plan`. Implement explicit `halted` state when `RDDF_VERIFIER_MAX_LOOPS` is reached, with append-only audit log containing change, commit, route history, and halt reason.
- [ ] 10. Implement `SKIP_RDD_VERIFIER=yes` audited bypass: require `RDDF_VERIFIER_BYPASS_REASON` env var, write `bypass_source=SKIP_RDD_VERIFIER` plus `bypass_reason`, refuse to run without the reason (exit `3`), and prove it does not weaken `FEATURE_ARCHIVE_GATE=hard` or `FORCE_ARCHIVE_INCOMPLETE=yes`.

### Archive Gate and Guide-Ship Handoff

- [ ] 11. Update `_lib/archive.sh::archive_gate_check` to consume the canonical verifier contract: require `verification.state=passed` (or audited `bypassed`) plus matching `verdict_sha`; reject missing/stale/failed/halted; route `STRICT_AC_GATE` only to legacy direct ac-verifier fallback; ensure `SKIP_RDD_VERIFIER` never lets a failed cache pass.
- [ ] 12. Make archive cache lookup canonical across lightweight and worktree modes. Resolve cache path through `main_repo_root()`; pass paths via argv/environment variables; remove shell-to-Python interpolation. Add tests for cache hit, stale cache, worktree mode, failed verdict, and direct archive invocation.
- [ ] 13. Implement structured ac-verifier fallback output: parse ac-verifier JSON output, write the cache with `ran_by=archive_gate_check`, include `verification_state`, `failed_acs`, and `implementation_ref`. Block archive on cache-write failure even when the verdict passed. Treat exit code `2` (skipped/no AC) as no cache written.
- [ ] 14. Update guide-ship archive orchestration to call rdd-verifier before merge, read verification state, and pass through only when archive readiness is true. Update documentation to document the handoff and add negative-assertion tests that rdd-verifier never deletes branches, removes worktrees, or moves `openspec/changes/<change>`.

### Archive Synchronization

- [ ] 15. Update `mark_iteration_archived` to preserve `verification` and only add `archived_at`. Add tests proving `clean-stale-plan-handoff-on-ship-done`, plan-file cleanup, and post-archive cleanup do not delete `.rddf/state/verifier/`, `.rddf/state/.ac-verdict-<change>.json`, or the audit log.
- [ ] 16. Add audit log writer and JSONL schema for verifier events (running, failed, halted, bypassed, archive-ready), each with timestamp, change name, and the relevant commit.

### Dashboard

- [ ] 17. Extend `_lib/dashboard/__init__.py::ChangeEntry` with the structured `verification` object and derived `archive_ready` boolean. Backward compatible with historical entries. Add readers and tests for missing `verification`, `legacy`, and `bypassed` data.
- [ ] 18. Update terminal, plain, and JSON dashboard renderers to show implementation, verification, and archive dimensions. Add a short verification code column and a detail line for failed ACs and route. Define an icon map covering all eight states for terminal and plain modes. Ensure long change names are truncated on the right, never on the verification summary.
- [ ] 19. Add dashboard tests covering all eight derived states, JSON field stability, plain/terminal readability, failed AC display, halted display, bypass display, and legacy archived changes. Avoid string-prefix matching; assert structured fields.

### Documentation, ADR, and Final Validation

- [ ] 20. Update ADR-0034, `skills/rdd-verifier/SKILL.md`, guide-ship documentation, iteration schema documentation, and dashboard documentation. Remove invalid `ship-done`/`in-progress`/`verified` references and document the final lifecycle contract, gate precedence, branch identity, fallback contract, and storage ownership.
- [ ] 21. Replace fabricated `ship-done` rdd-verifier fixtures with valid production lifecycle fixtures. Add integration coverage for non-empty queue execution, real cache writes, batch aggregation, per-change isolation, bypass, and meaningful aggregate exit codes.
- [ ] 22. Run focused unit and integration tests, then the repository-mandated `./test.sh --full --regression` before archive. Record any pre-existing baseline failures separately from new failures.