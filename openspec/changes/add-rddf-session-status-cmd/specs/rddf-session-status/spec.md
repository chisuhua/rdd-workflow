# rddf-session-status — Capability Spec

## ADDED Requirements

### Requirement: Status Subcommand Outputs Table + Binding + Counts

The rddf-session skill SHALL provide a `status` subcommand that emits:
- A binding line identifying the current active session for the calling owner (or "no current binding")
- A table of all rddf-sessions (sorted: active first, then by started_at descending)
- A counts summary grouped by session state

#### Scenario: Caller has active session

- GIVEN `OPENCODE_SESSION_ID` matches an `active` rddf-session in `sessions.json`
- WHEN the user invokes `skill_use("rddf-session", "status")`
- THEN output includes `📍 Current: <sid>` line, table header `session_id kind owner state`, and counts section

#### Scenario: Caller has no active session

- GIVEN no `active` rddf-session with `owner_opencode_session_id` matching the caller
- WHEN `status` is invoked
- THEN output shows `📍 No current binding` followed by the table and counts (if any sessions exist)

#### Scenario: Empty sessions.json

- GIVEN `sessions.json` contains zero sessions
- WHEN `status` is invoked
- THEN output shows `📍 No current binding` and `(no rddf-sessions found)`

### Requirement: Status Subcommand Is Read-Only

The `status` subcommand MUST NOT mutate `sessions.json` — no create_session, update_session_status, refresh_heartbeat, or archive_history calls.

#### Scenario: Status invocation leaves file unchanged

- GIVEN a `sessions.json` with N sessions and SHA256 hash H1
- WHEN `status` is invoked
- THEN the file's SHA256 hash remains H1 after the call

### Requirement: guide Recommender Shows Active Binding

The `guide` skill's `scan-state.sh` SHALL emit a binding line via `scan_binding_lines` whenever the calling owner has an active rddf-session, so the menu can surface "you are in session rds_xxx".

#### Scenario: Active session owned by caller

- GIVEN `OPENCODE_SESSION_ID` matches an active session
- WHEN `scan-state.sh::scan_state` runs
- THEN `BINDING_LINES` is exported and `📍 Current: <sid>` is printed to stdout

#### Scenario: No active session owned by caller

- GIVEN no active session owned by caller (only owned by others, or none)
- WHEN `scan-state.sh::scan_state` runs
- THEN no `📍` line is emitted