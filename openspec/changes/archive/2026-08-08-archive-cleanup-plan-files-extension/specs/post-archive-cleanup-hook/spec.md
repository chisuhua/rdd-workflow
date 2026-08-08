# post-archive-cleanup-hook Specification

## Purpose

Idempotent post-archive cleanup hook (`_lib/post_archive_cleanup.sh`) that scans `git status --porcelain` after `openspec archive <name>` finishes, classifies residue into whitelist buckets, applies `git rm -f` to deleted-tracked paths and `git add` to modified-critical paths, then commits only the rm bucket with subject `chore(post-archive): clean residue from <name>`. The hook respects `SKIP_POST_ARCHIVE_CLEANUP=yes` (escape hatch) and `DRY_RUN_POST_ARCHIVE_CLEANUP=yes` (echo-only). Auto-invoked from `guide-ship` Phase 3 (`archive_change_for_mode`).

This delta extends the hook to also clean residue from `openspec/changes/<name>/` (the 6 artifact types: `.openspec.yaml`, `design.md`, `proposal.md`, `roadmap-meta.yaml`, `specs/...`, `tasks.md`) when the change has been archived to `openspec/changes/archive/<date>-<name>/`. The defensive archive-presence check prevents accidental deletion of active changes.

## MODIFIED Requirements

### Requirement: `_WHITELIST_DELETED_PATTERNS` MUST include `openspec/changes/`

The `_lib/post_archive_cleanup.sh::_WHITELIST_DELETED_PATTERNS` array MUST include `openspec/changes/` as a delete-tracked prefix in addition to the existing `.rddf/plans/` and `.rddf/state/*.tmp` patterns.

modifies: post-archive-cleanup-hook

The pattern MUST be matched
as a **prefix** (substring from index 0) so all nested files under
`openspec/changes/<name>/` are picked up.

When the hook detects a `D openspec/changes/<name>/...` residue line, it MUST
verify that `openspec/changes/archive/<date>-<name>/` exists for some `<date>`
matching `YYYY-MM-DD` before including the path in the rm bucket. This
defensive check prevents deletion of active (non-archived) changes.

The `_matches_prefix` glob helper MUST match `openspec/changes/` as a literal
prefix, not a glob (no `*` suffix). The exact pattern value is
`openspec/changes/` (with trailing slash).

#### Scenario: Archived change leaves 6-residue — hook cleans them

- **GIVEN** change `add-rdd-doctor-skill` was archived to `openspec/changes/archive/2026-08-08-add-rdd-doctor-skill/`
- **AND** `git status --porcelain` shows:
  ```
   D openspec/changes/add-rdd-doctor-skill/.openspec.yaml
   D openspec/changes/add-rdd-doctor-skill/design.md
   D openspec/changes/add-rdd-doctor-skill/proposal.md
   D openspec/changes/add-rdd-doctor-skill/roadmap-meta.yaml
   D openspec/changes/add-rdd-doctor-skill/specs/diagnose-changes/spec.md
   D openspec/changes/add-rdd-doctor-skill/tasks.md
  ```
- **AND** `SKIP_POST_ARCHIVE_CLEANUP` is unset
- **WHEN** `post_archive_cleanup "$project_root" "add-rdd-doctor-skill"` runs
- **THEN** all 6 paths are added to the deleted_to_rm bucket
- **AND** `git rm -f` is invoked on all 6 paths
- **AND** 1 commit is created with subject `chore(post-archive): clean residue from add-rdd-doctor-skill`
- **AND** working tree becomes clean

#### Scenario: Active change — hook skips defenses

- **GIVEN** change `draft-change` is still active (directory exists at `openspec/changes/draft-change/`)
- **AND** `openspec/changes/archive/*-draft-change/` does NOT exist
- **AND** `git status --porcelain` shows ` D openspec/changes/draft-change/proposal.md`
- **WHEN** `post_archive_cleanup "$project_root" "draft-change"` runs
- **THEN** the `openspec/changes/draft-change/proposal.md` path is NOT added to deleted_to_rm
- **AND** hook does NOT `git rm` it
- **AND** hook does NOT commit (rm bucket is empty)
- **AND** the path remains in the working tree for human review

#### Scenario: archive/ directory excluded from cleanup

- **GIVEN** `openspec/changes/archive/2026-07-01-old-archive/` contains residue
- **AND** `git status --porcelain` shows ` D openspec/changes/archive/2026-07-01-old-archive/proposal.md`
- **WHEN** `post_archive_cleanup` runs
- **THEN** the path is NOT added to deleted_to_rm (archive/ preserves history)
- **AND** no commit is produced

### Requirement: `git rm` MUST use `-f` for tracked-only residue

The hook MUST invoke `git rm -f <paths>` (not `git rm -r` and not `rm -rf`) to remove the 6-residue from `openspec/changes/<name>/`.

modifies: post-archive-cleanup-hook

The `-f` flag is required because the files are tracked in the index but the working tree files are already deleted (the `D` status indicates worktree deletion only, not stage deletion).
to remove the 6-residue from `openspec/changes/<name>/`. The `-f` flag is
required because the files are tracked in the index but the working tree
files are already deleted (the `D` status indicates worktree deletion only,
not stage deletion).

This is consistent with the existing `_WHITELIST_DELETED_PATTERNS` cleanup
of `.rddf/plans/`, which uses `git rm -f`. The `-r` recursive flag MUST
NOT be used (avoids accidental removal of sibling files).

#### Scenario: git rm -f removes from index and worktree

