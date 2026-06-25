## ADDED Requirements

### Requirement: design-first-phase-pre-loop
The system SHALL run a design-first phase before the loop starts, allowing the user to confirm or modify three design dimensions.

Design dimensions: Goal Design (deliverables + completion criteria), Verification Design (Executor/Reviewer agents), Control Design (max_iterations, max_retries, oscillation threshold).

#### Scenario: Design phase displays goal
- **WHEN** loop engine is invoked
- **THEN** design phase shows the current goal + completion criteria
- **AND** user can accept or modify

#### Scenario: Design parameters persist
- **WHEN** user modifies design parameters
- **THEN** modifications are saved to state vector
- **AND** loop uses modified parameters

### Requirement: flowchart-real-time-display
The system SHALL provide an ASCII flowchart generator that displays current workflow state.

Flowchart shows: current phase, gate status, iteration count, error/warning summary, progress.

#### Scenario: Flowchart updates on state change
- **WHEN** state vector changes
- **THEN** flowchart regenerates within 100ms
- **AND** new state is visible to user
