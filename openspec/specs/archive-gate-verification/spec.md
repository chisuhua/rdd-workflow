# archive-gate-verification Specification

## Purpose
TBD - created by archiving change fix-rdd-verifier-lifecycle-dashboard. Update Purpose after archive.

## Requirements

### Requirement: Archive SHALL remain owned by the builder stage

> **Re-pointed (2026-11-17, per ADR-0036 AMENDED)**: the owner was `guide-ship`,
<!-- v4-residue:allow=history -->
> which was removed in the v4 stage merge (ADR-0043 / ADR-0044 / ADR-0048); the
> v4 owner is `rdd-builder`.

`rdd-builder` SHALL own merge, `openspec archive`, archive-side commits, branch deletion, worktree cleanup, iteration synchronization, and post-archive cleanup. `rdd-verifier` SHALL produce and record verification results but SHALL NOT perform those delivery operations.

#### Scenario: Verification passes before archive finalization
- **GIVEN** rdd-builder execution has produced a task-complete implementation
- **AND** rdd-verifier has recorded `verification.state=passed`
- **AND** the verdict SHA matches the current `openspec/<change>` branch tip
- **WHEN** rdd-builder enters archive finalization
- **THEN** rdd-builder may merge, archive, synchronize state, and clean branch/worktree

#### Scenario: Verification has not passed
- **GIVEN** a change is task-complete but verification is missing, stale, failed, or halted
- **WHEN** rdd-builder enters archive finalization
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

The archive gate SHALL compose verifier results with `SKIP_RDD_VERIFIER`, `SKIP_AC_VERIFICATION`, `STRICT_AC_GATE`, `FORCE_ARCHIVE_INCOMPLETE`, `RDDF_VERIFIER_BYPASS_REASON`, and `FEATURE_ARCHIVE_GATE`. `STRICT_AC_GATE` SHALL NOT override verifier result validity: it only governs the cached-verdict path (the direct subprocess fallback was removed in v2.0 per ADR-0045). Verifier bypass SHALL NOT bypass `FEATURE_ARCHIVE_GATE` or `FORCE_ARCHIVE_INCOMPLETE`.

#### Scenario: STRICT_AC_GATE does not override verifier results
- **GIVEN** a current cached verdict contains a failed AC
- **AND** `STRICT_AC_GATE=no`
- **WHEN** archive_gate_check runs
- **THEN** it blocks because verifier result validity is independent of `STRICT_AC_GATE`

#### Scenario: Verifier bypass does not skip feature gate
- **GIVEN** `verification.state=bypassed`
- **AND** `FEATURE_ARCHIVE_GATE=hard`
- **AND** the change belongs to an incomplete feature
- **WHEN** rdd-builder reaches archive finalization
- **THEN** feature gate still blocks archive

#### Scenario: Verifier bypass does not skip tasks gate
- **GIVEN** `verification.state=bypassed`
- **AND** `FORCE_ARCHIVE_INCOMPLETE=yes` is not set
- **AND** the change has uncompleted tasks
- **WHEN** rdd-builder reaches archive finalization
- **THEN** archive_gate_check still blocks because tasks are incomplete

#### Scenario: Direct archive fallback without proposal
- **GIVEN** no `proposal.md` exists for the change
- **WHEN** archive_gate_check runs
- **THEN** it skips AC verification entirely
- **AND** it does not write a passed verdict
- **AND** it does not block on missing verifier

#### Scenario: Direct archive fallback ac-verifier error
<!-- v4-residue:allow=history -->

> **RETIRED (2026-11-21, annotate-spec-residue-guard-batch4)** —— 直接调用已删除 verifier 的 fallback 路径已于 **v2.0 移除**（ADR-0045：`_lib/archive.sh:787` 注明 v2.0 起 subprocess fallback 已移除，`:921` 注明无新鲜 cache 时不再有 fallback，对应脚本也不存在）⇒ 本 Scenario 描述的 fallback 调用与 exit code 3 语义均无对象。保留原文作为历史记录。
- **GIVEN** `proposal.md` exists
- **AND** ac-verifier invocation errors (exit code 3)
<!-- v4-residue:allow=history -->
- **WHEN** archive_gate_check runs
- **THEN** it treats the error as a warning by default
- **AND** writes `verification.state=unknown` with `bypass_source=archive_gate_fallback_error`
- **AND** archive proceeds only when `STRICT_AC_GATE=no`

### Requirement: Direct archive fallback SHALL write structured verdict to the canonical cache

> **RETIRED (2026-11-21, annotate-spec-residue-guard-batch4)** —— 同上：直接 fallback 路径已移除（ADR-0045），今天 verdict 只由 `rdd-verifier` 写入 SHA 绑定缓存（`_lib/archive.sh:786-791`）；承接的活契约见 `inline-ac-verifier-into-rdd-verifier` 的 Requirement「archive_gate_check SHALL NOT shell out to …」。保留原文与 Scenario 作为历史记录。

When `archive_gate_check` invokes ac-verifier directly and ac-verifier produces a structured verdict (exit code 0 or 1), the gate SHALL parse the verdict and write it to the canonical cache with `ran_by=archive_gate_check`. The cache entry SHALL include `verification_state`, `failed_acs`, and the implementation commit. Failure to write the cache SHALL NOT promote a failed verdict to passed.
<!-- v4-residue:allow=history -->

#### Scenario: Direct fallback succeeds and writes cache
- **GIVEN** a `proposal.md` exists
- **AND** the cache is missing or stale
- **WHEN** archive_gate_check invokes ac-verifier
<!-- v4-residue:allow=history -->
- **AND** ac-verifier produces a structured verdict
<!-- v4-residue:allow=history -->
- **THEN** the gate writes the verdict to the canonical cache with `ran_by=archive_gate_check`
- **AND** sets `verification_state` accordingly

#### Scenario: Direct fallback cache write fails
- **GIVEN** the verdict is a passing verdict
- **AND** the cache write fails (permission, disk, etc.)
- **WHEN** archive_gate_check evaluates the result
- **THEN** it does not promote the verdict to passed
- **AND** it blocks archive

#### Scenario: Direct fallback ac-verifier returns no structured verdict
<!-- v4-residue:allow=history -->
- **GIVEN** ac-verifier returns exit code 0 or 1 without producing a parseable verdict JSON
<!-- v4-residue:allow=history -->
- **WHEN** archive_gate_check runs
- **THEN** it logs a warning
- **AND** it does not write a cache
- **AND** it does not promote to passed

### Requirement: Archive bypass SHALL be explicit and auditable

Skipping or bypassing verification SHALL not be indistinguishable from a normal pass. A bypass SHALL record the bypass reason, change, implementation commit, timestamp, and initiating option or environment variable. Historical archived changes without verification metadata SHALL be shown as legacy/unknown rather than silently marked passed.

#### Scenario: Explicit bypass archives with audit state
- **GIVEN** a user enables the documented verifier bypass
- **WHEN** rdd-builder completes archive
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
- **THEN** `.rddf/state/verifier/<change>.json` and `.rddf/state/verifier/.ac-verdict-<change>.json` remain intact
- **AND** only plan-handoff state is mutated

#### Scenario: Post-archive cleanup does not affect verification
- **GIVEN** a change has verification metadata
- **WHEN** post-archive cleanup runs
- **THEN** verifier namespace and audit records remain intact
- **AND** only archive residue (deleted-tracked paths, modified critical paths) is processed
