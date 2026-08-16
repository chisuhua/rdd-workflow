# mcp-trace Specification

## Purpose
This specification defines the MCP trace log schema and entry format for observability of all Hub-Spoke communications. Every MCP tool call SHALL produce a JSONL entry in `.rddf/state/.mcp-trace.jsonl` containing tool name, arguments, result or error, transport used, timestamp, and fallback status. This enables audit trails and debugging of cross-repo AI workflows. Grounded in proposal Section "可观测性".

## ADDED Requirements

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
