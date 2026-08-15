# cross-repo-federation: Specifications

## ADDED Requirements

### Requirement: RFC Issue Creation via rddf report-issue

`rddf report-issue --category=rfc` MUST create a GitHub Issue in the Hub repository with RFC prefix in title.

#### Scenario: Create RFC Issue from Spoke repository
- **WHEN** the user runs `rddf report-issue --category=rfc --title "[RFC] Title" --stakeholders "org/repo" --gate "Design-Gate" --contract-impact "Breaking-Change"`
- **THEN** a GitHub Issue is created in the Hub repository with title prefixed with `[RFC]`
- **AND** the Issue is associated with the `RDD Cross-Repo Sync` Project V2
- **AND** the Issue contains labels: `RFC`, `Design-Gate`, `Breaking-Change`
- **AND** a local pending entry is created in `.rddf/state/.cross-repo-pending.json`

#### Scenario: RFC Issue Project V2 field mapping
- **WHEN** the Issue is created in Hub
- **THEN** `Status` field is set to `RFC`
- **AND** `Stakeholders` field is set to the comma-separated org/repo list
- **AND** `Gate` field is set to the `--gate` argument value
- **AND** `Contract Impact` field is set to the `--contract-impact` argument value

#### Scenario: RFC creation dry-run mode
- **WHEN** `rddf report-issue --category=rfc --dry-run` is executed
- **THEN** no GitHub Issue is created
- **AND** the command outputs what would be created without making changes
- **AND** the exit code is 0

---

### Requirement: rddf sync-hub Contract Synchronization

`rddf sync-hub --contract <path>` MUST download a contract from the Hub repository to the local `openspec/` directory.

#### Scenario: Sync a single contract from Hub
- **WHEN** the user runs `rddf sync-hub --contract auth-v2.yaml`
- **THEN** the file is downloaded from `rdd-hub/contracts/auth-v2.yaml`
- **AND** saved to `openspec/specs/auth-v2/spec.md` (converted extension)
- **AND** `git diff` shows only the target file changed

#### Scenario: Idempotent sync produces no diff
- **WHEN** `rddf sync-hub --contract auth-v2.yaml` has been executed successfully
- **AND** the same command is run again
- **THEN** the file content is identical
- **AND** `git diff` shows no changes
- **AND** the command reports "Contract already up-to-date"

#### Scenario: Sync dry-run mode
- **WHEN** `rddf sync-hub --contract auth-v2.yaml --dry-run` is executed
- **THEN** no file is downloaded
- **AND** the command outputs the source URL and destination path
- **AND** the command indicates what the content hash would be
- **AND** exit code is 0

---

### Requirement: rddf watch-hub One-time Polling

`rddf watch-hub --once` MUST perform a single poll of Hub Issue statuses and trigger approval actions.

#### Scenario: Single poll for RFC Issue status
- **WHEN** `rddf watch-hub --once --owner=org/rdd-hub` is executed
- **AND** there are pending entries in `.rddf/state/.cross-repo-pending.json`
- **THEN** the command fetches the current status of all pending Hub Issues
- **AND** for each Issue that changed to "Approved" status, `approve_proposal.sh` is called
- **AND** the pending entry is updated or removed

#### Scenario: Filter by stakeholders
- **WHEN** `--filter "Stakeholders:[email protected]"` is specified
- **THEN** only Issues where `[email protected]` is in the Stakeholders field are checked
- **AND** other pending entries are skipped

#### Scenario: Watch command completes in single poll
- **GIVEN** `rddf watch-hub --once` is executed
- **WHEN** the poll completes
- **THEN** the command exits
- **AND** no background process remains

#### Scenario: Watch dry-run mode
- **WHEN** `rddf watch-hub --once --dry-run` is executed
- **THEN** no GitHub API calls that modify state are made
- **AND** the command outputs what actions would be taken
- **AND** exit code is 0

---

### Requirement: Pending State Tracking

The system MUST maintain a local pending state file tracking Hub Issues that are waiting for approval.

#### Scenario: Create pending entry for RFC Issue
- **WHEN** `rddf report-issue --category=rfc` successfully creates an RFC Issue
- **THEN** a pending entry is added to `.rddf/state/.cross-repo-pending.json`
- **AND** the entry contains: `hub_issue_url`, `contract_path`, `gate_type`, `expected_status`, `created_at`, `stakeholders`, `title`, `status`

