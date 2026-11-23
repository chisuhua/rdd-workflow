# session-agents Specification

## Purpose
TBD - created by archiving change v2-advanced-features. Update Purpose after archive.
## Requirements
### Requirement: session-coordinator
The system SHALL provide a `SessionCoordinator` for managing related workflow sessions.

v2.0 implements lightweight coordination (sequential). v2.1 will add true parallel execution.

#### Scenario: Session created
- **WHEN** `create_session()` is called with session_id and goal
- **THEN** session is recorded in state vector
- **AND** session_id is unique

#### Scenario: Parent-child relationship
- **WHEN** sub-session is created within a parent session
- **THEN** parent-child relationship is recorded in state vector
- **AND** parent can list its children

### Requirement: session-state-machine
Sessions SHALL transition through states: `active → paused → active`, `active → completed`, `active → failed`.

#### Scenario: Session paused and resumed
- **WHEN** session is paused
- **THEN** session state changes to `paused`
- **AND** can be resumed to `active` with context preserved

#### Scenario: Session completed
- **WHEN** session's goal is achieved
- **THEN** session state changes to `completed`
- **AND** completion event is recorded

### Requirement: agent-roles
The system SHALL define three agent roles: Planner, Executor, Verifier.

- **Planner**: Analyzes current state, generates execution plan
- **Executor**: Runs actions, reports results
- **Verifier**: Validates results, computes quality score

#### Scenario: Full agent flow
- **WHEN** workflow requires multi-agent coordination
- **THEN** Planner generates plan
- **AND** Executor runs actions
- **AND** Verifier validates and scores

### Requirement: agent-state-vector-communication
Agents SHALL communicate via the state vector (from v2-core-foundation).

#### Scenario: Planner writes plan
- **WHEN** Planner completes plan generation
- **THEN** plan is written to state vector
- **AND** Executor can read it in next iteration

### Requirement: Quota-aware execution strategy

The orchestrator MUST probe subagent quota before parallel dispatch and degrade to direct execution when quota is exhausted.

#### Scenario: Quota exhausted mid-wave

When `task()` returns `quota_exceeded`, the orchestrator MUST retry once then fall back to direct execution within the current session.
Given a change with hooks triggering on comments matching `subagent-orchestrator-execution-strategy` patterns
When the change is committed via `git commit`
Then no false-positive hook warning is emitted.

#### Scenario: Magic-number annotation

When a comment annotates a numeric threshold with explanation (e.g. "100ms threshold tuned for hardware X")
And the comment is in the same file as the threshold
Then the hook MUST NOT emit a lint warning on the threshold.

