# archive-gate-verification Specification

## Purpose
TBD - created by archiving change fix-rdd-verifier-lifecycle-dashboard. Update Purpose after archive.
## Requirements
### Requirement: Archive SHALL remain owned by guide-ship

`guide-ship` SHALL continue to own merge, `openspec archive`, archive-side commits, branch deletion, worktree cleanup, iteration synchronization, and post-archive cleanup. `rdd-verifier` SHALL produce and record verification results but SHALL NOT perform those delivery operations.

#### Scenario: Verification passes before archive finalization
- **GIVEN** guide-ship execution has produced a task-complete implementation
- **AND** rdd-verifier has recorded `verification.state=passed`
- **AND** the verdict SHA matches the current `openspec/<change>` branch tip
- **WHEN** guide-ship enters archive finalization
- **THEN** guide-ship may merge, archive, synchronize state, and clean branch/worktree

#### Scenario: Verification has not passed
- **GIVEN** a change is task-complete but verification is missing, stale, failed, or halted
- **WHEN** guide-ship enters archive finalization
- **THEN** archive finalization is blocked
- **AND** the output identifies the verification state and required next route

#### Scenario: Negative assertion: verifier must not perform delivery operations
- **GIVEN** `rddf rdd-verify` runs
- **WHEN** it completes any batch
- **THEN** it does not delete any `openspec/<change>` branch
- **AND** it does not remove any worktree
- **AND** it does not move `openspec/changes/<change>` to `openspec/changes/archive/`
- **AND** it does not call `mark_iteration_archived`

### Requirement: Archive gate SHALL consume commit-bound verifier results

The archive gate SHALL accept a cached verifier result only when it belongs to the same change and matches the current implementation branch tip. Cache lookup SHALL work in both lightweight and worktree execution modes using one canonical project state location. Cache reads and writes SHALL pass paths through environment variables or argv rather than interpolating paths into Python source.

#### Scenario: Current passing verdict permits archive
- **GIVEN** a current verdict cache exists for the change
- **AND** its verdict is all pass
- **AND** its SHA matches the branch tip
- **WHEN** `archive_gate_check` runs
- **THEN** it skips a duplicate LLM invocation
- **AND** reports archive readiness

#### Scenario: Stale verdict blocks archive readiness
- **GIVEN** a verdict cache exists but its SHA differs from the branch tip
- **WHEN** `archive_gate_check` runs
- **THEN** the cache is not accepted as verification
- **AND** the gate requires a fresh verification result

#### Scenario: Cached failure blocks strict archive
- **GIVEN** a current cached verdict contains a failed AC
- **AND** strict verification is enabled
- **WHEN** `archive_gate_check` runs
- **THEN** it returns non-zero
- **AND** it reports the failed ACs and route information

#### Scenario: Cache path is canonical across execution modes
- **GIVEN** the change is being archived in worktree mode
- **WHEN** verifier writes the verdict cache and archive_gate reads it
- **THEN** both write and read resolve the same path under the main project state directory
- **AND** no path interpolation occurs in Python source

### Requirement: Gate precedence SHALL be deterministic across skip, strict, bypass, and feature options

The archive gate SHALL compose verifier results with `SKIP_RDD_VERIFIER`, `SKIP_AC_VERIFICATION`, `STRICT_AC_GATE`, `FORCE_ARCHIVE_INCOMPLETE`, `RDDF_VERIFIER_BYPASS_REASON`, and `FEATURE_ARCHIVE_GATE`. `STRICT_AC_GATE` SHALL NOT override verifier result validity: it only governs the legacy direct ac-verifier fallback path. Verifier bypass SHALL NOT bypass `FEATURE_ARCHIVE_GATE` or `FORCE_ARCHIVE_INCOMPLETE`.

#### Scenario: STRICT_AC_GATE does not override verifier results
- **GIVEN** a current cached verdict contains a failed AC
- **AND** `STRICT_AC_GATE=no`
- **WHEN** archive_gate_check runs
- **THEN** it blocks because verifier result validity is independent of `STRICT_AC_GATE`

#### Scenario: Verifier bypass does not skip feature gate
- **GIVEN** `verification.state=bypassed`
- **AND** `FEATURE_ARCHIVE_GATE=hard`
- **AND** the change belongs to an incomplete feature
- **WHEN** guide-ship reaches archive finalization
- **THEN** feature gate still blocks archive

#### Scenario: Verifier bypass does not skip tasks gate
- **GIVEN** `verification.state=bypassed`
- **AND** `FORCE_ARCHIVE_INCOMPLETE=yes` is not set
- **AND** the change has uncompleted tasks
- **WHEN** guide-ship reaches archive finalization
- **THEN** archive_gate_check still blocks because tasks are incomplete

