# tests Specification

## Purpose
Define the integration test coverage for the spoke-system-prompt-injection change.

## ADDED Requirements

### Requirement: integration-test-file

The system SHALL provide `tests/integration/test_spoke_injection.bats` covering five key paths.

#### Scenario: deploy test
- **WHEN** `bats tests/integration/test_spoke_injection.bats` runs with "deploy" tag
- **THEN** it SHALL verify `deploy.sh --tools cursor` appends protocol to `.cursorrules`

#### Scenario: idempotent test
- **WHEN** `bats tests/integration/test_spoke_injection.bats` runs with "idempotent" tag
- **THEN** it SHALL verify running deploy twice produces identical result

#### Scenario: multi-tool test
- **WHEN** `bats tests/integration/test_spoke_injection.bats` runs with "multi-tool" tag
- **THEN** it SHALL verify deploying to multiple tools in one invocation

#### Scenario: uninstall test
- **WHEN** `bats tests/integration/test_spoke_injection.bats` runs with "uninstall" tag
- **THEN** it SHALL verify `--uninstall` removes protocol content

#### Scenario: backup test
- **WHEN** `bats tests/integration/test_spoke_injection.bats` runs with "backup" tag
- **THEN** it SHALL verify backup file is created before modification

### Requirement: test-environment-isolation

Integration tests SHALL NOT modify the host repository's `.rddf/` directory.

#### Scenario: Tests use temp directory
- **WHEN** any integration test runs
- **THEN** it SHALL create a temporary git repository in `$BATS_TMPDIR`
- **AND** not modify the source repository's state

### Requirement: test-covers-all-five-tools

The test suite SHALL verify deployment to all five AI tool configurations.

#### Scenario: All five tools tested
- **WHEN** the full test suite runs
- **THEN** each of Cursor, Cline, Continue, Copilot, and Claude SHALL have at least one test case
