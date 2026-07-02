# step-pipeline Specification

## Purpose
TBD - created by archiving change v3-step-pipeline. Update Purpose after archive.
## Requirements
### Requirement: phase-step-templates
The system SHALL provide a `phase_templates.yaml` declaring the default step sequence for each phase (`arch`, `plan`, `ship`), where each step has an `id`, `type` (`detector` | `action`), `module`, and `function`.

#### Scenario: template loaded at startup
- **WHEN** the Loop engine initializes
- **THEN** it SHALL load `phase_templates.yaml` and register the steps for each phase

### Requirement: step-pipeline-execution
The system SHALL execute a phase's steps in declared order via a `StepPipeline` executor, recording `step_started` and `step_completed` event-log entries for each step.

#### Scenario: steps run in order
- **WHEN** the `plan` phase is triggered for change `add-auth`
- **THEN** the steps SHALL execute in the order declared in the template
- **AND** each step SHALL emit a `step_started` event before execution and a `step_completed` event after

### Requirement: interruption-recovery
The system SHALL resume a phase from the last un-completed step by skipping steps already marked completed in the state vector.

#### Scenario: resume after interrupt
- **WHEN** a `plan` pipeline is interrupted after `generate_proposal` completes
- **AND** the pipeline is re-triggered for the same change
- **THEN** the pipeline SHALL skip `scan_candidates`, `select_changes`, and `generate_proposal`
- **AND** SHALL resume execution from `generate_design`

### Requirement: backward-compatibility-fallback
The system SHALL fall back to the v2.0 black-box phase execution when `phase_templates.yaml` is missing or empty.

#### Scenario: missing template falls back
- **WHEN** `phase_templates.yaml` is absent
- **THEN** the Loop engine SHALL invoke the legacy black-box phase handler
- **AND** existing v2.0 workflows SHALL continue to work unchanged

