# fix-flow-drift-batch-1 Specification

## Purpose
Keep the three surfaces that consume a change's acceptance criteria in step with each
other — the header spellings the verifier recognises, the `--dry-run` contract of the
legacy-state migration, and the fix hints `rddf doctor --category layout` prints for a
missing path.
## Requirements
### Requirement: ac-header-variants-are-parsed-uniformly

The acceptance-criteria parser SHALL recognise the three header spellings `验收标准`,
`Acceptance Criteria` and `Acceptance`, and the verifier skill's documentation SHALL list
all three so that a reader of the documentation is not misled about which sections are
recognised.

#### Scenario: every header variant yields the same criteria count

- **WHEN** a fixture proposal uses `## 验收标准`, `## Acceptance Criteria` or `## Acceptance`
  as its acceptance header
- **THEN** parsing that proposal SHALL yield the same number of criteria for all three
- **AND** the criteria SHALL be numbered consecutively from `AC-1`

#### Scenario: the verifier skill lists every header variant

- **WHEN** the `rdd-verifier` skill documentation is read
- **THEN** it SHALL mention `验收标准`, `Acceptance Criteria` and `Acceptance`

### Requirement: layout-fix-hint-distinguishes-file-from-directory

The `layout` doctor's fix hint for a missing path SHALL reflect the kind of the entry:
a missing **file** entry SHALL be reported without a trailing slash and a missing
**directory** entry SHALL be reported with one.

#### Scenario: a missing file entry is reported without a trailing slash

- **WHEN** the layout manifest lists a file that does not exist on disk
- **THEN** the fix hint SHALL name that file without a trailing slash

#### Scenario: a missing directory entry is reported with a trailing slash

- **WHEN** the layout manifest lists a directory that does not exist on disk
- **THEN** the fix hint SHALL name that directory with a trailing slash

### Requirement: rdd-verify-dry-run-writes-nothing

`rddf rdd-verify --dry-run` SHALL NOT move, create or delete any legacy state file.

#### Scenario: a dry run leaves the legacy state files untouched

- **WHEN** `rddf rdd-verify --dry-run` runs against a fixture that contains legacy state files
- **THEN** the set of files under the fixture's state directory SHALL be unchanged

### Requirement: rdd-verify-dry-run-reports-what-it-would-migrate

`rddf rdd-verify --dry-run` SHALL report the migration it would perform, so that a dry
run does not lose the information it was asked to surface.

#### Scenario: a dry run states how many files it would migrate

- **WHEN** `rddf rdd-verify --dry-run` runs against a fixture that contains legacy state files
- **THEN** the output SHALL state that it would migrate and name the files

### Requirement: rdd-verify-dry-run-and-stage-are-mutually-exclusive

`--dry-run` and `--stage` SHALL NOT be combined: the combination reports a usage error
and exits 2.

#### Scenario: combining --dry-run with --stage is a usage error

- **WHEN** `rddf rdd-verify --dry-run --stage <change>` is invoked
- **THEN** the command SHALL exit 2 with a usage error
- **AND** the message SHALL state that the two options are mutually exclusive

### Requirement: rdd-verify-stage-still-migrates-and-stages

`rddf rdd-verify --stage <change>` SHALL still migrate the legacy state files and stage
the result — the `--dry-run` fix SHALL NOT have changed the staging path.

#### Scenario: staging migrates the legacy state and stages the result

- **WHEN** `rddf rdd-verify --stage <change>` is invoked without `--dry-run`
- **THEN** the legacy state files SHALL be migrated
- **AND** the result SHALL be staged
