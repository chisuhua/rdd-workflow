# add-strict-human-approval Specification

## Purpose
TBD - created by archiving change add-strict-human-approval-for-cross-repo-changes. Update Purpose after archive.
## Requirements
### Requirement: Cross-repo proposals MUST be blocked from AI auto-approval

When `approve_proposal.sh` is invoked with `--auto-accept` and the proposal's category is `cross-repo-federation`, the script MUST hard-block with exit code 3. Category detection MUST use `.rddf/improvements/<name>.md` head `**分类**:` field as the single source of truth (SSOT); it MUST NOT depend on `openspec/changes/<name>/roadmap-meta.yaml`, which is created later by the same script and therefore fail-open on first approve.

**Rationale**: Oracle review (2026-08-18) found the original roadmap-meta.yaml source fail-open: on first approve the file does not yet exist, so `is_cross_repo_proposal()` silently returned false and `--auto-accept` passed. ADR-0031 §分类传递契约 names the improvements file as SSOT.

#### Scenario: First approve of cross-repo proposal with --auto-accept
**WHEN** `.rddf/improvements/<name>.md` contains `**分类**: cross-repo-federation` and `openspec/changes/<name>/` does not exist

**THEN** `approve_proposal.sh <name> --auto-accept` MUST exit 3

**AND** the output MUST direct the user to `--manual --hub-issue <org/repo#N>`

#### Scenario: Proposal without cross-repo category unaffected
**WHEN** `.rddf/improvements/<name>.md` has a `**分类**:` value other than `cross-repo-federation` (or no such field)

**THEN** the cross-repo gate MUST NOT trigger and the normal approve flow proceeds

### Requirement: STRICT_DESIGN_GATE blocks design-done for unapproved cross-repo proposals

When `STRICT_DESIGN_GATE=yes` is set and a cross-repo proposal exists where the corresponding Hub Issue status is not `Approved`, the design-done gate MUST fail. This creates a second layer of protection beyond the approve_proposal blocking.

#### Scenario: design-done blocked when Hub Issue not Approved
**WHEN** `rddf design-gate-check` runs during guide-design Phase 4 with `STRICT_DESIGN_GATE=yes` set

**AND** a cross-repo proposal `cross-repo-auth-v2` exists with Hub Issue `org/rdd-hub#42` in status `📢 RFC` (not Approved)

**THEN** the gate MUST fail with exit code 1

**AND** output MUST show: `🛡️ 检测到 1 个挂起的 cross-repo 提案` with proposal details

---

### Requirement: RDDF_REQUIRE_HUB_APPROVAL enables explicit cross-repo enforcement

The environment variable `RDDF_REQUIRE_HUB_APPROVAL=yes` MUST enable strict cross-repo mode where:
1. Any cross-repo proposal approval requires explicit human confirmation
2. The approval MUST reference a valid Hub Issue that is in `Approved` status
3. There is NO escape path from this gate (fail-closed)

#### Scenario: RDDF_REQUIRE_HUB_APPROVAL=yes forces strict mode
**WHEN** `RDDF_REQUIRE_HUB_APPROVAL=yes` is set in environment

**AND** a proposal with `**分类**: cross-repo-federation` exists

**THEN** any approval attempt without `--manual` and valid Hub Issue reference MUST be rejected

---

### Requirement: All cross-repo decisions MUST be recorded in audit log

Every human decision on a cross-repo proposal MUST be written to `.rddf/state/.cross-repo-audit.jsonl` (JSON Lines format). The log is append-only and MUST NOT be modified after writing.

**Rationale**: ADR-0030 §S5 identifies audit log integrity as a medium-risk concern. This requirement establishes the minimum audit trail for cross-repo decisions.

#### Scenario: Human approval recorded in audit log
**WHEN** a human approver with GitHub username `alice` manually approves cross-repo proposal `cross-repo-auth-v2`

**AND** the corresponding Hub Issue is `org/rdd-hub#42` with status `Approved`

**THEN** a new line MUST be appended to `.rddf/state/.cross-repo-audit.jsonl`

**AND** the line MUST contain: `{"timestamp": "<ISO8601>", "proposal_name": "cross-repo-auth-v2", "hub_issue": "org/rdd-hub#42", "approver": "alice", "decision": "approved"}`

#### Scenario: Human rejection recorded in audit log
**WHEN** a human approver rejects a cross-repo proposal via interactive prompt

**THEN** a new line MUST be appended with `decision: "rejected"`

#### Scenario: Auto-block due to Hub Issue not Approved
**WHEN** an approval attempt is blocked because Hub Issue is not in Approved status

**THEN** a new line MUST be appended with `decision: "blocked"` and reason field

