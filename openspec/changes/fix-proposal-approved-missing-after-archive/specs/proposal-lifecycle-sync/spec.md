# proposal-lifecycle-sync Specification

## Purpose

Ensure that `proposal-approved.md` stays in sync with the actual approval and archive lifecycle of OpenSpec changes. After a change is approved, every stage (design → plan → ship → archive) MUST consistently reflect the change's status in `proposal-approved.md`. The current implementation has 3 synchronization gaps that cause archived changes to remain visible as "pending" in the dashboard.

This delta closes the gaps by:
1. Adding `git add proposal-approved.md` to `approve_proposal.sh` so design-phase writes are never lost.
2. Adding a `compgen -G "openspec/changes/archive/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-<name>"` fallback to `mark_approved_completed <name>` so archive-phase can recover from missing entries in the main table.
3. Hardening the dashboard's pending filter so archived changes are never reported as pending, even if `proposal-approved.md` is missing their entry.

## MODIFIED Requirements

### Requirement: `approve_proposal.sh` MUST stage `proposal-approved.md` before returning

The `skills/guide-design/scripts/approve_proposal.sh` script MUST execute `git add proposal-approved.md` after the file is written (whether by `append_approved` or as a fallback) and BEFORE the script exits successfully. The git add call MUST run failure-fast: if the staging fails, the script MUST exit non-zero with a clear error message.

The script SHALL output a confirmation line `git add proposal-approved.md done` so the AI orchestrator can verify the staging succeeded.

modifies: proposal-lifecycle-sync

#### Scenario: Normal approval — proposal-approved.md is staged

- **GIVEN** working tree is clean
- **AND** `approve_proposal.sh <name> <priority> <project_root>` runs
- **WHEN** the script writes a new row to `proposal-approved.md` main table
- **THEN** the script executes `git add proposal-approved.md` before exit
- **AND** `git status --porcelain proposal-approved.md` shows `M  proposal-approved.md` (no question mark)
- **AND** the script outputs `git add proposal-approved.md done`
- **AND** exit code is 0

#### Scenario: git add fails — script exits non-zero

- **GIVEN** working tree has a pre-existing `proposal-approved.md` lock or readonly error
- **WHEN** `approve_proposal.sh` runs and `git add` fails
- **THEN** the script exits with code 1
- **AND** outputs `❌ git add proposal-approved.md failed: <git error message>`
- **AND** the row IS written to `proposal-approved.md` (the underlying state is correct, only the staging fails)

### Requirement: `mark_approved_completed <name>` MUST fallback to archive-prefix detection

The `_lib/state.sh::mark_approved_completed <project_root> <name>` function MUST, when the entry is not found in the main table of `proposal-approved.md`, check if `openspec/changes/archive/<date>-<name>/` exists using the pattern `compgen -G "openspec/changes/archive/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-<name>"`. If the pattern matches, the function MUST append a row to the `## 已实施` section even though the main table entry is missing.

The fallback MUST NOT emit a warning when the archive presence is verified — this is a normal recovery path, not an error.

modifies: proposal-lifecycle-sync

#### Scenario: Main table entry missing — archive fallback recovers

- **GIVEN** `proposal-approved.md` main table does NOT contain `[fix-proposal-approved-missing-after-archive]` row
- **AND** `openspec/changes/archive/2026-08-08-fix-proposal-approved-missing-after-archive/` exists
- **WHEN** `mark_approved_completed <project_root> "fix-proposal-approved-missing-after-archive"` runs
- **THEN** the function appends a row to `## 已实施` section: `| [fix-proposal-approved-missing-after-archive](improvements/fix-proposal-approved-missing-after-archive.md) | P1 | 2026-08-08 |`
- **AND** the function returns 0 (success)
- **AND** no error or warning is emitted

#### Scenario: Main table entry missing + no archive — no-op

- **GIVEN** `proposal-approved.md` main table does NOT contain `[draft-change]` row
- **AND** `openspec/changes/archive/*-draft-change/` does NOT exist
- **AND** `openspec/changes/draft-change/` does NOT exist either
- **WHEN** `mark_approved_completed <project_root> "draft-change"` runs
- **THEN** the function emits a warning `⚠️ mark_approved_completed: draft-change not found in proposal-approved.md and no archive/ detected`
- **AND** the function returns 1 (failure)
- **AND** no row is added

### Requirement: Dashboard pending filter MUST skip archived changes

