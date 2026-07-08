# three-phase-skills Specification

## Purpose
TBD - created by archiving change v2-core-foundation. Update Purpose after archive.
## Requirements
### Requirement: guide-arch-skill
The system SHALL provide `skills/guide-arch.md` as the architecture definition phase state machine.

The skill SHALL implement 5 sub-phases: setup, adr-create, architecture, roadmap-define, arch-done.

#### Scenario: arch phase complete
- **WHEN** user completes all 5 sub-phases
- **THEN** arch_done gate check runs (from v2-core-foundation)
- **AND** `.rddf/state/arch-handoff.json` is written with: ADR count, roadmap state, gap analysis

#### Scenario: adr-create required
- **WHEN** user reaches `adr-create` sub-phase
- **THEN** user is guided through ADR template
- **AND** ADR is created in `docs/adr/`

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

### Requirement: guide-spec-alias
The system SHALL provide `skills/guide-spec.md` as a backward-compatible alias that internally invokes `guide-arch.md` then `guide-plan.md`.

#### Scenario: v1.x user invokes guide-spec
- **WHEN** v1.x user invokes `skill_use("guide-spec")`
- **THEN** skill transparently runs guide-arch then guide-plan
- **AND** user sees no difference from v1.x behavior

### Requirement: guide-recommender-three-phase
The system SHALL extend `skills/guide.md` to recommend among three phases (arch, plan, ship) based on project state.

#### Scenario: Recommender suggests arch
- **WHEN** project has no `docs/adr/` directory
- **THEN** recommender suggests `skill_use("guide-arch")`

#### Scenario: Recommender suggests plan
- **WHEN** project has ADRs but no `openspec/changes/` directory
- **THEN** recommender suggests `skill_use("guide-plan")`

