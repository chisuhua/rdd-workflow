# mcp-trace: Specifications

> Source: `_lib/schemas/mcp_trace_schema.json` v1
> Change: add-cross-repo-state-schemas

## ADDED Requirements

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
