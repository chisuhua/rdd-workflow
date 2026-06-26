## ADDED Requirements

### Requirement: migration-guide-content
The system SHALL provide a `docs/migration/v1-to-v2.md` guide that helps v1.x users transition to v2.0.

The guide SHALL include:
- Quick Start for v1.x Users
- Conceptual Changes (state machine → loop)
- Backward Compatibility (guide-spec alias, sync layer)
- FAQ

#### Scenario: v1.x user reads guide
- **WHEN** v1.x user opens the migration guide
- **THEN** they can follow Quick Start without prior v2 knowledge
- **AND** understand what changed conceptually
- **AND** know what remains backward compatible

### Requirement: readme-v2-update
The system SHALL update `README.md` to reflect v2.0 features.

Required sections: v2.0 features list, three-phase workflow diagram, Quick Start for v2.0.

#### Scenario: New user reads README
- **WHEN** new user reads README
- **THEN** they see v2.0 as the current recommended version
- **AND** can immediately use v2.0 features

### Requirement: usage-doc-update
The system SHALL update `USAGE.md` with v2.0 skills and Loop engine examples.

#### Scenario: User follows USAGE guide
- **WHEN** user follows USAGE.md
- **THEN** they can invoke guide-arch, guide-plan, guide-ship
- **AND** configure the loop engine
- **AND** see example configurations
