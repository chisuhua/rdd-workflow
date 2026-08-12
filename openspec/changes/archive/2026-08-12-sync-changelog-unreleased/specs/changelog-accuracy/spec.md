# Changelog Accuracy

## ADDED Requirements

### Requirement: Unreleased section covers all post-boundary commits

The project SHALL maintain a `[Unreleased]` section in `CHANGELOG.md` that documents every commit since the previous release boundary.

#### Scenario: Drift detection

- **GIVEN** release boundary at commit `B` (last CHANGELOG update)
- **WHEN** running `git log --oneline B..HEAD -- CHANGELOG.md` returns 0 commits
- **AND** `git log --oneline B..HEAD` excluding CHANGELOG.md returns ≥ 1 commit
- **THEN** the post-flow-analysis reporter SHOULD detect this drift and file an issue
- **AND** the issue category SHALL be `arch_drift`
- **AND** the issue description SHALL mention "CHANGELOG drift: N commits unrecorded"

#### Scenario: Drift resolution

- **GIVEN** the reporter detects N commits unrecorded
- **WHEN** a sync-changelog-unreleased change is merged
- **THEN** `git log --oneline B..HEAD -- CHANGELOG.md` SHALL return ≥ 1 commit
- **AND** the reporter SHALL NOT report this drift again