- **GIVEN** working tree has `D openspec/changes/foo/.openspec.yaml`
- **WHEN** hook runs `git rm -f openspec/changes/foo/.openspec.yaml`
- **THEN** the file is removed from the git index
- **AND** the working tree file is confirmed gone (no-op since already deleted)
- **AND** subsequent `git commit` records the deletion

### Requirement: Hook MUST be idempotent on re-run

A second invocation of `post_archive_cleanup` with the same args MUST NOT produce additional commits.

modifies: post-archive-cleanup-hook

The hook's bucket-classification is deterministic — second run sees an empty `git status --porcelain` and exits with no buckets, no commit, no error.
NOT produce additional commits. The hook's bucket-classification is
deterministic — second run sees an empty `git status --porcelain` and
exits with no buckets, no commit, no error.

#### Scenario: Second invocation is a no-op

- **GIVEN** first invocation ran `git rm -f` and committed the rm bucket
- **AND** working tree is now clean
- **WHEN** `post_archive_cleanup` is invoked again
- **THEN** zero paths are added to either bucket
- **AND** no commit is created
- **AND** function returns 0

### Requirement: Hook MUST respect `SKIP_POST_ARCHIVE_CLEANUP=yes`

The hook MUST short-circuit (return 0) when `SKIP_POST_ARCHIVE_CLEANUP=yes` is exported, without reading `git status` or running any `git rm` / `git add` / `git commit` commands.

modifies: post-archive-cleanup-hook

This is the existing escape hatch behavior; the new `openspec/changes/` extension MUST NOT bypass it.
is exported, without reading `git status` or running any `git rm` / `git add` /
`git commit` commands. This is the existing escape hatch behavior; the new
`openspec/changes/` extension MUST NOT bypass it.

#### Scenario: Skip env var still works

- **GIVEN** `SKIP_POST_ARCHIVE_CLEANUP=yes` is exported
- **AND** working tree has `D openspec/changes/foo/proposal.md` residue
- **WHEN** `post_archive_cleanup` runs
- **THEN** output begins with `⏭️  post_archive_cleanup: SKIPPED`
- **AND** no `git rm` is invoked
- **AND** no commit is created
- **AND** function returns 0

### Requirement: Hook MUST commit only the rm bucket (not modified)

The system SHALL preserve the existing behavior of `git add` modified-critical paths without committing them (let user review).

modifies: post-archive-cleanup-hook

The new `openspec/changes/` extension adds to the rm bucket only (the 6-residue is `D` status, not `M` status), so the existing `git add` bucket logic is unaffected.
paths without committing them (let user review). The new `openspec/changes/`
extension adds to the rm bucket only (the 6-residue is `D` status, not
`M` status), so the existing `git add` bucket logic is unaffected.

#### Scenario: Modified paths still staged, not committed

- **GIVEN** working tree has `M proposal-approved.md` and `D openspec/changes/foo/proposal.md`
- **WHEN** `post_archive_cleanup` runs
- **THEN** `M proposal-approved.md` is added to modified_to_add and `git add` is called
- **AND** `D openspec/changes/foo/proposal.md` is added to deleted_to_rm and `git rm -f` is called
- **AND** the commit includes only the rm bucket (1 commit, subject `chore(post-archive): clean residue from foo`)
- **AND** `proposal-approved.md` remains staged but uncommitted for human review

### Requirement: Manual entry MUST support `--include-change-artifacts` flag

The script `scripts/cleanup-plan-files.sh` MUST accept a `--include-change-artifacts` flag. When the flag is present, the manual entry SHALL list each `openspec/changes/<name>/` directory that has a matching `openspec/changes/archive/<date>-<name>/` archive, show the 6-residue file count per directory, request user confirmation before `git rm -r`, and MUST NOT auto-commit. Without the flag, the script MUST retain its existing behavior (only cleans `.rddf/plans/<name>.md`).

modifies: post-archive-cleanup-hook

Without `--include-change-artifacts`, the manual entry MUST retain its
existing behavior (only cleans `.rddf/plans/<name>.md`).

#### Scenario: Manual entry with --include-change-artifacts

- **GIVEN** `openspec/changes/foo/` exists with 6-residue
- **AND** `openspec/changes/archive/2026-08-08-foo/` exists
- **AND** user runs `bash cleanup-plan-files.sh --include-change-artifacts`
- **WHEN** the script prompts
- **THEN** output shows `openspec/changes/foo/ → 6 residue files`
- **AND** user confirms with `y`
- **AND** `git rm -r openspec/changes/foo/` is invoked
- **AND** no commit is created (manual entry)

#### Scenario: Manual entry without flag — unchanged behavior

- **GIVEN** user runs `bash cleanup-plan-files.sh` (no flag)
- **WHEN** script runs
- **THEN** only `.rddf/plans/<name>.md` is cleaned (existing behavior)
- **AND** `openspec/changes/` is NOT touched

### Requirement: Out-of-scope MUST NOT include proposed change territory

The fix MUST NOT extend to cleaning `openspec/changes/archive/` itself (the archive directory is a permanent record by design).

modifies: post-archive-cleanup-hook

The `_WHITELIST_DELETED_PATTERNS` MUST continue to exclude `openspec/changes/archive/` as a delete-prefix target.
(the archive directory is a permanent record by design). The
`_WHITELIST_DELETED_PATTERNS` MUST continue to exclude `openspec/changes/archive/`
as a delete-prefix target.

#### Scenario: archive/ directory is never cleaned

- **GIVEN** any code path runs `post_archive_cleanup`
- **THEN** only paths matching `openspec/changes/` (NOT `openspec/changes/archive/`)
  are added to the rm bucket
- **AND** the `_matches_prefix` function does NOT match `openspec/changes/archive/` as a prefix of itself
