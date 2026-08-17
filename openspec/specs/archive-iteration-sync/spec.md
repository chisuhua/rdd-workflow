# archive-iteration-sync Specification

## Purpose
TBD - created by archiving change harden-archive-iteration-sync. Update Purpose after archive.
## Requirements
### Requirement: archive.sh MUST auto-recover iteration.json via on-disk reconciliation

When `archive_change_for_mode` (in `skills/guide-ship/scripts/ship_archive.sh`) invokes `mark_iteration_archived` and the underlying `sync_iteration_after_archive` call returns a warning string (indicating iteration.json sync partially or fully failed), the function MUST attempt on-disk reconciliation: scan `openspec/changes/archive/<date>-<change_name>/` for the change's archive directory, and if it exists, force-set `iteration.json` entry's `status` to `archived`, `archived_at` to current timestamp (UTC), and `archive_commit_sha` to current HEAD SHA.

**Rationale**: 2026-08-16 P2 debt improvements (`backfill-proposal-approved-col4` + `enforce-plan-tdd-5step-new`) both completed on-disk archive operations successfully but failed iteration.json sync due to a `KeyError: 'skills._lib'` namespace package import bug (since fixed by commit 78724ca). Without reconciliation, `rddf status` shows stale `📋 planned` status for already-archived changes — forcing manual backfill. This requirement prevents that divergence.

#### Scenario: mark_iteration_archived fails, archive dir exists, reconciliation succeeds
**WHEN** `archive_change_for_mode` calls `mark_iteration_archived "$change_name" "$project_root" "$archive_commit_sha"` and the internal `sync_iteration_after_archive` raises an exception

**AND** `openspec/changes/archive/<date>-<change_name>/` exists on disk (proving archive main flow succeeded)

**THEN** `reconcile_iteration_from_disk "$change_name" "$project_root"` MUST invoke

**AND** iteration.json entry's `status` MUST become `archived`

**AND** iteration.json entry's `archived_at` MUST be set to current UTC timestamp

**AND** stderr MUST contain: `⚠️ iteration.json sync failed — auto-recovered via on-disk scan`

**AND** `archive_change_for_mode` exit code MUST be 0 (archive main flow succeeded, reconciliation succeeded)

#### Scenario: mark_iteration_archived succeeds, reconciliation not triggered
**WHEN** `archive_change_for_mode` calls `mark_iteration_archived` and it returns None (no warning)

**THEN** `reconcile_iteration_from_disk` MUST NOT be invoked (no on-disk scan needed)

**AND** iteration.json entry's `status` is already `archived` from mark_iteration_archived path

#### Scenario: FORCE_ITERATION_BACKFILL=no skips reconciliation
**WHEN** `FORCE_ITERATION_BACKFILL=no` is set in environment

**AND** `mark_iteration_archived` fails for a change

**THEN** `reconcile_iteration_from_disk` MUST NOT be invoked

**AND** stderr MUST contain: `⚠️ iteration.json sync failed — set FORCE_ITERATION_BACKFILL=yes to enable auto-recovery`

---

### Requirement: archive.sh MUST expose `reconcile` subcommand for manual on-disk backfill

The `skills/_lib/archive.sh` script MUST expose a `reconcile [project_root]` subcommand (alongside existing `archive_change`, `commit_archive_moves`, etc.) that scans `openspec/changes/archive/` and force-syncs any iteration.json entries that are missing `archived_at` despite having an archive directory on disk.

**Rationale**: Users who run rdd-workflow before this fix was deployed may already have stale iteration.json state. The `reconcile` subcommand gives them a one-shot remediation tool.

#### Scenario: Manual reconcile fixes stale iteration entries
**WHEN** user runs `bash skills/_lib/archive.sh reconcile .` (or with explicit `project_root` argument)

**AND** `openspec/changes/archive/2026-08-16-enforce-plan-tdd-5step-new/` exists

**AND** iteration.json shows `enforce-plan-tdd-5step-new` with `status: planned` (stale, missing `archived_at`)

**THEN** reconcile MUST update iteration.json entry to `status: archived` + `archived_at: <reconcile_time>`

**AND** stdout MUST show: `✅ enforce-plan-tdd-5step-new: fixed (was planned, now archived)`

**AND** exit code MUST be 0

#### Scenario: Idempotent reconcile (no-op when already synced)
**WHEN** user runs `bash skills/_lib/archive.sh reconcile .` twice in succession

**AND** all iteration.json entries already have `status: archived` and matching `archived_at`

**THEN** second invocation MUST NOT modify iteration.json (idempotency)

**AND** stdout MUST show `⏭️ <name>: already synced` for each entry

**AND** exit code MUST be 0

---

### Requirement: archive_iteration_sync_resilience MUST have bats integration coverage

A new file `tests/integration/test_archive_iteration_sync_resilience.bats` MUST exist and cover 3 cases:
1. Normal archive flow: `mark_iteration_archived` succeeds → reconciliation not triggered → iteration.json correctly archived
2. Failed sync: `mark_iteration_archived` mocked to raise `KeyError` → reconciliation triggered → iteration.json correctly archived via on-disk fallback
3. Manual reconcile: simulate historical stale entries → `bash skills/_lib/archive.sh reconcile .` fixes them all

**Rationale**: ADR-0007 mandates quality gates for archive mutation paths. Without test coverage, future refactors may regress the reconciliation logic.

#### Scenario: bats test suite passes
**WHEN** user runs `bats tests/integration/test_archive_iteration_sync_resilience.bats`

**THEN** all 3 cases MUST pass with exit code 0

**AND** no skipped or todo cases

#### Scenario: regression run after refactor
**WHEN** user refactors `ship_archive.sh::archive_change_for_mode` or `archive.sh::mark_iteration_archived`

**THEN** running `bats tests/integration/test_archive_iteration_sync_resilience.bats` MUST still pass

---

### Requirement: docs/operations/archive-state-recovery.md MUST document manual recovery workflow

A new (or extended) documentation file at `docs/operations/archive-state-recovery.md` MUST contain:
1. **Symptoms section**: How to detect stale iteration.json state (e.g., `rddf status` shows `📋 planned` but `openspec/changes/archive/<date>-<name>/` exists)
2. **Manual recovery section**: 3-step procedure (run `reconcile` → verify with `rddf status` → commit if iteration.json was modified)
3. **Opt-out section**: Explanation of `FORCE_ITERATION_BACKFILL=no` env var
4. **Quick verification**: One-liner bash command to verify state consistency (`rddf status | grep planned && echo "STALE FOUND"`)

#### Scenario: User follows recovery guide successfully
**WHEN** user reads `docs/operations/archive-state-recovery.md`

**AND** runs the documented 3-step procedure

**THEN** `rddf status` MUST show `📦 archived` for the previously-stale change

**AND** iteration.json MUST contain `status: archived` + `archived_at` for that change

