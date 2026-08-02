# spec-validation-gates Specification (delta)

## ADDED Requirements

### Requirement: plan-done isComplete 校验

The plan-done gate SHALL query `openspec status --change <name> --json` for each active change and emit a warning when `isComplete` is false. This check coexists with the ADR-0015 `openspec_validate` check and MUST NOT duplicate its `openspec validate --all --strict --json` invocation.

#### Scenario: 未完成的 change 给出 warning

- GIVEN an active change whose `status --json` reports `isComplete: false`
- WHEN the plan-done gate runs
- THEN a warning listing the incomplete change is emitted, and the ADR-0015 strict validate check still runs exactly once

### Requirement: skip_specs 接入

For changes whose `roadmap-meta.yaml` has `change_type` of `doc-only` or `test-only`, the system SHALL write `skip_specs: true` into the change's `.openspec.yaml`, replacing ad-hoc zero-delta workarounds.

#### Scenario: doc-only change 免 delta

- GIVEN a change with `change_type: "doc-only"`
- WHEN the change is created
- THEN `.openspec.yaml` contains `skip_specs: true` and `openspec validate <name> --strict --json` passes without any specs delta
