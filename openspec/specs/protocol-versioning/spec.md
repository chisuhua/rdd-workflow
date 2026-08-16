# protocol-versioning Specification

## Purpose
TBD - created by archiving change add-spoke-system-prompt-injection. Update Purpose after archive.
## Requirements
### Requirement: centralized-protocol-version

All templates SHALL reference a single canonical protocol version identifier.

#### Scenario: Version identifier present
- **WHEN** any template is read
- **THEN** it SHALL contain `protocol_version: 1.0` or higher
- **AND** the version SHALL match across all five templates

#### Scenario: Version in inject.md
- **WHEN** `inject.md` is read
- **THEN** it SHALL define the `protocol_version` variable used by all templates

### Requirement: version-upgrade-path

Protocol version upgrades SHALL be managed through version comparison logic in deploy.sh.

#### Scenario: Skip downgrade injection
- **WHEN** deploy.sh runs with `--force-version` on a file with protocol_version 2.0
- **AND** inject.md defines protocol_version 1.0
- **THEN** it SHALL NOT inject the lower version

#### Scenario: Force upgrade
- **WHEN** deploy.sh runs with `--force-upgrade`
- **THEN** it SHALL replace existing protocol content with the current version regardless of version comparison

### Requirement: version-display

The deploy.sh script SHALL report the protocol version being deployed.

#### Scenario: Version reported on deploy
- **WHEN** `deploy.sh --tools cursor` runs successfully
- **THEN** output SHALL include "Deploying protocol_version: X.Y"

#### Scenario: Version displayed on status
- **WHEN** `deploy.sh --status --tools cursor` runs
- **THEN** it SHALL display the currently installed protocol version
- **AND** compare it with the available version in inject.md

