# memory Specification

## Purpose
TBD - created by archiving change v2-advanced-features. Update Purpose after archive.
## Requirements
### Requirement: memory-execution-history
The system SHALL record each loop execution to a memory file for later analysis.

Memory stored at `.rdd-workflow/memory.jsonl` as JSONL. Each record contains: `change_name`, `goal`, `config`, `iterations`, `result`, `failure_reason` (if any), `timestamp`.

#### Scenario: Execution recorded
- **WHEN** a loop execution completes
- **THEN** execution record is appended to memory file
- **AND** record contains all required fields

#### Scenario: Memory cap enforced
- **WHEN** memory file exceeds 10,000 records
- **THEN** oldest records are archived
- **AND** warning is logged

### Requirement: memory-interruption-recovery
The system SHALL support recovering from interrupted loop executions.

#### Scenario: Interrupted execution detected
- **WHEN** loop engine starts and finds incomplete execution in memory
- **THEN** user is shown the last execution context (time, result, failure reason)
- **AND** user is offered options: resume, restart, abandon

### Requirement: memory-config-recommendation
The system SHALL recommend configuration based on similar past executions.

Uses heuristic similarity: goal string match + config similarity.

#### Scenario: Similar past success found
- **WHEN** new goal has 80%+ string similarity to a past successful execution
- **THEN** system recommends that execution's config
- **AND** shows source execution for user review

### Requirement: memory-repeated-failure-warning
The system SHALL warn when the same change has failed multiple times.

#### Scenario: Same change failed 3 times
- **WHEN** user attempts to run loop for a change that has ≥ 3 failures in memory
- **THEN** system displays warning with failure analysis
- **AND** asks user to confirm before proceeding

