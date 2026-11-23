# mcp-trace Specification

## Purpose
TBD - created by archiving change add-cross-repo-state-schemas. Update Purpose after archive.
## Requirements
### Requirement: MCP call tracing

The system SHALL record every MCP call between Hub and Spokes in newline-delimited JSON format.

#### Scenario: Trace spoke-to-hub MCP call
- **WHEN** a Spoke repo invokes an MCP tool (e.g., `hub_create_issue`)
- **THEN** a JSON record is appended to `.rddf/state/.mcp-trace.jsonl`
- **AND** `direction` is `spoke-to-hub`, `tool_name` is recorded

#### Scenario: Trace hub-to-spoke MCP call
- **WHEN** Hub invokes a tool on a Spoke
- **THEN** a JSON record with `direction: hub-to-spoke` is appended
- **AND** `actor_repo` identifies the target Spoke

#### Scenario: Record successful MCP call
- **WHEN** an MCP call succeeds
- **THEN** `result_status` is `success` and `error_message` is null

#### Scenario: Record failed MCP call
- **WHEN** an MCP call fails
- **THEN** `result_status` reflects error type (`error`, `rate-limited`, `unauthorized`, `timeout`)
- **AND** `error_message` contains the error details if available

---

### Requirement: MCP trace privacy

The system SHALL NOT write sensitive argument values to the trace.

#### Scenario: Args hashed for privacy
- **WHEN** an MCP call is recorded
- **THEN** `args_hash` contains SHA-256 hash of arguments
- **AND** actual argument values are never written to the trace

#### Scenario: Token ID for audit without exposing tokens
- **WHEN** an MCP call involves authentication
- **THEN** `token_id` is recorded for correlation
- **AND** the actual token value is never written

---

### Requirement: MCP trace validation

MCP trace entries MUST pass schema validation.

#### Scenario: Valid MCP trace entry
- **GIVEN** a trace entry with all required fields and valid enum values
- **WHEN** schema validation runs
- **THEN** the entry passes validation

#### Scenario: Invalid direction enum
- **GIVEN** a trace entry with `direction` not in `hub-to-spoke` or `spoke-to-hub`
- **WHEN** schema validation runs
- **THEN** validation fails with enum error

#### Scenario: Invalid tool_name enum
- **GIVEN** a trace entry with `tool_name` not in the defined MCP tool enum
- **WHEN** schema validation runs
- **THEN** validation fails with enum error

### Requirement: Trace file location and format

The trace log SHALL be stored at `.rddf/state/.mcp-trace.jsonl` in the Spoke repository root. Each entry SHALL be a valid JSON object on a single line.

#### Scenario: New trace file created on first call
- **WHEN** first MCP tool call occurs and `.rddf/state/.mcp-trace.jsonl` does not exist
- **THEN** the MCP Client SHALL create the file with parent directory if needed
- **AND** SHALL append the first JSONL entry

#### Scenario: Entry appended to existing trace file
- **WHEN** MCP tool call occurs and `.rddf/state/.mcp-trace.jsonl` exists
- **THEN** the new JSONL entry SHALL be appended to the file
- **AND** existing entries SHALL be preserved

### Requirement: Trace entry schema

Each JSONL trace entry SHALL contain the following fields:
- `timestamp`: ISO 8601 formatted UTC datetime string
- `tool_name`: string name of the MCP tool invoked
- `args`: object containing the arguments passed to the tool
- `result`: object containing the successful response (absent on error)
- `error`: object containing error details (absent on success)
- `transport`: string indicating transport used ("stdio" or "http")
- `fallback_attempted`: boolean indicating if REST fallback was triggered
- `duration_ms`: integer milliseconds of the call duration

#### Scenario: Successful call produces complete trace entry
- **WHEN** `hub_read_issue` call succeeds
- **THEN** the trace entry SHALL contain `tool_name: "hub_read_issue"`, `args`, `result`, `transport`, `fallback_attempted: false`, `duration_ms`, and `timestamp`
- **AND** `error` field SHALL be absent

#### Scenario: Failed call produces error trace entry
- **WHEN** `hub_read_issue` call fails with not_found
- **THEN** the trace entry SHALL contain `tool_name`, `args`, `error: {"code": "not_found", "message": "..."}`, `transport`, `fallback_attempted`, `duration_ms`, and `timestamp`
- **AND** `result` field SHALL be absent

### Requirement: Sensitive data redaction

The trace log SHALL redact `GITHUB_TOKEN` values and any field containing `token`, `secret`, or `password` in the key name.

#### Scenario: Token value redacted in args
- **WHEN** MCP call includes `args: {"token": "ghp_xxx"}`
- **THEN** the trace entry SHALL contain `args: {"token": "[REDACTED]"}`
- **AND** the raw token SHALL NOT appear in `.mcp-trace.jsonl`

### Requirement: Manual Hub validation gate trace

When a human manually validates the Hub MCP Server in the browser, the validation result SHALL be logged to `.mcp-trace.jsonl` with `tool_name: "hub_manual_validation"`.

#### Scenario: Manual validation logged
- **WHEN** Hub operator completes manual validation of MCP Server endpoint
- **THEN** a trace entry SHALL be written with `tool_name: "hub_manual_validation"`, `result: {"validated": true, "endpoint": <url>}`, and `timestamp`

