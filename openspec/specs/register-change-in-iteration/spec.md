# register-change-in-iteration Specification

## Purpose
Keep `.rddf/state/iteration.json` in sync with the changes that exist on disk: P0 approve
registers a newly approved change, and the archive-side sync then updates that entry
instead of reporting the change as unknown.
## Requirements
### Requirement: phase0-approve-registers-change-in-iteration

`skills/rdd-builder/scripts/phase0_approval.sh` SHALL register an approved change in
`.rddf/state/iteration.json` with status `proposed`. The archive-side sync only updates
existing entries, so without this registration a change stays invisible to the iteration
views until someone edits the JSON by hand.

#### Scenario: approve registers the change with status proposed

- **WHEN** `phase0_approval.sh` approves a change whose improvement draft exists
- **THEN** `.rddf/state/iteration.json` SHALL contain an entry for that change
- **AND** that entry's status SHALL be `proposed`

### Requirement: archive-sync-updates-registered-change

`sync_iteration_after_archive` SHALL transition a change to `archived` in
`iteration.json`. It SHALL update the existing entry when there is one, SHALL recover an
absent entry from the on-disk archive directory, and SHALL return a warning — never
raise — when `iteration.json` itself is missing.

#### Scenario: archive sync updates the existing entry

- **WHEN** `sync_iteration_after_archive` runs for a change that P0 approve registered
- **THEN** the change's entry status SHALL become `archived`
- **AND** the entry SHALL carry an `archived_at` timestamp

#### Scenario: archive sync propagates the archived task counts

- **WHEN** `sync_iteration_after_archive` runs for a change whose archive directory has
  a `tasks.md`
- **THEN** the entry's `tasks_done` and `tasks_total` SHALL reflect that `tasks.md`

#### Scenario: archive sync is idempotent

- **WHEN** `sync_iteration_after_archive` runs twice for the same change
- **THEN** the second run SHALL NOT overwrite the entry's `archived_at`

#### Scenario: an absent entry is recovered from the archive directory

- **WHEN** `sync_iteration_after_archive` runs for a change that has no entry in
  `iteration.json` but does have an archive directory on disk
- **THEN** the entry SHALL be re-created with status `archived`
- **AND** the call SHALL NOT report a missing-entry warning

#### Scenario: a missing iteration.json yields a warning, not an exception

- **WHEN** `sync_iteration_after_archive` runs and `.rddf/state/iteration.json` does not exist
- **THEN** it SHALL return a warning message
- **AND** it SHALL NOT raise

### Requirement: phase0-approve-is-idempotent

Re-approving a change that is already registered SHALL NOT create a second entry and
SHALL NOT reset the fields the archive side owns.

#### Scenario: re-approving keeps a single entry and preserves its fields

- **WHEN** a change already registered in `iteration.json` is approved again
- **THEN** `iteration.json` SHALL still contain exactly one entry for that change
- **AND** its `tasks_done` and `tasks_total` SHALL be unchanged
- **AND** its `archived_at` and `archive_commit_sha` SHALL be unchanged
- **AND** its `added_at` SHALL be present

#### Scenario: re-approving does not downgrade an entry that is already under way

- **WHEN** a change whose entry status is already `in_worktree` is approved again
- **THEN** the entry's status SHALL remain `in_worktree`

### Requirement: iteration-json-problems-do-not-block-approve

A missing, corrupt or schema-invalid `iteration.json` SHALL NOT fail the approval. The
problem SHALL be reported on stderr, the command SHALL still exit 0, and the file on disk
SHALL NOT be replaced by a partial one.

#### Scenario: a missing iteration.json warns and creates no file

- **WHEN** `.rddf/state/iteration.json` does not exist and P0 approve runs
- **THEN** a warning SHALL be printed on stderr
- **AND** the command SHALL exit 0
- **AND** no `iteration.json` SHALL be created

#### Scenario: a corrupt iteration.json is reported and left untouched

- **WHEN** `.rddf/state/iteration.json` exists but cannot be parsed
- **THEN** the problem SHALL be reported on stderr
- **AND** the file SHALL keep its original content

#### Scenario: a schema-invalid iteration.json is reported and left untouched

- **WHEN** `.rddf/state/iteration.json` parses but violates the iteration schema
- **THEN** the problem SHALL be reported on stderr
- **AND** the file SHALL keep its original content

### Requirement: dispatch-quick-does-not-register-change

The dispatch-quick route SHALL NOT write `iteration.json` — it hands the change to the
quick path instead of registering it.

#### Scenario: choice 5 leaves iteration.json unwritten

- **WHEN** P0 approve is invoked with choice 5 (dispatch-quick)
- **THEN** `.rddf/state/iteration.json` SHALL NOT contain an entry for that change

### Requirement: phases-suite-leaves-repo-iteration-untouched

Running the builder phase scripts SHALL NOT modify the repository's own
`.rddf/state/iteration.json`.

#### Scenario: the phases suite leaves the repository iteration.json unchanged

- **WHEN** `tests/integration/test_rdd_builder_phases.bats` runs
- **THEN** the repository's `.rddf/state/iteration.json` SHALL be byte-identical to its
  content before the run
