# state-management Specification

## Purpose
TBD - created by archiving change v2-core-foundation. Update Purpose after archive.
## Requirements
### Requirement: state-management-state-vector
The system SHALL provide a unified state vector as the single source of truth for workflow state.

The state vector SHALL be stored as a JSON file at `.spec-workflow/state-vector.json` and SHALL contain fields: `goal`, `arch_side`, `plan_side`, `ship_side`, `loop_state`, `memory`, `metadata`.

The `plan_side` field SHALL include a `planned_changes` array tracking skeleton changes.

#### Scenario: State vector write
- **WHEN** any component updates workflow state
- **THEN** the state vector file is atomically rewritten
- **AND** the change is recorded in the event log

#### Scenario: State vector corruption detected
- **WHEN** state vector file fails checksum validation on load
- **THEN** system falls back to last known good state
- **AND** records corruption event in event log

### Requirement: state-management-event-log
The system SHALL maintain an append-only event log recording all workflow state changes.

The event log SHALL be stored as JSONL at `.spec-workflow/event-log.jsonl`. Each event SHALL have a unique ID in format `evt_YYYYMMDD_HHMMSS_NNN`.

#### Scenario: Event recorded
- **WHEN** a workflow state transition occurs
- **THEN** an event is appended to the log within 10ms

#### Scenario: Event query by time range
- **WHEN** user queries events between two timestamps
- **THEN** system returns matching events in chronological order

### Requirement: state-management-file-lock
The system SHALL provide file-level locking for concurrent state access.

The lock SHALL use `fcntl` and SHALL have a default timeout of 10 seconds. The lock SHALL be released automatically when the context manager exits.

#### Scenario: Concurrent write blocked
- **WHEN** process A holds the lock and process B attempts to acquire
- **THEN** process B waits up to 10 seconds
- **AND** either acquires after A releases or fails with timeout error

### Requirement: state-management-v1x-sync
The system SHALL provide bidirectional synchronization between the v2 state vector and v1.x legacy state files.

State vector SHALL be the authoritative source. On conflict, state vector wins. Conflicts SHALL be logged to the event log.

#### Scenario: State vector update propagates to v1.x
- **WHEN** state vector is updated
- **THEN** corresponding v1.x files (`.rddf/state/roadmap-state.json`, `proposal-suggestions.md`, `openspec/changes/<name>/.openspec.yaml`) are updated within 50ms

#### Scenario: v1.x file change propagates to state vector
- **WHEN** a v1.x file is modified
- **THEN** state vector is updated to reflect the change
- **AND** sync direction is recorded in event log

### Requirement: iteration-json-planned-status
The system SHALL support a `planned` status value in the iteration.json change status enum.

The `planned` status SHALL be valid alongside existing statuses: `proposed`, `in_worktree`, `review`, `completed`, `archived`.

The status SHALL be set by propose (--skeleton mode) and SHALL be transitioned to `proposed` by guide-plan fill phase.

#### Scenario: Iteration schema validates planned
- **WHEN** iteration.json contains a change with `status: "planned"`
- **THEN** schema validation SHALL pass
- **AND** the change SHALL be counted in status Mode E output under "planned" group

#### Scenario: Status transition planned to proposed
- **WHEN** guide-plan fill successfully creates design.md and tasks.md for a `planned` change
- **THEN** iteration.json status SHALL update from `planned` to `proposed`
- **AND** the transition SHALL be recorded in the event log

### Requirement: proposal-suggestions-skeleton-status
The system SHALL support a `skeleton` value in the proposal-suggestions.md entry status field.

The `skeleton` status SHALL indicate the change directory exists with minimal artifacts. It SHALL be distinct from `待创建` (not yet created), `进行中` (in progress), and `已完成` (completed).

#### Scenario: Skeleton entry preserved in suggestions
- **WHEN** a proposal-suggestions entry has `status: "skeleton"`
- **THEN** the entry SHALL NOT be removed by propose Phase 0 cleanup (which only removes `已完成` entries)
- **AND** the entry's `description` field SHALL be preserved for use during fill

