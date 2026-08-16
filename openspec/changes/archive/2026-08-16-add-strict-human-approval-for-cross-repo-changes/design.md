# Design: add-strict-human-approval-for-cross-repo-changes

## Context

This change implements the cross-repo human approval gate specified in ADR-0031 (Human-in-Loop for Cross-Repo). The Hub-and-Spoke federation architecture (ADR-0030) established that cross-project RFCs require mandatory human decision-making because AI misjudgment in cross-repo scenarios can cause widespread pollution across multiple Spoke repositories.

Current `approve_proposal.sh` can be executed automatically by AI when `STRICT_DESIGN_GATE` or `SKIP_DESIGN_HANDOFF` are not enabled. This creates a critical security gap where AI could auto-approve a cross-repo proposal without human oversight.

## Goals / Non-Goals

**Goals:**
- Block AI auto-approval of cross-repo proposals with exit code 3
- Require human confirmation via interactive stdin prompt for cross-repo decisions
- Record all cross-repo decisions to append-only `.cross-repo-audit.jsonl`
- Re-check Hub Issue status from GitHub before granting approval (prevent race conditions)
- Extend `.openspec.yaml` schema with `cross_repo_review.required` field
- Upgrade `design_content_review.sh` to handle cross-repo category review

**Non-Goals:**
- Do NOT modify single-repository proposal approval flow (keeps existing `y/N` interaction)
- Do NOT create new interaction modes (Human-in-Loop node types unchanged per ADR-0005)
- Do NOT implement Hub-side human fallback (belongs to Hub Repo scope)
- Do NOT add any Spoke-side bypass paths (P1 security requirement)

## Decisions

### 1. Fail-Closed by Default

**Decision**: When `RDDF_REQUIRE_HUB_APPROVAL=yes` is set or when a proposal has `category: cross-repo-federation`, all approval paths require explicit human confirmation. Any failure in the approval chain (network error, Hub Issue not Approved, missing manual confirmation) results in rejection.

**Rationale**: ADR-0031 §Decision establishes fail-closed as the only acceptable behavior for cross-repo changes. Unlike single-repo changes where AI can proceed with warning, cross-repo changes have compounding effects across federated repositories.

**Alternatives considered:**
- Fail-open with warning: Rejected — violates P1 security requirement that AI cannot auto-approve cross-repo changes
- Timeout-based retry: Rejected — would introduce unpredictable behavior and delay human decisions

### 2. Two-Layer Gate Enforcement

**Decision**: Implement two independent enforcement layers:
1. **Primary gate** (`approve_proposal.sh`): Blocks auto-approval at proposal approval time
2. **Secondary gate** (`STRICT_DESIGN_GATE=yes`): Blocks design-done when Hub Issue not Approved

**Rationale**: The two gates operate at different phases (approval vs. design-done) and serve different purposes. The primary gate prevents AI from auto-granting approval. The secondary gate ensures design-done cannot proceed until the Hub Issue status is confirmed Approved. This defense-in-depth approach is consistent with ADR-0027's security-first design philosophy.

**Alternatives considered:**
- Single gate only: Rejected — single points of failure are unacceptable for cross-repo changes
- Three-layer with MCP verification: Deferred to future ADR (add-mcp-cross-repo-protocol)

### 3. Stdin-Based Interactive Confirmation

**Decision**: Use `read -s` (silent mode) to read GitHub username from stdin when `--manual` mode is invoked. Never accept credentials via command-line arguments or environment variables that could be exposed via process listing.

**Rationale**: ADR-0031 §Implementation details item 3 explicitly requires stdin input to avoid credential leakage via `ps aux` or `/proc/<pid>/cmdline`. This is a practical security measure against process inspection attacks.

**Alternatives considered:**
- Environment variable: Rejected — `env` command and `/proc/<pid>/environ` can leak variables
- Command-line argument: Rejected — `ps aux` shows full command line
- Config file: Rejected — adds complexity without security benefit

### 4. Hub Issue Status Recheck Before Approval

**Decision**: Before any cross-repo approval is granted, the script MUST make a live GitHub API call to re-fetch the Hub Issue's current status. Cached or previously-observed status values MUST NOT be used for approval decisions.

**Rationale**: Prevents race conditions where Hub Issue status changes between local observation and approval. ADR-0031 §Implementation details item 5 explicitly requires this recheck.

