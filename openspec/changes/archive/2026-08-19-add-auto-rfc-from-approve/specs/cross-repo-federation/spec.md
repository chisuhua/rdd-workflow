## ADDED Requirements

### Requirement: approve_proposal --auto-issue Automatically Creates Hub Issue

`approve_proposal.sh --manual --auto-issue` MUST call `report_issue_rfc.py` with the prepared draft, capture the resulting Hub Issue URL, and write it back to the proposal's draft JSON.

#### Scenario: Successful auto-issue updates draft + audit
**WHEN** `approve_proposal.sh <name> --manual --auto-issue` runs and Hub Issue creation succeeds

**THEN** `.rddf/state/.rfc-draft-<name>.json` MUST be updated with `hub_issue_url: <url>`

**AND** `.cross-repo-audit.jsonl` MUST contain a new entry with `decision=approve` and `hub_issue=<url>`

#### Scenario: Hub creation failure writes audit fail and keeps draft
**WHEN** `report_issue_rfc.py` returns non-zero (rate limit / network / auth error)

**THEN** `.cross-repo-audit.jsonl` MUST contain a `decision=fail` entry with `error_msg=<stderr>`

**AND** the draft JSON MUST remain with `status=pending` for human retry

**AND** `approve_proposal.sh` MUST exit 0 (approve already succeeded; only Hub creation failed)

#### Scenario: --hub-issue and --auto-issue are mutually exclusive
**WHEN** user passes both `--hub-issue <org/repo#N>` and `--auto-issue`

**THEN** `approve_proposal.sh` MUST exit 2 with message `ERROR: --hub-issue and --auto-issue are mutually exclusive`

#### Scenario: Auto-issue requires existing draft
**WHEN** `--auto-issue` is passed but `.rfc-draft-<name>.json` does not exist

**THEN** `approve_proposal.sh` MUST exit 4 with message `ERROR: --auto-issue requires rfc-draft for <name>; run rddf rfc-draft <name> first`
