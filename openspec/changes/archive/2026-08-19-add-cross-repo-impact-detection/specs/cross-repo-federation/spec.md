## ADDED Requirements

### Requirement: Cross-Repo Impact Detection at Proposal Generation

`add-improve` MUST detect whether a new proposal touches any Hub `contracts/*.yaml` and surface that to the human owner as an actionable warning.

#### Scenario: Single contract keyword match surfaces RFC suggestion
**WHEN** `.rddf/improvements/<name>.md` body mentions a path matching Hub `contracts/auth-v2.yaml` (e.g. `auth/` or `auth-v2`)

**THEN** `detect_cross_repo_impact.py` MUST output a warning: `⚠️ Detected Hub contract: contracts/auth-v2.yaml — consider initiating RFC`

**AND** MUST suggest `category: cross-repo-federation` if not already set

#### Scenario: Multiple contract matches output stakeholder list
**WHEN** the proposal body matches multiple Hub contracts (e.g. `auth-v2.yaml` and `user-profile.json`)

**THEN** the output MUST list all stakeholders derived from each contract's `x-owners:` annotation

**AND** MUST offer one-line summary per match for human triage

#### Scenario: No match produces no noise
**WHEN** the proposal body has no Hub contract matches

**THEN** `detect_cross_repo_impact.py` MUST exit silently (no output, no warning)

**AND** MUST NOT modify `.rddf/improvements/<name>.md`

#### Scenario: Auto-detection is opt-in via env var
**WHEN** `RDDF_SKIP_CROSS_REPO_DETECTION=yes` is set

**THEN** `add-improve` MUST skip the detection step entirely

**AND** MUST proceed with the standard add-improve flow

### Requirement: Hub Contract Ownership Metadata

Hub contract files (`contracts/*.yaml` and `contracts/*.json`) MUST carry an `x-owners:` extension field enumerating GitHub `org/repo` strings as the source of stakeholder auto-suggestion.

#### Scenario: Owner annotation read from contract header
**WHEN** `contracts/auth-v2.yaml` starts with `x-owners: [your-org/repo-backend, your-org/repo-security]`

**THEN** `detect_cross_repo_impact.py` MUST extract `your-org/repo-backend` and `your-org/repo-security` as stakeholder suggestions

#### Scenario: Missing owner annotation gracefully defaults
**WHEN** a Hub contract has no `x-owners:` field

**THEN** the contract MUST still match by file name, but stakeholders MUST default to `[]` (empty list)
