# contract-lint Specification

## Purpose
CI gate integration: `rddf contract-check` CLI for validating Spoke implementations against Hub contracts before merge.

## Behavior
Exit codes:
- 0 = compliant (No-Diff or Low/Medium severity)
- 1 = Breaking-Change detected (CI should block merge)

Flags: `--hub <path>`, `--local <path>`, `--dry-run`, `--format json|markdown`

## Requirements
### Requirement: contract-check-blocks-on-breaking-changes

`rddf contract-check` SHALL validate a Spoke implementation against the Hub contract and
SHALL exit non-zero when it finds a breaking change, so a CI merge is blocked; its
`--dry-run` mode SHALL print the plan without applying it.

#### Scenario: a compliant implementation exits zero

- **WHEN** `rddf contract-check` finds no breaking change
- **THEN** it SHALL exit with code 0

#### Scenario: a breaking change exits non-zero

- **WHEN** `rddf contract-check` finds a breaking change
- **THEN** it SHALL exit with a non-zero code

#### Scenario: the dry run only prints the plan

- **WHEN** `rddf contract-check --dry-run` runs
- **THEN** it SHALL print the plan
- **AND** it SHALL NOT apply it

## Test Coverage
- 3 bats integration tests (ok exit 0 / breaking exit 1 / --dry-run)
