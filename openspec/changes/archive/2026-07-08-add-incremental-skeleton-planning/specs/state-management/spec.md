## MODIFIED Requirements

### Requirement: state-management-state-vector
The system SHALL provide a unified state vector as the single source of truth for workflow state.

The state vector SHALL be stored as a JSON file at `.rdd-workflow/state-vector.json` and SHALL contain fields: `goal`, `arch_side`, `plan_side`, `ship_side`, `loop_state`, `memory`, `metadata`.

The `plan_side` field SHALL include a `planned_changes` array tracking skeleton changes.

#### Scenario: State vector write
- **WHEN** any component updates workflow state
- **THEN** the state vector file is atomically rewritten
- **AND** the change is recorded in the event log

#### Scenario: State vector corruption detected
- **WHEN** state vector file fails checksum validation on load
- **THEN** system falls back to last known good state
- **AND** records corruption event in event log

## MODIFIED Requirements

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