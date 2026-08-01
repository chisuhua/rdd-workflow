## ADDED Requirements

### Requirement: scan-state.sh loads shared helper from local or global install
`scan-state.sh` SHALL source `skills/_lib/state.sh` using the following precedence:
1. `$PROJECT_ROOT/skills/_lib/state.sh`
2. `${HOME}/.agents/skills/_lib/state.sh`
If either file exists, the scanner SHALL proceed with the same menu output as today.

#### Scenario: Local helper exists
- **WHEN** the project has a local `skills/_lib/state.sh`
- **THEN** `scan_state` sources that file and does not load the global copy

#### Scenario: Global helper fallback
- **WHEN** the project has no local `skills/_lib/state.sh` but `${HOME}/.agents/skills/_lib/state.sh` exists
- **THEN** `scan_state` sources the global copy and produces the same menu output as a local install

#### Scenario: Both local and global exist
- **WHEN** both the local and global copies exist
- **THEN** the local copy is used and the global copy is not sourced

#### Scenario: Both missing
- **WHEN** neither the local nor the global copy exists
- **THEN** `scan_state` prints a warning to stderr containing the literal text `rdd-workflow not installed` and a reference to `INSTALL.md`, and exits 0

### Requirement: guide_entry.sh uses the same fallback as scan-state.sh
`guide_entry.sh` SHALL load the shared helper using the same local-then-global fallback and the same warning contract as `scan-state.sh`.

#### Scenario: guide entry in consumer project
- **WHEN** `guide_entry` runs in a project with no local `skills/_lib/state.sh` but a global install exists
- **THEN** it sources the global copy and emits the same workflow overview as a local install

#### Scenario: guide entry when both copies are missing
- **WHEN** both the local and global copies are missing
- **THEN** `guide_entry` prints the warning to stderr and exits 0

### Requirement: fallback is non-blocking and does not pollute stdout
When the helper is missing and the warning is emitted, stdout SHALL remain in the same format as the successful path, and the exit code SHALL be 0.

#### Scenario: JSON mode with missing helper
- **WHEN** `guide_entry --json` is invoked and both helper copies are missing
- **THEN** stderr contains the warning and stdout contains no error text

#### Scenario: scanner stdout unchanged on fallback success
- **WHEN** `scan_state` is invoked through the global fallback path
- **THEN** stdout is identical to the output produced when the local path is used
