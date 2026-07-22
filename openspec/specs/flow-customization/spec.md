# flow-customization Specification

## Purpose
TBD - created by archiving change v3-flow-customization. Update Purpose after archive.
## Requirements
### Requirement: flow-yaml-customizations
The system SHALL read `.rdd-workflow/flow.yaml` if present and apply its `customizations.<phase>` directives (`insert_after`, `insert_before`, `replace`) to the default step sequence from `phase_templates.yaml`.

#### Scenario: user inserts a custom step
- **WHEN** `.rdd-workflow/flow.yaml` declares `customizations.plan.insert_after.generate_proposal` with step `compliance_review`
- **THEN** the effective plan phase steps SHALL include `compliance_review` immediately after `generate_proposal`

### Requirement: trigger-engine-restricted-dsl
The system SHALL evaluate step `trigger` expressions using a restricted DSL parser that supports `always`, `never`, `changes.any(predicate)`, `state.<path>` field access, comparisons, and logical operators — and SHALL NOT use `eval` or `exec`.

#### Scenario: trigger evaluates safely
- **WHEN** a step has `trigger: "changes.any(has_security_impact)"`
- **THEN** the TriggerEngine SHALL parse the expression via AST
- **AND** SHALL evaluate it without invoking Python `eval`
- **AND** if parsing fails the trigger SHALL evaluate to `false`

### Requirement: failure-handling-strategies
The system SHALL execute the configured `on_failure` strategy (`back_to:<step>`, `skip`, `abort`, or `escalate_to_human`) when a custom step fails, bounded by `on_failure_max_retries`.

#### Scenario: back_to bounded by retries
- **WHEN** a step with `on_failure: "back_to:generate_proposal"` and `on_failure_max_retries: 3` fails four times consecutively
- **THEN** the StepPipeline SHALL escalate to human instead of attempting a fourth back-to

### Requirement: backward-compatibility-no-config
The system SHALL behave identically to the default step pipeline when `.rdd-workflow/flow.yaml` is absent.

#### Scenario: no flow.yaml equals default
- **WHEN** `.rdd-workflow/flow.yaml` does not exist
- **THEN** the effective step sequence SHALL equal the default `phase_templates.yaml`
- **AND** existing v2.x workflows SHALL be unaffected