#### Scenario: Pending entry structure
- **WHEN** the pending state is read
- **THEN** each entry contains required fields:
  - `hub_issue_url`: Full URL to the Hub Issue
  - `gate_type`: The gate that should be unblocked (e.g., "Design-Gate")
  - `expected_status`: The status that should trigger unblock (e.g., "Approved")
  - `created_at`: ISO timestamp of when the entry was created
  - `status`: One of `pending | approved | rejected | superseded`

#### Scenario: Multiple pending entries
- **WHEN** multiple RFC Issues are created from different Spoke repositories
- **THEN** all entries are present in the `entries` array
- **AND** each entry is independently tracked

---

### Requirement: Design Gate Integration

The design-done gate MUST check for pending Hub Issues before allowing design phase completion.

#### Scenario: Design gate blocks when RFC pending
- **WHEN** a change has an active RFC Issue in Hub with status "RFC"
- **AND** `guide-design` or design-done gate is invoked
- **THEN** the gate blocks completion with a hard error
- **AND** the message indicates which Hub Issue is blocking
- **AND** the command shows the Hub Issue URL

#### Scenario: Design gate allows when RFC approved
- **WHEN** a change has an RFC Issue that is now "Approved" in Hub
- **AND** the design-done gate is invoked
- **THEN** the gate allows completion
- **AND** the pending entry is marked as resolved

#### Scenario: Manual override via SKIP_HUB_CHECK
- **WHEN** `SKIP_HUB_CHECK=true` environment variable is set
- **AND** the design-done gate runs
- **THEN** it skips the Hub status check
- **AND** it outputs a warning that manual override is in effect
- **AND** the change can proceed

---

### Requirement: Offline Behavior

All cross-repo commands MUST handle network failures gracefully without blocking workflows.

#### Scenario: Sync uses cache when offline
- **WHEN** Hub is unreachable during `rddf sync-hub`
- **THEN** the command outputs "⚠️ Hub unreachable, using local cache"
- **AND** if a cached version exists, it is used
- **AND** if no cached version exists, an error is reported
- **AND** the exit code is 0 (graceful degradation)

#### Scenario: Watch graceful degradation offline
- **WHEN** Hub is unreachable during `watch-hub --once`
- **THEN** the command outputs a warning
- **AND** it exits with code 0
- **AND** no pending entries are modified

---

### Requirement: Rate Limits Compliance

All Hub interactions MUST respect GitHub API rate limits (5000 req/hour for authenticated requests).

#### Scenario: Batch fetch via GraphQL
- **WHEN** `watch-hub` polls Hub
- **THEN** it uses a single GraphQL query to fetch all Issue statuses
- **AND** it makes at most 1 API call regardless of pending entry count

#### Scenario: Read-only token sufficiency
- **WHEN** a GitHub token with only `repo:read` scope is used
- **AND** `rddf sync-hub` or `rddf watch-hub` is executed
- **THEN** the command succeeds
- **AND** no write operations are attempted

---

### Requirement: Local/Manual Acceptance Gates

A manual acceptance gate MUST exist for approving changes locally before Hub approval.

#### Scenario: Local approve action
- **WHEN** `approve_proposal.sh` is called with a change name and approval type
- **THEN** the corresponding pending entry is marked as approved
- **AND** the local state file is updated
- **AND** the design-done gate is unblocked

#### Scenario: Gate passes with local approval
- **WHEN** a pending entry has `status: approved` with `approval_type: local`
- **AND** the design-done gate checks
- **THEN** it passes
- **AND** it logs the manual/local approval

---

### Requirement: JSON Schema Validation

The pending state file MUST be validated against the JSON schema in `skills/_lib/schemas/cross-repo-pending-schema.json`.

#### Scenario: Schema validation on read
- **WHEN** any rdd-workflow command reads the pending state
- **THEN** it validates against the schema
- **AND** if invalid, reports a validation error with which fields are missing

#### Scenario: Required schema fields
- **WHEN** a pending entry is written
- **THEN** it requires: `hub_issue_url`, `gate_type`, `expected_status`, `created_at`
- **AND** optional: `contract_path`, `stakeholders`, `title`, `status`
