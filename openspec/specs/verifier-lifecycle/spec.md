# verifier-lifecycle Specification

## Purpose
TBD - created by archiving change fix-rdd-verifier-lifecycle-dashboard. Update Purpose after archive.
## Requirements
### Requirement: Verifier queue SHALL discover implemented task-complete non-archived changes

The verifier queue SHALL use the canonical iteration lifecycle and SHALL NOT depend on `ship-done` as a per-change status. A change is eligible when it is non-archived, has a supported implementation lifecycle status, and all tracked tasks are complete. The queue SHALL exclude changes whose implementation is incomplete and changes already archived.

#### Scenario: Completed in-worktree change is queued
- **GIVEN** a change has status `in_worktree`
- **AND** its `tasks_done` equals `tasks_total` and `tasks_total` is greater than zero
- **AND** its verification result is missing or stale for the current branch commit
- **WHEN** the verifier queue is scanned
- **THEN** the change is returned as a verification candidate

#### Scenario: Incomplete implementation is excluded
- **GIVEN** a change has status `in_worktree`
- **AND** `tasks_done` is less than `tasks_total`
- **WHEN** the verifier queue is scanned
- **THEN** the change is not returned

#### Scenario: Archived change is excluded
- **GIVEN** a change has status `archived`
- **WHEN** the verifier queue is scanned
- **THEN** the change is not returned even if old verification metadata exists

### Requirement: rddf rdd-verify SHALL execute real batch verification

The `rddf rdd-verify` command SHALL invoke the ac-verifier backend for each eligible change unless a current valid verdict cache exists. It SHALL persist the verdict and verification state, classify failed acceptance criteria, and return a non-success exit code when any change fails, errors, or reaches the retry limit. An empty queue SHALL be a successful no-op only when the queue is genuinely empty.

#### Scenario: Eligible change is verified
- **GIVEN** the queue contains one eligible change
- **AND** no current verdict cache exists
- **WHEN** `rddf rdd-verify` runs
- **THEN** it invokes ac-verifier
- **AND** writes a verdict cache bound to the implementation commit
- **AND** writes verification state for the change

#### Scenario: Batch contains one failure
- **GIVEN** a batch contains multiple eligible changes
- **AND** one change has a failed acceptance criterion
- **WHEN** `rddf rdd-verify` completes
- **THEN** successful changes retain `passed` verification state
- **AND** the failed change receives `failed` or `halted` state with a route
- **AND** the command exits non-zero

#### Scenario: Empty queue is a successful no-op
- **GIVEN** no non-archived change is implemented and task-complete
- **WHEN** `rddf rdd-verify` runs
- **THEN** it reports an empty queue
- **AND** exits zero without claiming that any change was verified

### Requirement: Batch exit code SHALL aggregate per-change outcomes

`rddf rdd-verify` SHALL compute an aggregate exit code across the batch. Higher-severity outcomes SHALL dominate lower-severity ones, so a single halt masks failures and errors.

#### Scenario: Mixed batch outcome
- **GIVEN** a batch contains one passed change, one failed change, and one halted change
- **WHEN** `rddf rdd-verify` completes
- **THEN** the aggregate exit code is `4` (halted) because halt dominates failure
- **AND** each change retains its individual verification state

#### Scenario: All-pass batch
- **GIVEN** a batch contains only passed changes
- **WHEN** `rddf rdd-verify` completes
- **THEN** the aggregate exit code is `0`

#### Scenario: Error dominates failure
- **GIVEN** a batch contains one failed change and one error change
- **WHEN** `rddf rdd-verify` completes
- **THEN** the aggregate exit code is `3` because error dominates failure

### Requirement: Verification state SHALL be stored per change with layered ownership

Each change SHALL have an optional `verification` object independent of the existing lifecycle `status`. The object SHALL include `state`, `verdict_sha`, `checked_at`, `route`, `loop_count`, `failed_acs`, `bypass_reason`, `bypass_source`, and `archive_ready`. Loop state and audit data SHALL be isolated per change and SHALL NOT overwrite another change's state during batch verification. The four storage layers SHALL have a single source of truth per field.

#### Scenario: Two changes maintain independent loop state
- **GIVEN** two changes fail verification in the same batch
- **WHEN** their failure routes are recorded
- **THEN** each change has its own loop count and classification history
- **AND** updating one change does not alter the other change's route or retry count

#### Scenario: Storage layers do not duplicate authoritative fields
- **GIVEN** the four storage layers exist for a change
- **WHEN** any layer is updated
- **THEN** summary fields (`state`, `archive_ready`, `failed_acs`) live only in iteration
- **AND** retry history and classification live only in per-change loop state
- **AND** raw verdict and `codebase_commit` live only in the canonical cache
- **AND** events live only in the append-only audit log

#### Scenario: Verification state is backward compatible
- **GIVEN** an older iteration entry has no `verification` object
- **WHEN** dashboard, queue discovery, or archive gate reads the entry
- **THEN** it treats the verification state as unknown/pending according to context
- **AND** it does not invalidate the existing lifecycle status

