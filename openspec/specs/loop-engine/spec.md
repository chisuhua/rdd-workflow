# loop-engine Specification

## Purpose
TBD - created by archiving change v2-loop-engine. Update Purpose after archive.
## Requirements
### Requirement: loop-engine-main-cycle
The system SHALL provide a `LoopEngine` class implementing a 5-building-block cycle: `verify_goal`, `scan_state`, `generate_plan`, `execute_plan`, `verify_results`, `adapt`.

The cycle continues until `verify_goal` returns true or a safety mechanism triggers.

#### Scenario: Full cycle runs
- **WHEN** `LoopEngine.run()` is called with a goal
- **THEN** all 5 blocks execute in sequence per iteration
- **AND** cycle repeats until goal achieved or safety limit reached

#### Scenario: Goal achieved
- **WHEN** `verify_goal` returns true
- **THEN** loop exits with `success` status
- **AND** completion event is recorded

### Requirement: loop-engine-safety-mechanisms
The system SHALL enforce four safety mechanisms to prevent runaway loops.

Safety mechanisms:
- Max iterations (default 100, configurable)
- Max retries per action (default 3, configurable)
- Oscillation detection: 5 iterations with ≤ 2 distinct states triggers stop
- Per-action timeout: 30 minutes
- Circuit breaker: 3 consecutive failures triggers stop

#### Scenario: Max iterations reached
- **WHEN** loop has run for `max_iterations` iterations without goal achievement
- **THEN** loop exits with `max_iterations_exceeded` status
- **AND** warning event is recorded

#### Scenario: Oscillation detected
- **WHEN** last 5 iterations had ≤ 2 distinct states
- **THEN** loop exits with `oscillation_detected` status
- **AND** last 5 states are logged for debugging

### Requirement: loop-engine-goal-types
The system SHALL support multiple goal types read from configuration `success_criteria`.

Supported goal types include: "complete all changes", "create worktrees for X", "achieve state Y", custom predicates.

#### Scenario: Custom goal predicate
- **WHEN** config specifies `success_criteria: "active_changes == 0 and worktrees == 0"`
- **THEN** loop exits when both conditions are true