---

### Requirement: Audit log entries MUST include all required fields

Each audit log entry MUST contain:
- `timestamp`: ISO 8601 format (e.g., `2026-08-15T10:30:00Z`)
- `proposal_name`: Name of the proposal
- `hub_issue`: Full Hub Issue reference (e.g., `org/rdd-hub#42`)
- `approver`: GitHub username of human decision-maker
- `decision`: One of `approved`, `rejected`, `blocked`
- `reason`: Optional field explaining why blocked/rejected

#### Scenario: Audit log validates required fields
**WHEN** a new audit log entry is about to be written

**AND** any required field is missing or null

**THEN** the entry MUST NOT be written

**AND** an error MUST be logged to stderr

---

### Requirement: Interactive prompt MUST NOT leak credentials via process listing

When `--manual` mode prompts for GitHub username, the input MUST be read via stdin (not command-line arguments or environment variables) to prevent exposure via process listing.

**Rationale**: ADR-0031 §Implementation details item 3 specifies stdin input to avoid process listing leakage.

#### Scenario: Username input via stdin
**WHEN** user invokes `rddf approve-proposal cross-repo-auth-v2 --manual`

**THEN** the interactive prompt asks for GitHub username via stdin using `read -s` (silent mode)

**AND** the input MUST NOT appear in `ps aux` or `/proc/<pid>/cmdline`

---

### Requirement: Hub Issue status MUST be re-fetched before approval

Before any cross-repo proposal approval is granted, the script MUST re-fetch the current status of the corresponding Hub Issue from GitHub. Cached or previously observed status MUST NOT be used for approval decisions.

**Rationale**: ADR-0031 §Implementation details item 5 specifies Hub Issue status recheck to prevent race conditions where the Hub status changes after local observation but before approval.

#### Scenario: Approval blocked when Hub Issue status changed to not Approved
**WHEN** user runs `rddf approve-proposal cross-repo-auth-v2 --manual`

**AND** the re-fetched status shows Hub Issue `org/rdd-hub#42` is now `📢 RFC` (not Approved)

**THEN** the approval MUST be rejected

**AND** output MUST state: `Hub Issue org/rdd-hub#42 状态已变更，需要重新确认`

#### Scenario: Approval succeeds when re-fetched status is Approved
**WHEN** user runs `rddf approve-proposal cross-repo-auth-v2 --manual --hub-issue "org/rdd-hub#42"`

**AND** the re-fetched Hub Issue status is `✅ Approved`

**AND** all other requirements are satisfied

**THEN** the approval MUST proceed

---

### Requirement: Network failure during Hub status recheck MUST fail-closed

If the Hub Issue status cannot be re-fetched due to network failure, authentication failure, or GitHub API error, the approval MUST be rejected (fail-closed).

#### Scenario: Network error during Hub status fetch
**WHEN** the GitHub API call to fetch Hub Issue status fails with any error

**THEN** the approval MUST be rejected with exit code 1

**AND** output MUST state: `无法获取 Hub Issue 状态，批准被阻断`

#### Scenario: Invalid Hub Issue reference
**WHEN** user provides a Hub Issue reference that does not exist or is not accessible

**THEN** the approval MUST be rejected with clear error messaging

---

### Requirement: Hub Issue status MUST be verified against exact status values

The approval logic MUST check for explicit `Approved` status, not approximate matches or substring matching against other RFC statuses.

**Statuses to check against:**
- `✅ Approved` - Allow approval
- `📢 RFC` - Block approval
- `🚧 Draft` - Block approval
- `❌ Rejected` - Block approval

#### Scenario: RFC status correctly identified and blocked
**WHEN** Hub Issue `org/rdd-hub#42` has status `📢 RFC`

**THEN** the approval MUST be blocked because status is not `Approved`

---

### Requirement: Proposal classification MUST be detected from roadmap-meta.yaml

The `**分类**` field in `.rddf/improvements/<name>.md` is the SSOT for proposal classification. When a change is created, this value MUST be copied to `openspec/changes/<name>/roadmap-meta.yaml` under the `category` field. All gate logic MUST read from `roadmap-meta.yaml.category`.

**Rationale**: ADR-0031 §Classification transmission contract establishes that plan/ship gates must read from `roadmap-meta.yaml.category` and not from `proposal-approved.md`.

#### Scenario: Classification detected from roadmap-meta.yaml
**WHEN** `approve_proposal.sh` evaluates whether to block a proposal

**AND** `openspec/changes/cross-repo-auth-v2/roadmap-meta.yaml` contains `category: cross-repo-federation`

**THEN** it MUST read the `category` field from `roadmap-meta.yaml`