### Requirement: Implementation commit SHALL be the openspec branch tip and bind the verifier to a fail-closed identity

The verifier SHALL use the `openspec/<change>` branch tip as the implementation commit. If the branch does not exist, is detached, or the current branch does not match, verification SHALL fail closed and the change SHALL NOT be eligible for archive. Archive gate SHALL compare against the same commit. Arbitrary execution root HEAD SHALL NEVER be used as an archive authorization commit.

#### Scenario: Branch tip is used as implementation commit
- **GIVEN** the `openspec/<change>` branch exists
- **WHEN** verifier writes the verdict cache
- **THEN** the cache's `codebase_commit` equals the branch tip
- **AND** archive gate compares the cached commit to the branch tip

#### Scenario: Branch missing fails closed
- **GIVEN** no `openspec/<change>` branch exists
- **WHEN** `rddf rdd-verify` evaluates the change
- **THEN** it marks verification as `failed` with reason `branch_missing`
- **AND** it does not pass the change

#### Scenario: Detached HEAD fails closed
- **GIVEN** the verifier runs in a detached HEAD context
- **WHEN** it attempts to resolve the implementation commit
- **THEN** it fails closed
- **AND** writes no cache or passed state

#### Scenario: Lightweight current branch mismatch
- **GIVEN** lightweight execution mode is active
- **AND** the current branch is not `openspec/<change>`
- **WHEN** verifier evaluates the change
- **THEN** it fails closed
- **AND** the change is not archive-eligible

### Requirement: SKIP_RDD_VERIFIER SHALL only produce audited bypass records, never passed

`SKIP_RDD_VERIFIER=yes` SHALL require an explicit `RDDF_VERIFIER_BYPASS_REASON` env var. When set, it SHALL write `verification.state=bypassed` with `bypass_reason` and `bypass_source="SKIP_RDD_VERIFIER"` instead of producing a passed verdict. Without the reason, the command SHALL fail closed with exit code `3`. `SKIP_RDD_VERIFIER` SHALL NOT bypass `FEATURE_ARCHIVE_GATE=hard` or `FORCE_ARCHIVE_INCOMPLETE=yes`.

#### Scenario: Skip with reason produces audited bypass
- **GIVEN** `SKIP_RDD_VERIFIER=yes` is set
- **AND** `RDDF_VERIFIER_BYPASS_REASON=<text>` is set
- **WHEN** `rddf rdd-verify` runs
- **THEN** it writes `verification.state=bypassed`
- **AND** writes `bypass_reason=<text>` and `bypass_source=SKIP_RDD_VERIFIER`
- **AND** writes no `verdict_sha`
- **AND** exits `0` only when at least one eligible change received `bypassed`

#### Scenario: Skip without reason fails closed
- **GIVEN** `SKIP_RDD_VERIFIER=yes` is set
- **AND** `RDDF_VERIFIER_BYPASS_REASON` is missing
- **WHEN** `rddf rdd-verify` runs
- **THEN** it exits `3`
- **AND** it writes no verification state

#### Scenario: Skip does not bypass feature gate
- **GIVEN** `SKIP_RDD_VERIFIER=yes` with reason is set
- **AND** `FEATURE_ARCHIVE_GATE=hard`
- **AND** the change belongs to an incomplete feature
- **WHEN** guide-ship reaches archive finalization
- **THEN** the feature gate still blocks archive

#### Scenario: Skip does not bypass task incompleteness gate
- **GIVEN** `SKIP_RDD_VERIFIER=yes` with reason is set
- **AND** `FORCE_ARCHIVE_INCOMPLETE=yes`
- **WHEN** guide-ship reaches archive finalization
- **THEN** archive_gate_check ignores `FORCE_ARCHIVE_INCOMPLETE` for verifier
- **AND** verifier bypass does not skip tasks gate either

### Requirement: Verification failures SHALL route back to plan or ship

A failed acceptance criterion SHALL be classified as `implementation_gap` or `proposal_drift`, with an explicit user-confirmed route. `implementation_gap` SHALL route to `guide-ship`; `proposal_drift` SHALL route to `guide-plan`. A change that reaches the retry limit SHALL enter `halted` state and SHALL remain unavailable for archive without an explicit audited bypass.

#### Scenario: Implementation gap routes to ship
- **GIVEN** a failed verdict is classified as `implementation_gap`
- **WHEN** the user confirms the classification
- **THEN** verification state becomes `failed`
- **AND** route is `guide-ship`

#### Scenario: Proposal drift routes to plan
- **GIVEN** a failed verdict is classified as `proposal_drift`
- **WHEN** the user confirms the classification
- **THEN** verification state becomes `failed`
- **AND** route is `guide-plan`

#### Scenario: Retry limit blocks archive
- **GIVEN** a change reaches `RDDF_VERIFIER_MAX_LOOPS`
- **WHEN** another verification attempt is requested
- **THEN** verification state becomes `halted`
- **AND** archive readiness is false
- **AND** an audit record identifies the change, commit, route history, and halt reason

