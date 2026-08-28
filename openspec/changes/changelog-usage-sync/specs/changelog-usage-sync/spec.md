# CHANGELOG-USAGE Sync Capability

## ADDED Requirements

### Requirement: USAGE.md version banner synced with CHANGELOG.md

The system SHALL verify that `USAGE.md` top banner reflects the current release version documented in `CHANGELOG.md` `[Unreleased]` section or latest released tag.

The banner SHALL be placed between `<!-- VERSION_BANNER_START -->` and `<!-- VERSION_BANNER_END -->` markers.

#### Scenario: Banner mentions latest release

- **WHEN** `CHANGELOG.md` contains `## [v3.0.0]` section
- **THEN** `USAGE.md` banner SHALL include reference to v3.0.0 features
- **AND** the four-stage architecture (arch → design → plan → ship → verify) SHALL be mentioned

#### Scenario: Pre-commit hook flags stale banner

- **WHEN** developer modifies `CHANGELOG.md` `[Unreleased]` section
- **AND** `USAGE.md` banner is not updated accordingly
- **THEN** pre-commit hook emits a warning listing required USAGE.md changes

### Requirement: Doctor module check for CHANGELOG-USAGE drift

The `_lib/sync_usage_banner.py` module SHALL provide a check function that compares `CHANGELOG.md` [Unreleased] Added/Changed/Fixed sections against `USAGE.md` banner.

#### Scenario: Doctor detects missing USAGE references

- **WHEN** developer runs `python3 _lib/sync_usage_banner.py --check`
- **THEN** any CHANGELOG entries not mentioned in USAGE are reported as drift
- **AND** exit code is 0 (no drift) or 1 (drift detected)

#### Scenario: Doctor does not auto-modify USAGE.md

- **WHEN** doctor check detects CHANGELOG-USAGE drift
- **THEN** a warning message SHALL be printed listing required USAGE.md changes
- **AND** the doctor SHALL NOT modify USAGE.md automatically
- **AND** the doctor SHALL exit with non-blocking code (unless --strict flag set)