#### Scenario: Direct archive fallback without proposal
- **GIVEN** no `proposal.md` exists for the change
- **WHEN** archive_gate_check runs
- **THEN** it skips AC verification entirely
- **AND** it does not write a passed verdict
- **AND** it does not block on missing verifier

#### Scenario: Direct archive fallback ac-verifier error
- **GIVEN** `proposal.md` exists
- **AND** ac-verifier invocation errors (exit code 3)
- **WHEN** archive_gate_check runs
- **THEN** it treats the error as a warning by default
- **AND** writes `verification.state=unknown` with `bypass_source=archive_gate_fallback_error`
- **AND** archive proceeds only when `STRICT_AC_GATE=no`

### Requirement: Direct archive fallback SHALL write structured verdict to the canonical cache

When `archive_gate_check` invokes ac-verifier directly and ac-verifier produces a structured verdict (exit code 0 or 1), the gate SHALL parse the verdict and write it to the canonical cache with `ran_by=archive_gate_check`. The cache entry SHALL include `verification_state`, `failed_acs`, and the implementation commit. Failure to write the cache SHALL NOT promote a failed verdict to passed.

#### Scenario: Direct fallback succeeds and writes cache
- **GIVEN** a `proposal.md` exists
- **AND** the cache is missing or stale
- **WHEN** archive_gate_check invokes ac-verifier
- **AND** ac-verifier produces a structured verdict
- **THEN** the gate writes the verdict to the canonical cache with `ran_by=archive_gate_check`
- **AND** sets `verification_state` accordingly

#### Scenario: Direct fallback cache write fails
- **GIVEN** the verdict is a passing verdict
- **AND** the cache write fails (permission, disk, etc.)
- **WHEN** archive_gate_check evaluates the result
- **THEN** it does not promote the verdict to passed
- **AND** it blocks archive

#### Scenario: Direct fallback ac-verifier returns no structured verdict
- **GIVEN** ac-verifier returns exit code 0 or 1 without producing a parseable verdict JSON
- **WHEN** archive_gate_check runs
- **THEN** it logs a warning
- **AND** it does not write a cache
- **AND** it does not promote to passed

### Requirement: Archive bypass SHALL be explicit and auditable

Skipping or bypassing verification SHALL not be indistinguishable from a normal pass. A bypass SHALL record the bypass reason, change, implementation commit, timestamp, and initiating option or environment variable. Historical archived changes without verification metadata SHALL be shown as legacy/unknown rather than silently marked passed.

#### Scenario: Explicit bypass archives with audit state
- **GIVEN** a user enables the documented verifier bypass
- **WHEN** guide-ship completes archive
- **THEN** the change is marked `verification.state=bypassed`
- **AND** an audit record is written
- **AND** dashboard labels the archived change as bypassed

#### Scenario: Legacy archive has no verifier metadata
- **GIVEN** an archived change predates verifier metadata
- **WHEN** archive state is displayed
- **THEN** it is shown as legacy/unknown verification
- **AND** it is not falsely labeled as verified

### Requirement: Archive synchronization SHALL preserve verification metadata

`mark_iteration_archived`, plan-handoff cleanup, plan-file cleanup, and post-archive cleanup SHALL NOT remove, mutate, or invalidate verification state, loop state, verdict cache, or audit records. `archived_at` SHALL be recorded alongside, not instead of, verification metadata.

#### Scenario: mark_iteration_archived preserves verification
- **GIVEN** a change has `verification.state=passed` and `verdict_sha=X`
- **WHEN** archive finalization runs
- **THEN** after `mark_iteration_archived`, the change entry still contains `verification.state=passed`
- **AND** `verification.verdict_sha` still equals `X`
- **AND** `archived_at` is added without removing verification

#### Scenario: Bypassed archive preserves bypass evidence
- **GIVEN** a change has `verification.state=bypassed` with `bypass_reason`
- **WHEN** archive finalization runs
- **THEN** after `mark_iteration_archived`, `verification.state=bypassed` and `bypass_reason` remain intact

#### Scenario: Clean-stale-plan-handoff does not affect verification
- **GIVEN** a change has verification metadata
- **WHEN** `clean-stale-plan-handoff-on-ship-done` runs
- **THEN** `.rddf/state/verifier/<change>.json` and `.rddf/state/.ac-verdict-<change>.json` remain intact
- **AND** only plan-handoff state is mutated

#### Scenario: Post-archive cleanup does not affect verification
- **GIVEN** a change has verification metadata
- **WHEN** post-archive cleanup runs
- **THEN** verifier namespace and audit records remain intact
- **AND** only archive residue (deleted-tracked paths, modified critical paths) is processed

