## ADDED Requirements

### Requirement: guide-arch-skill
The system SHALL provide `skills/guide-arch.md` as the architecture definition phase state machine.

The skill SHALL implement 5 sub-phases: setup, adr-create, architecture, roadmap-define, arch-done.

#### Scenario: arch phase complete
- **WHEN** user completes all 5 sub-phases
- **THEN** arch_done gate check runs (from v2-core-foundation)
- **AND** `.zcf/.arch-handoff.json` is written with: ADR count, roadmap state, gap analysis

#### Scenario: adr-create required
- **WHEN** user reaches `adr-create` sub-phase
- **THEN** user is guided through ADR template
- **AND** ADR is created in `docs/adr/`

### Requirement: guide-plan-skill
The system SHALL provide `skills/guide-plan.md` as the change generation phase state machine.

Forked from `guide-spec.md` with roadmap-related logic removed. Implements 4 sub-phases: scan, propose, deps, plan-done.

#### Scenario: plan phase complete
- **WHEN** user completes all 4 sub-phases
- **THEN** plan_done gate check runs
- **AND** `.zcf/.plan-handoff.json` is written with: active changes, artifacts state, deps analysis

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