The `_lib/dashboard/__init__.py` filter for `pending_suggestions` MUST, after the `proposal-approved.md` regex extraction, additionally skip any name for which `openspec/changes/archive/<date>-<name>/` exists. The check MUST use the same `compgen -G` pattern as the post-archive-cleanup hook:

```
compgen -G "openspec/changes/archive/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-<name>"
```

The dashboard collection function MUST also remove the matched name from `data.suggestions` so it does not appear in the rendered table.

modifies: proposal-lifecycle-sync

#### Scenario: Archived change is NOT in pending

- **GIVEN** `improvements/archive-cleanup-plan-files-extension.md` exists
- **AND** `openspec/changes/archive/2026-08-08-archive-cleanup-plan-files-extension/` exists
- **AND** `proposal-approved.md` does NOT contain the entry (lost during plan-phase commit)
- **WHEN** `data = collect(project_root)` runs
- **AND** `data.pending_suggestions` is computed
- **THEN** `archive-cleanup-plan-files-extension` is NOT counted in `pending_suggestions`
- **AND** `archive-cleanup-plan-files-extension` is NOT in `data.suggestions`
- **AND** the Section 7 "Pending" render lists it as "(no pending suggestions)" — no false-positive row

#### Scenario: Active improvement IS in pending

- **GIVEN** `improvements/fix-proposal-approved-missing-after-archive.md` exists
- **AND** `openspec/changes/archive/*-fix-proposal-approved-missing-after-archive/` does NOT exist
- **AND** `proposal-approved.md` already contains this name (in the main table)
- **WHEN** `data = collect(project_root)` runs
- **THEN** `fix-proposal-approved-missing-after-archive` is filtered out by the main-table check
- **AND** `pending_suggestions` does NOT include it (already approved)

#### Scenario: Pending improvement (not yet approved) IS in pending

- **GIVEN** `improvements/some-new-improvement.md` exists
- **AND** `proposal-approved.md` does NOT contain the entry
- **AND** `openspec/changes/archive/*-some-new-improvement/` does NOT exist
- **WHEN** `data = collect(project_root)` runs
- **THEN** `some-new-improvement` IS in `pending_suggestions`
- **AND** `some-new-improvement` IS in `data.suggestions`

### Requirement: `plan-done` gate MUST warn on dirty `proposal-approved.md`

The `guide-plan.md` plan-done exit handler MUST, before writing `.plan-handoff.json`, check `git status --porcelain proposal-approved.md`. If the output is non-empty (tracked file modified, or untracked file present), the gate MUST emit a warning `⚠️ proposal-approved.md has uncommitted changes — commit before plan-done` to stderr. The gate MUST NOT block plan-done (warning level only).

The warning is best-effort: if `git status` fails or `proposal-approved.md` does not exist, the gate MUST skip the warning silently.

modifies: proposal-lifecycle-sync

#### Scenario: plan-done with dirty proposal-approved.md

- **GIVEN** `proposal-approved.md` has uncommitted changes (`M proposal-approved.md` in `git status`)
- **WHEN** `plan-done` gate runs
- **THEN** the warning `⚠️ proposal-approved.md has uncommitted changes — commit before plan-done` is emitted to stderr
- **AND** plan-done continues (does not block)
- **AND** `.plan-handoff.json` is written

#### Scenario: plan-done with clean proposal-approved.md

- **GIVEN** `proposal-approved.md` is committed (no `M` or `??` in `git status`)
- **WHEN** `plan-done` gate runs
- **THEN** no warning is emitted
- **AND** plan-done proceeds normally

### Requirement: Out of scope MUST NOT include backward-compat shims

This fix MUST NOT introduce backward-compat shims for the missing `proposal-approved.md` row in `archive-cleanup-plan-files-extension` (the bug that motivated this improvement). The historical state is preserved in git; future recovery MUST be via the fix itself, not via retroactive patch.

modifies: proposal-lifecycle-sync

#### Scenario: No retroactive patch applied

- **GIVEN** `archive-cleanup-plan-files-extension` row was manually added to `## 已实施` (commit 3dc1b03)
- **WHEN** this improvement is shipped
- **THEN** the manual row is preserved (no rewriting)
- **AND** no script auto-detects and re-adds historical entries

## Opening Note

Worktree commit policy: this change follows the v2.0.5+ aggregate-commit pattern. After all tasks complete, ONE commit at the worktree level with conventional message, then archive.
