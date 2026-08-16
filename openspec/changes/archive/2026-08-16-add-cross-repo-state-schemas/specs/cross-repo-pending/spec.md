# cross-repo-pending: Specifications

> Source: `_lib/schemas/cross_repo_pending_schema.json` v1
> Change: add-cross-repo-state-schemas

## ADDED Requirements

### Requirement: Hub Issue pending tracking

The system SHALL track Hub Issues that block local design-done/plan-done gates.

#### Scenario: Pending issue blocks plan-done gate
- **WHEN** a Hub Issue referenced in `.rddf/state/.cross-repo-pending.json` has status different from `expected_status`
- **THEN** the `blocked_gates` indicate which local gates remain blocked
- **AND** `last_polled_at` records the last check time

#### Scenario: Pending issue unblocks gate
- **WHEN** a Hub Issue status transitions to `expected_status`
- **THEN** the blocked gate becomes eligible to proceed
- **AND** the pending issue entry may be removed or marked resolved

---

### Requirement: Pending issue entry validation

Each `pending_issues` entry MUST contain required fields and follow defined patterns.

#### Scenario: Valid pending issue entry
- **GIVEN** a pending issue with `hub_issue`, `local_proposal`, `expected_status`, `blocked_gates`, `added_at`
- **WHEN** schema validation runs
- **THEN** the entry passes validation

#### Scenario: Invalid hub_issue pattern
- **GIVEN** a pending issue with `hub_issue` not matching `^[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+#[0-9]+$`
- **WHEN** schema validation runs
- **THEN** validation fails with pattern error

#### Scenario: Invalid blocked_gate value
- **GIVEN** a pending issue with `blocked_gates` containing non-enum value
- **WHEN** schema validation runs
- **THEN** validation fails with enum error

---

### Requirement: Pending state file structure

The `.rddf/state/.cross-repo-pending.json` file SHALL maintain a list of pending Hub Issues.

#### Scenario: File contains version and pending_issues array
- **WHEN** the pending state file is read
- **THEN** it contains `version` (const: 1), `pending_issues` array, and `last_updated` timestamp

#### Scenario: Empty pending_issues when no blockers
- **WHEN** no Hub Issues are blocking any gates
- **THEN** `pending_issues` is an empty array `[]`
- **AND** `last_updated` reflects the last modification time
