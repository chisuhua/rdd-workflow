## ADDED Requirements

### Requirement: beta-version-published
The system SHALL publish `rdd-workflow@2.0.0-beta` to npm with explicit beta designation.

#### Scenario: Beta install succeeds
- **WHEN** user runs `npm install rdd-workflow@2.0.0-beta` in a clean project
- **THEN** installation succeeds
- **AND** v2.0 skills (guide-arch, guide-plan, guide-ship, loop) are available

### Requirement: changelog-completeness
The system SHALL provide a `CHANGELOG.md` documenting the v2.0.0-beta release.

Required sections: New Features, Breaking Changes, Known Issues, Migration Guide link.

#### Scenario: User reads CHANGELOG
- **WHEN** user opens CHANGELOG.md
- **THEN** they see comprehensive release notes
- **AND** understand what's new and what may break

### Requirement: feedback-channel-active
The system SHALL provide a feedback collection mechanism via GitHub Issues.

#### Scenario: User submits feedback
- **WHEN** user files a beta-feedback GitHub Issue
- **THEN** it is labeled `beta-feedback`
- **AND** triaged within 48 hours

### Requirement: performance-baseline
The system SHALL meet baseline performance targets for beta release.

Targets: state vector read/write < 10ms, event log query < 100ms (10K events), loop engine startup < 1s.

#### Scenario: Performance targets met
- **WHEN** benchmark suite runs
- **THEN** all targets are met
- **AND** metrics are published in CHANGELOG

### Requirement: p0-issue-response
The system SHALL respond to P0 (blocking/data loss) issues within 24 hours of reporting.

#### Scenario: P0 issue reported
- **WHEN** P0 issue is filed via GitHub
- **THEN** maintainer acknowledges within 24 hours
- **AND** patch is released within 1 week
