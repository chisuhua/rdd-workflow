# detectors-actions Specification

## Purpose
TBD - created by archiving change v2-loop-engine. Update Purpose after archive.
## Requirements
### Requirement: detectors-builtin-set
The system SHALL provide 8 built-in detectors returning structured `DetectionResult` (type, data, message).

Built-in detectors: `detect_worktrees`, `detect_pending_changes`, `detect_archived_changes`, `detect_roadmap_state`, `detect_adr_status`, `detect_health_issues`, `detect_test_gaps`, `detect_stale_branches`.

#### Scenario: All detectors run
- **WHEN** loop engine calls `scan_state`
- **THEN** all 8 detectors execute and write results to state vector

#### Scenario: Detector performance
- **WHEN** all 8 detectors run sequentially
- **THEN** total execution time is < 500ms

### Requirement: detectors-plugin-extension
The system SHALL allow custom detectors to be loaded from `.spec-workflow/detectors/`.

#### Scenario: Custom detector loaded
- **WHEN** a Python file exists in `.spec-workflow/detectors/`
- **THEN** its `Detector` subclass is registered and runs alongside built-ins

### Requirement: actions-builtin-set
The system SHALL provide 7 built-in actions returning `ActionResult` (success, data, error).

Built-in actions: `action_create_worktree`, `action_generate_plan`, `action_execute_worktree`, `action_archive_change`, `action_cleanup_stale`, `action_update_roadmap`, `action_create_adr`.

#### Scenario: Action execution
- **WHEN** loop engine calls an action
- **THEN** action executes via subprocess with stdout/stderr captured
- **AND** result is recorded in event log

#### Scenario: Action timeout
- **WHEN** action runs longer than 30 minutes
- **THEN** action is terminated
- **AND** failure is returned to loop engine

### Requirement: actions-plugin-extension
The system SHALL allow custom actions to be loaded from `.spec-workflow/actions/`.

#### Scenario: Custom action loaded
- **WHEN** a Python file exists in `.spec-workflow/actions/`
- **THEN** its `Action` subclass is registered and available for loop engine invocation

