# gate-mechanism Specification

## Purpose
TBD - created by archiving change v2-core-foundation. Update Purpose after archive.
## Requirements
### Requirement: gate-mechanism-phase-transition
The system SHALL validate phase transitions using a gate mechanism before allowing them.

Phase transitions SHALL be validated against a checklist of `Check` objects, each with a name, condition (lambda), message, and severity (`error` or `warning`).

#### Scenario: Error-severity check fails
- **WHEN** a phase transition is attempted and an error-severity check fails
- **THEN** transition is rejected
- **AND** failure event is recorded to event log

#### Scenario: Warning-severity check fails
- **WHEN** a phase transition is attempted and only warning-severity checks fail
- **THEN** transition proceeds with warning logged
- **AND** warning event is recorded to event log

#### Scenario: Force transition
- **WHEN** user explicitly forces a transition despite gate failure
- **THEN** transition proceeds
- **AND** force_transition event is recorded
- **AND** user confirmation is required

### Requirement: gate-mechanism-default-checks
The system SHALL provide default gate checks for `arch_done`, `plan_done`, and `ship_done` transitions.

- `arch_done`: adr_exists (error), roadmap_defined (error), gap_analysis_complete (warning)
- `plan_done`: changes_committed (error), artifacts_complete (error), deps_analyzed (warning)
- `ship_done`: worktrees_empty (error), archive_empty (error), tests_pass (error)

#### Scenario: arch_done gate blocks missing ADR
- **WHEN** user attempts arch → plan transition
- **AND** no ADR exists in `docs/adr/`
- **THEN** transition is rejected with message "ADR required before planning"

### Requirement: gate-mechanism-plugin-api
The system SHALL allow extension via plugins loaded from `.spec-workflow/plugins/`.

The plugin API SHALL provide `register_gate_check(check: Check)` to add custom checks.

#### Scenario: Plugin gate check loaded
- **WHEN** a plugin file exists in `.spec-workflow/plugins/`
- **THEN** its registered gate checks are added to the default checklist

### Requirement: gate-mechanism-actionable-suggestions
The system SHALL provide actionable fix suggestions when gate checks fail.

Each gate check SHALL include a suggestion string with concrete commands the user can run.

#### Scenario: Suggestion includes command
- **WHEN** a gate check fails
- **THEN** the error message includes a suggestion with at least one shell command