**Alternatives considered:**
- Use cached status with TTL: Rejected — introduces stale data risk that defeats the purpose of status verification
- Optimistic approval with rollback: Rejected — adds complexity and doesn't guarantee rollback success

### 5. Classification Detection via roadmap-meta.yaml

**Decision**: All cross-repo gates MUST read proposal classification from `roadmap-meta.yaml.category`. The `category` field is populated at change creation time from `.rddf/improvements/<name>.md`'s `**分类**` field.

**Rationale**: ADR-0031 §Classification transmission contract establishes `roadmap-meta.yaml` as the SSOT for plan/ship gate decisions. Using the index (`proposal-approved.md`) would require additional lookups and introduce inconsistency risk.

**Alternatives considered:**
- Read from proposal-approved.md: Rejected — index doesn't carry classification field
- Read directly from .rddf/improvements/: Rejected — improvements are ephemeral and don't persist through the change lifecycle

### 6. Audit Log Append-Only via JSON Lines

**Decision**: All cross-repo decisions are recorded to `.rddf/state/.cross-repo-audit.jsonl` in JSON Lines format (one JSON object per line). The file is append-only; no modification or deletion of existing entries is supported.

**Rationale**: JSON Lines format allows streaming writes without file locking. Append-only semantics guarantees audit trail integrity. ADR-0030 §S5 identifies audit log integrity as a medium-risk concern; this designmitigates tampering.

**Alternatives considered:**
- SQLite database: Rejected — adds dependency and doesn't improve integrity guarantees
- JSON array file: Rejected — requires read-modify-write which creates race conditions and file locking complexity
- Git-based immutable log: Deferred — requires Hub-side GitHub integration

### 7. No Spoke-Side Escape Hatches

**Decision**: There are ZERO escape paths from the cross-repo approval gate in Spoke repositories. The only bypass mechanism is Hub-side `STRICT_HUB_APPROVAL=no` which requires Hub maintainer PR approval.

**Rationale**: ADR-0031 §Negative/Risks explicitly states "逃生口缺失" (no escape path). This is a P1 security requirement. Any Spoke-side bypass would defeat the purpose of the human approval gate.

**Alternatives considered:**
- Spoke-side `SKIP_CROSS_REPO_GATE`: Explicitly rejected in ADR-0031
- Conditional bypass via env var: Rejected — would create security theater

## Risks / Trade-offs

### Risk: Decision Delay
**Risk**: Cross-repo RFC average decision time increases by 1-3 days due to required human confirmation.

**Mitigation**: Hub Issue status changes trigger local notifications via `rddf watch-hub`. Human reviewers are explicitly assigned during design review.

### Risk: AI Workflow Blocked
**Risk**: AI assistants cannot automatically proceed with cross-repo changes, requiring human intervention.

**Mitigation**: The system prompt (via `add-spoke-system-prompt-injection` future change) explicitly states "AI cannot auto-approve cross-repo changes". AI can continue working on other tasks while waiting.

### Risk: Network Dependency for Hub Status
**Risk**: Approval requires GitHub API access to re-check Hub Issue status.

**Mitigation**: Fail-closed behavior ensures network failures don't result in accidental approval. Clear error messaging helps humans diagnose and retry.

### Risk: Audit Log Tampering
**Risk**: Local audit log could be modified or deleted before archival.

**Mitigation**: ADR-0030 §S5 specifies daily `rddf audit-verify` to compare local log with Hub-side record. Critical decisions are also recorded in Hub Issue comments (immutable via GitHub).

## Implementation Notes

### File Locations
- `approve_proposal.sh`: `skills/guide-design/scripts/approve_proposal.sh`
- `design_content_review.sh`: `skills/guide-design/scripts/design_content_review.sh`
- `cross_repo_audit.py`: `skills/_lib/cross_repo_audit.py` (new file)
- `.openspec.yaml` schema: Extended in-place

### Exit Codes
- `0`: Approval succeeded
- `1`: General error or Hub Issue not Approved
- `2`: Usage error (missing required arguments)
- `3`: Cross-repo auto-approval blocked (AI tried to auto-approve)
- `4`: Hub Issue status recheck failed (network error)

### Schema Extension
```yaml
# In .openspec.yaml
cross_repo_review:
  required: boolean  # Default: false
```
