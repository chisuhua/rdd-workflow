# cross-repo-audit: Specifications

> Source: `_lib/schemas/cross_repo_audit_schema.json` v1
> Change: add-cross-repo-state-schemas

## ADDED Requirements

### Requirement: Cross-repo decision audit logging

The system SHALL record every cross-repo decision (RFC initiation, approval, rejection, gate block) in newline-delimited JSON format.

#### Scenario: Record RFC initiation
- **WHEN** a Spoke repo initiates an RFC that references a Hub Issue
- **THEN** a new JSON line is appended to `.rddf/state/.cross-repo-audit.jsonl`
- **AND** `decision` is `initiate`, `hub_status_at_decision` is recorded

#### Scenario: Record approval decision
- **WHEN** a human or AI agent approves a cross-repo change
- **THEN** a JSON line with `decision: approve` and `actor` is appended
- **AND** `reason` may contain optional explanation

#### Scenario: Record rejection decision
- **WHEN** a cross-repo change is rejected
- **THEN** a JSON line with `decision: reject` and `reason` is appended
- **AND** `hub_status_at_decision` reflects the Hub Issue state at decision time

---

### Requirement: Audit entry actor tracking

Audit entries MUST record actor information with type and identifier.

#### Scenario: Human actor decision
- **WHEN** a human makes a decision
- **THEN** `actor.type` is `human` and `actor.id` is the GitHub username

#### Scenario: AI agent actor decision
- **WHEN** an AI agent makes a decision
- **THEN** `actor.type` is `ai-agent` and `actor.id` is the agent identifier

#### Scenario: CI bot actor decision
- **WHEN** CI automation makes a decision
- **THEN** `actor.type` is `ci-bot` and `actor.id` identifies the bot

---

### Requirement: Audit entry schema validation

Audit entries MUST pass schema validation before being written.

#### Scenario: Valid audit entry
- **GIVEN** an audit entry with all required fields
- **WHEN** jsonschema validation runs
- **THEN** the entry passes validation

#### Scenario: Missing required field
- **GIVEN** an audit entry missing `hub_issue`
- **WHEN** schema validation runs
- **THEN** validation fails with required property error

#### Scenario: Invalid decision enum
- **GIVEN** an audit entry with `decision` not in `initiate, approve, reject, block, defer, revoke`
- **WHEN** schema validation runs
- **THEN** validation fails with enum error
