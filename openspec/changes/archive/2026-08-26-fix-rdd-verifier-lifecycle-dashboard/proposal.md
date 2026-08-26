## Why

The initial `rdd-verifier` phase is present but does not form a working pre-archive gate. Its queue scanners look for the non-existent per-change status `ship-done`, the CLI returns success without invoking `ac-verifier`, verdict caches have no production writer, and a single loop-state file can overwrite state for multiple changes. As a result, a change can appear successfully verified without verification actually taking place, while the archive path still owns the only effective AC check.

The dashboard also exposes only implementation/lifecycle status and cannot distinguish an implemented change awaiting verification, a failed or halted verification, a verified archive-ready change, or an archived change that bypassed verification.

## What Changes

- Align verifier discovery with the real iteration lifecycle: identify implemented, task-complete, non-archived changes without using `ship-done` as a per-change status.
- Make `rddf rdd-verify` execute the real batch verification flow, persist verdicts, classify failures, update per-change loop state, and return non-success exit codes when verification fails or halts.
- Persist verdict caches from the production verifier path, bind them to the relevant branch/worktree commit, and make archive gate cache lookup work consistently in lightweight and worktree modes.
- Change loop state to be per-change so batch verification cannot overwrite another change's retry history.
- Keep merge, `openspec archive`, branch deletion, worktree cleanup, and archive-side synchronization owned by `guide-ship`, but require a current passing verification result before archive proceeds.
- Remove shell-to-Python path interpolation in the changed verifier/cache paths and make bypass behavior explicit and auditable.
- Add an independent verification object to dashboard change data and render distinct implementation, verification, and archive states in terminal, plain, and JSON output.
- Update lifecycle documentation, schemas, tests, and the rdd-verifier skill contract to match the implemented flow.

## Capabilities

### New Capabilities

- Per-change verification lifecycle state with `pending`, `running`, `passed`, `failed`, `halted`, and `bypassed` states.
- Batch `rddf rdd-verify` execution for implemented, task-complete, non-archived changes.
- Per-change verifier loop state and commit-bound verdict cache.
- Dashboard distinction between implementation completion, verification outcome, and archive outcome.

### Modified Capabilities

- `rdd-verifier` phase: becomes a functional verification and routing phase rather than a queue/scaffolding wrapper.
- `guide-ship` phase: retains finalization responsibilities but blocks merge/archive unless verification has passed for the current branch commit, except for an explicit audited bypass.
- Archive gate: consumes valid verifier results without duplicate LLM calls and remains a defensive backstop for direct archive invocation.
- Iteration state: preserves the existing lifecycle status enum and adds an optional verification object to change entries.
- Dashboard: adds verification-aware fields, labels, icons, and grouping while retaining existing lifecycle statuses.

## Impact

Affected code includes `_lib/cli/rdd_verify_cmd.py`, `_lib/verifier/`, `skills/rdd-verifier/`, `skills/guide-ship/` archive integration, `_lib/archive.sh`, iteration schemas/readers, dashboard collection/rendering, installation/skill metadata, and related unit/integration tests.

Existing `rddf ac-verify <change>` remains a single-change diagnostic entry point. It is not removed or made dependent on the batch phase. `rddf rdd-verify` becomes the workflow phase entry point and archive readiness is determined by a passing verifier record bound to the current implementation commit.

Changes that have already been archived remain readable. Missing verification metadata on historical archived changes is displayed as legacy/unknown rather than being rewritten retroactively.