**AND** NOT from `proposal-approved.md` or any other source

---

### Requirement: Unknown classification MUST fail-closed

If a proposal's `category` field is missing, empty, or contains an unrecognized value, the system MUST treat it as a potential cross-repo proposal and apply the strict gate. The system MUST NOT silently allow unclassified proposals to bypass cross-repo checks.

#### Scenario: Missing classification treated as strict
**WHEN** `roadmap-meta.yaml` exists but `category` field is missing or empty

**THEN** the approval MUST be treated with strict mode

**AND** output should indicate: `⚠️ 分类未知，应用跨项目严格审查`

#### Scenario: Unknown classification value blocked
**WHEN** `category` contains an unrecognized value like `unknown-category`

**AND** approval is attempted with `RDDF_REQUIRE_HUB_APPROVAL=yes`

**THEN** the approval MUST be rejected

**AND** message MUST state that the classification is not recognized

---

### Requirement: .openspec.yaml schema extension for cross_repo_review

The `.openspec.yaml` schema MUST be extended to include a `cross_repo_review.required` boolean field to explicitly declare when cross-repo review is required for a change.

#### Scenario: .openspec.yaml has cross_repo_review.required field
**WHEN** `openspec/changes/<name>/.openspec.yaml` contains:
```yaml
cross_repo_review:
  required: true
```

**THEN** approval logic MUST treat this as requiring cross-repo human approval regardless of category

---

### Requirement: design_content_review.sh upgrade for cross-repo category

The `skills/guide-design/scripts/design_content_review.sh` script MUST be upgraded to perform additional review checks when the proposal category is `cross-repo-federation`.

#### Scenario: Cross-repo proposal triggers additional review
**WHEN** a proposal with `category: cross-repo-federation` is being reviewed

**THEN** `design_content_review.sh` MUST verify that:
1. Hub Issue reference is provided in the proposal
2. The Hub Issue exists and is accessible
3. At least one human reviewer is explicitly assigned

---

### Requirement: SKIP_DESIGN_HANDOFF remains available as emergency escape (Hub-side only)

The `SKIP_DESIGN_HANDOFF=yes` escape hatch is preserved for Hub repository maintainers to bypass gate in genuine emergencies. Spoke repositories MUST NOT have any bypass path.

| Variable | Scope | Effect |
|----------|-------|--------|
| `SKIP_DESIGN_HANDOFF` | Hub maintainers only | Emergency bypass of design handoff gate. Requires PR review. |
| Any Spoke-side bypass | Spoke repositories | MUST NOT exist (P1 security requirement) |

#### Scenario: Hub maintainer uses emergency bypass (Hub-side only)
**WHEN** a genuine emergency requiring immediate approval occurs

**AND** Hub maintainer with proper permissions sets `SKIP_DESIGN_HANDOFF=yes`

**AND** creates a PR to document the emergency bypass

**THEN** the bypass MAY be used

**BUT** this path is NOT available to Spoke repositories

---

### Requirement: No Spoke-side bypass paths exist

As specified in ADR-0031 §Negative/Risks, there MUST be NO escape path from the cross-repo approval gate in Spoke repositories. The only "bypass" is via Hub-side `STRICT_HUB_APPROVAL=no` which requires Hub maintainer PR approval.

#### Scenario: Verify no Spoke bypass exists
**WHEN** attempting to find any environment variable, flag, or configuration that bypasses cross-repo approval in a Spoke repository

**THEN** no such bypass MUST exist

**AND** all approval paths for cross-repo proposals require human manual approval

---

### Requirement: Unit tests MUST cover 5 key paths

The implementation MUST have unit tests covering these 5 critical paths as specified in ADR-0031 §后续待办:

#### Test Path 1: auto-block
**WHEN** `test_cross_repo_auto_block` runs

**THEN** it verifies that `--auto-accept` flag is blocked for cross-repo proposals with exit code 3

**AND** asserts output contains blocking message

#### Test Path 2: gate-detect
**WHEN** `test_gate_detect_unapproved_hub_issue` runs

**THEN** it verifies `STRICT_DESIGN_GATE=yes` detects unapproved Hub Issue and blocks design-done

**AND** asserts gate fails with error message showing pending cross-repo proposal

#### Test Path 3: manual-confirm
**WHEN** `test_manual_confirmation_flow` runs

**THEN** it verifies `--manual` mode prompts for username and records decision

**AND** asserts interactive prompt appears

**AND** asserts decision is recorded in audit log

#### Test Path 4: audit-write
**WHEN** `test_audit_log_write` runs

**THEN** it verifies audit log entry is written with all required fields

