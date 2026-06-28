## ADDED Requirements

### Requirement: full-multi-session-execution
The system SHALL provide a `SessionManager` that creates and coordinates multiple worker sessions executing changes in true parallel (multi-process), replacing the v2.0 lightweight round-robin `SessionCoordinatorV20`.

#### Scenario: parallel change execution
- **WHEN** two or more changes with no dependency between them are submitted
- **THEN** the SessionManager SHALL spawn one worker session per change via `ProcessPoolExecutor`
- **AND** each worker SHALL execute its assigned change concurrently in a separate process

### Requirement: dependency-graph-scheduling
The system SHALL provide a `DependencyScheduler` that builds a dependency graph from change `deps`, performs topological sort (Kahn's algorithm), and assigns changes to sessions only when all dependencies are completed.

#### Scenario: dependency-ordered dispatch
- **WHEN** change `B` declares `deps: [A]` and change `A` is still running
- **THEN** the scheduler SHALL mark `B` as `waiting`
- **AND** SHALL NOT assign `B` to any worker session until `A` reports completion

### Requirement: backward-compatibility-with-v2-mode
The system SHALL preserve v2.0 lightweight session mode as a working option; enabling full multi-session SHALL be an explicit opt-in configuration.

#### Scenario: v2.0 mode still works
- **WHEN** full multi-session mode is not enabled
- **THEN** the SessionCoordinatorV20 coordinator SHALL continue to function
- **AND** existing v2.0 single-process workflows SHALL be unaffected
