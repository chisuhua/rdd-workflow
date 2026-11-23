# fix-phase3-cleanup-wiring Specification

## Purpose
Make the post-archive cleanup behave correctly when it is misused: the helper is a
**library** and must fail loudly instead of silently doing nothing, and it must report a
missing state layer rather than swallow the error.
## Requirements
### Requirement: post-archive-cleanup-library-fails-loudly-when-executed-directly

`post_archive_cleanup.sh` is a library that has to be sourced. Executing it directly SHALL
exit non-zero and say so, rather than silently exiting 0 without doing its job.

#### Scenario: executing the library directly fails loudly

- **WHEN** `post_archive_cleanup.sh` is executed as a script instead of being sourced
- **THEN** it SHALL exit non-zero
- **AND** its message SHALL state that it is a library that has to be sourced

### Requirement: post-archive-cleanup-warns-when-state-sh-is-missing

When the state layer (`state.sh`) cannot be found or fails to source, the cleanup SHALL
report it on stderr instead of swallowing the error.

#### Scenario: a missing state layer is reported on stderr

- **WHEN** the cleanup runs and no `state.sh` can be found
- **THEN** it SHALL print a warning on stderr

### Requirement: post-archive-cleanup-syncs-improvement-approved

A correctly invoked cleanup SHALL move the archived proposal's entry into the
「已实施」section of `improvement-approved.md`.

#### Scenario: the correct call syncs improvement-approved.md

- **WHEN** the cleanup is invoked correctly for an archived change
- **THEN** the proposal's entry in `improvement-approved.md` SHALL be moved into the
  「已实施」section

### Requirement: post-archive-cleanup-is-idempotent

Running the cleanup again on an already-synced state SHALL NOT add duplicate rows.

#### Scenario: repeated calls stay idempotent

- **WHEN** the cleanup is invoked twice for the same change
- **THEN** the proposal's name SHALL appear in `improvement-approved.md` the same number
  of times as after the first invocation

### Requirement: post-archive-cleanup-works-without-a-project-lib

The cleanup SHALL find the shared library by itself when the project has no local `_lib`
directory, so that a global installation still syncs.

#### Scenario: a global-install shape still syncs

- **WHEN** the cleanup runs in a project that has no local `_lib` directory
- **THEN** it SHALL still locate the shared library and sync