**AND** asserts `.cross-repo-audit.jsonl` contains new entry with timestamp, proposal_name, hub_issue, approver, decision

#### Test Path 5: hub-state-recheck
**WHEN** `test_hub_state_recheck_blocks_stale_approval` runs

**THEN** it verifies approval is blocked when re-fetched Hub Issue status differs from expected

**AND** asserts approval fails with message indicating Hub Issue status changed

---

### Requirement: Test data isolation

Tests MUST NOT modify production state files. Each test MUST use temporary directories and mock GitHub API responses.

#### Scenario: Tests use isolated temp directories
**WHEN** unit tests are running

**AND** tests need to write state files

**THEN** they MUST use `$BATS_TMPDIR` or equivalent temporary directory

**AND** NOT write to `.rddf/state/` in the production repository

---

### Requirement: Mock GitHub API for Hub Issue status

Tests MUST mock GitHub API responses to avoid network dependencies and ensure deterministic test outcomes.

#### Scenario: Mock Hub Issue Approved status
**WHEN** a test scenario requires Hub Issue `org/rdd-hub#42` with `Approved` status

**THEN** the GitHub API call MUST be mocked to return `Approved` status

**AND** no actual network call is made

#### Scenario: Mock Hub Issue RFC status
**WHEN** a test scenario requires Hub Issue `org/rdd-hub#42` with `RFC` status

**THEN** the GitHub API call MUST be mocked to return `RFC` status

### Requirement: --manual mode MUST require a human GitHub username

For cross-repo proposals approved with `--manual --hub-issue <org/repo#N>`, the script MUST obtain a non-empty GitHub username before accepting, either from the `RDDF_APPROVE_ACTOR` environment variable (CI fallback) or via `read -t 30 -rp "GitHub username: "`. Empty input or 30s timeout MUST exit 4.

**Rationale**: ADR-0031 §实现细节 3 — the audit log must record a human decision-maker; a bare `--manual` flag proves no human involvement.

#### Scenario: Empty stdin rejects with exit 4
**WHEN** `approve_proposal.sh <name> --manual --hub-issue <org/repo#N>` runs with empty stdin and no `RDDF_APPROVE_ACTOR`

**THEN** the script MUST exit 4

#### Scenario: Username via stdin is accepted
**WHEN** a non-empty username is provided via stdin or `RDDF_APPROVE_ACTOR`

**THEN** the username is recorded as `actor`/`approver` in the audit log entry

### Requirement: Hub Issue status MUST be re-fetched before local approve

Before accepting a cross-repo approval, the script MUST re-fetch the Hub Issue via `gh issue view <N> --repo <org/repo> --json state,labels`. If state is not `OPEN` or the `approved` label is missing, the script MUST exit 6 (or exit 5 when `RDDF_REQUIRE_HUB_APPROVAL=yes`). Network-class failures (gh missing, timeout, unreachable) MUST fail-open with a warning; auth-class failures (401/403) MUST fail-closed.

**Rationale**: ADR-0031 §实现细节 5 — local state may be stale relative to Hub (race condition). Fail-open is permitted only for network-class errors so offline work is not blocked.

#### Scenario: Closed Hub Issue rejects with exit 6
**WHEN** the re-fetched Hub Issue has state `CLOSED`

**THEN** the script MUST write an audit entry with `decision=fail` and exit 6

#### Scenario: Missing approved label with RDDF_REQUIRE_HUB_APPROVAL=yes exits 5
**WHEN** `RDDF_REQUIRE_HUB_APPROVAL=yes` and the re-fetched Hub Issue lacks the `approved` label

**THEN** the script MUST write an audit entry with `decision=fail` and exit 5

#### Scenario: Network error fails open with warning
**WHEN** the `gh` invocation fails due to a network-class error

**THEN** the script MUST print a warning and continue the approve flow

### Requirement: Every cross-repo decision MUST be written to the audit log

Before accept, the script MUST call `cross_repo_audit.append_audit_log_entry` to append one JSONL entry to `.rddf/state/.cross-repo-audit.jsonl` containing `timestamp`, `proposal_name`, `hub_issue`, `approver`, `actor`, `decision`, `hub_state`, and `hub_labels`. Rejected decisions MUST be recorded with `decision=fail` before exiting.

**Rationale**: ADR-0031 §实现细节 4 — the audit module previously had no production caller, so the log was always empty (dead code).

#### Scenario: Successful approve appends audit entry
**WHEN** a cross-repo approval completes the human + Hub checks

**THEN** `.rddf/state/.cross-repo-audit.jsonl` MUST contain a new line with `decision=approve`, the provided `actor`, and the re-fetched `hub_state`/`hub_labels`

