# fix-adr-0031-safety-gate-substantiation: Specifications

## MODIFIED Requirements

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

## ADDED Requirements

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
