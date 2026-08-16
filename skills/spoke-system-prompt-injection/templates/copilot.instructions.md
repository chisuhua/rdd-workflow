# rdd-hub Cross-Repo Protocol Rules (GitHub Copilot)

You are operating in a Spoke repository that participates in the rdd-hub
Hub-and-Spoke federation. Follow these rules when using Hub MCP tools.

## Rule 1: RFC Initiation
Before creating RFC Issues, check for duplicates via `hub_read_issue`.
Include `stakeholders` field in every RFC body. Wait ≥1 second between
parallel RFC creation to respect GitHub rate limits (5000 req/hour).

## Rule 2: RFC Review
Apply Hub feedback before proceeding with implementation.
Never skip RFC review even for small changes.

## Rule 3: Sync
Pull contract changes via `hub_sync_contract`.
Fail fast on sync errors — never silently retry.

## Rule 4: Auto-Approval Prohibition
- Never auto-approve RFCs without Hub confirmation
- Never suppress sync warnings
- Never bypass rate limit handling
- Never log raw tokens
