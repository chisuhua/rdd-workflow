# workflow-design-phase Specification (delta)

## ADDED Requirements

### Requirement: design-handoff v2 with changes_pre_created

The design phase SHALL emit `.rddf/state/.design-handoff.json` at schema version 2, adding a required `changes_pre_created` array field listing change names pre-created during design approval. The v2 schema SHALL keep `additionalProperties: false`. Consumers (guide-plan intake) MUST accept both v1 (treating `changes_pre_created` as empty) and v2 payloads.

#### Scenario: v2 handoff 写入与消费

- GIVEN two proposals were approved with change creation in the design phase
- WHEN design-done completes
- THEN `.design-handoff.json` has `version: 2` and `changes_pre_created` containing both change names
- AND guide-plan intake accepts the payload without error

#### Scenario: v1 向后兼容

- GIVEN an existing v1 `.design-handoff.json` (no `changes_pre_created`)
- WHEN guide-plan intake validates it
- THEN validation passes and `changes_pre_created` is treated as an empty list
