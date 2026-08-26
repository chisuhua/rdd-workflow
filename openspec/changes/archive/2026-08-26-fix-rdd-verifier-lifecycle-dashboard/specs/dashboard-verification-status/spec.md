## ADDED Requirements

### Requirement: Dashboard SHALL expose implementation, verification, and archive dimensions separately

Dashboard change data SHALL preserve the existing lifecycle `status` and add verification metadata. Renderers SHALL expose enough information to distinguish not implemented, implemented awaiting verification, implemented with failed verification, verification halted, verified/archive-ready, archived after verification, and bypassed or legacy archived changes.

#### Scenario: Implemented change awaiting verification is visible
- **GIVEN** a change has completed tasks
- **AND** verification state is missing, pending, or stale
- **WHEN** dashboard data is collected
- **THEN** the change includes an explicit pending verification state
- **AND** archive readiness is false

#### Scenario: Failed verification is visible
- **GIVEN** a task-complete change has `verification.state=failed`
- **WHEN** dashboard is rendered in terminal, plain, or JSON mode
- **THEN** it shows failed verification
- **AND** includes failed AC identifiers and the recommended route when available

#### Scenario: Halted verification is distinct from ordinary failure
- **GIVEN** a change reached the verifier retry limit
- **WHEN** dashboard data is rendered
- **THEN** it shows a blocked/halted verification state
- **AND** does not present the change as archive-ready

#### Scenario: Verified archive-ready change is distinct from archived change
- **GIVEN** a current passing verdict matches the branch tip
- **WHEN** dashboard data is rendered before archive
- **THEN** it shows verified/archive-ready
- **AND** after archive it shows archived-after-verification

#### Scenario: Bypassed and legacy archives are distinguishable
- **GIVEN** an archived change has bypass metadata or lacks verifier metadata
- **WHEN** dashboard data is rendered
- **THEN** it shows bypassed or legacy/unknown verification
- **AND** does not show a normal verified state

### Requirement: Verification status schema SHALL be explicit and versioned

The iteration change entry SHALL include an optional `verification` object with explicit enum and nullability. The schema SHALL add `7` to the supported version enum while keeping backward compatibility for v3–v6.

```json
"verification": {
  "state": "pending|running|passed|failed|halted|bypassed|legacy|unknown",
  "verdict_sha": "<branch tip sha or null>",
  "checked_at": "<iso timestamp or null>",
  "route": "archive-ready|guide-ship|guide-plan|halted|null",
  "loop_count": 0,
  "failed_acs": ["AC-2"],
  "bypass_reason": null,
  "bypass_source": null,
  "archive_ready": false
}
```

#### Scenario: Schema v7 accepts verification object
- **GIVEN** an iteration entry has a `verification` object with all required fields
- **WHEN** validated against iteration schema v7
- **THEN** it passes

#### Scenario: Legacy v3–v6 entries remain readable
- **GIVEN** an iteration entry without `verification`
- **WHEN** read by dashboard or archive gate
- **THEN** it is treated as `verification.state=unknown` for active changes
- **AND** as `verification.state=legacy` for archived changes

#### Scenario: Schema rejects invalid verification states
- **GIVEN** an iteration entry has `verification.state=invalid_value`
- **WHEN** validated against iteration schema v7
- **THEN** it fails

### Requirement: Dashboard JSON SHALL expose structured verification fields

JSON dashboard output SHALL include structured per-change verification data rather than requiring consumers to parse display strings. Existing fields and historical entries without verification metadata SHALL remain valid.

#### Scenario: JSON consumer receives verification object
- **GIVEN** a change has verification metadata
- **WHEN** `rddf dashboard --json` renders the data
- **THEN** the change includes `verification.state`, `verification.verdict_sha`, `verification.checked_at`, `verification.route`, `verification.loop_count`, `verification.failed_acs`, `verification.bypass_reason`, `verification.bypass_source`, and `verification.archive_ready`

#### Scenario: Plain and terminal renderers remain readable
- **GIVEN** changes have mixed implementation and verification states
- **WHEN** dashboard renders in terminal or plain mode
- **THEN** the changes section uses stable short verification codes (`pending`, `running`, `passed`, `failed`, `halted`, `bypassed`, `legacy`, `unknown`)
- **AND** a short `VERIFY` column or summary line conveys the state without truncating `verified-archive-ready` or `archived-after-verification`
- **AND** a detail line shows failed ACs and route when applicable

#### Scenario: Status text is not truncated
- **GIVEN** a change name and a verification summary together exceed the renderer width
- **WHEN** terminal or plain renderers output the row
- **THEN** the change name is abbreviated on the right
- **AND** the verification short code is preserved
- **AND** no part of the verification summary is silently removed

### Requirement: Icon map SHALL cover all verification states

Both terminal and plain renderers SHALL map every verification state to a stable icon or character. Unknown states SHALL fall back to a stable character without raising.

#### Scenario: Terminal and plain icons are defined
- **WHEN** dashboard data is rendered
- **THEN** each of `pending`, `running`, `passed`, `failed`, `halted`, `bypassed`, `legacy`, `unknown` has a defined terminal icon and a defined plain character

#### Scenario: Unknown verification state renders without error
- **GIVEN** a change entry has a verification state that is not in the icon map
- **WHEN** dashboard is rendered
- **THEN** the row uses the fallback character
- **AND** the renderer does not raise