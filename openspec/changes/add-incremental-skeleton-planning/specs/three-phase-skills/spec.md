## MODIFIED Requirements

### Requirement: guide-plan-skill
The system SHALL provide `skills/guide-plan.md` as the change generation phase state machine.

Forked from `guide-spec.md` with roadmap-related logic removed. Implements 5 sub-phases: scan, propose, fill, deps, plan-done.

The fill sub-phase SHALL:
- Display `planned` status changes sorted by deps-recommended order
- Allow user to select changes for progressive content fill
- Fill design.md and tasks.md using openspec instructions
- Transition change status from `planned` to `proposed` on successful fill

The plan-done gate SHALL allow mixed state: at least 1 `proposed` change + any number of `planned` changes.

#### Scenario: plan phase complete with mixed state
- **WHEN** user completes all sub-phases with 2 `proposed` changes and 3 `planned` changes
- **THEN** plan_done gate check passes
- **AND** `.rddf/state/plan-handoff.json` is written with: `planned=N, proposed=M`
- **AND** deps analysis covers all N+M changes

#### Scenario: plan phase complete with only planned changes
- **WHEN** user attempts plan-done with only `planned` changes and zero `proposed`
- **THEN** plan_done gate check fails
- **AND** message: "至少需要一个 proposed 状态 change"

#### Scenario: fill skeleton change
- **WHEN** user selects fill from guide-plan menu and chooses a `planned` change
- **THEN** system creates design.md and tasks.md using openspec instructions
- **AND** change status transitions to `proposed`
- **AND** new artifacts are committed