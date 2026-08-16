# mcp-fallback Specification

## Purpose
This specification defines the REST API fallback behavior when the Hub MCP Server is unreachable. The MCP Client SHALL detect connection failures and automatically fall back to direct GitHub REST API calls, issuing a warning to maintain operation continuity. Grounded in proposal Section "错误处理".

## ADDED Requirements

### Requirement: Automatic fallback on MCP Server unreachable

When the MCP Client cannot connect to the Hub MCP Server (connection timeout, DNS failure, or TCP connection refused), it SHALL automatically fall back to direct GitHub REST API calls using the `requests` library.

#### Scenario: MCP Server unreachable triggers automatic fallback
- **WHEN** `mcp_client.call_tool("hub_read_issue", ...)` is called and MCP Server connection fails within 5 seconds
- **THEN** the client SHALL log `fallback_attempted: true` to trace
- **AND** SHALL attempt equivalent GitHub REST API call directly
- **AND** SHALL issue a warning to stderr: `"MCP Server unreachable, falling back to REST API"`

#### Scenario: Fallback preserves return schema
- **WHEN** REST fallback is triggered for `hub_read_issue`
- **THEN** the returned Issue object SHALL have the same JSON schema as the MCP response
- **AND** the caller SHALL receive the same structured data regardless of transport used

### Requirement: Fallback warning suppression

Users SHALL be able to suppress the fallback warning via `MCPSuppressFallbackWarning=true` environment variable.

#### Scenario: Warning suppressed when env var set
- **WHEN** `MCPSuppressFallbackWarning=true` is set
- **AND** MCP Server is unreachable
- **THEN** the client SHALL NOT print warning to stderr
- **AND** SHALL still perform REST fallback silently

### Requirement: Fallback uses same authentication

The REST fallback SHALL use the same `GITHUB_TOKEN` environment variable as the MCP transport.

#### Scenario: Fallback uses same token
- **WHEN** REST fallback is triggered
- **THEN** the direct `requests.get()` call SHALL use `Authorization: Bearer <token>` with the same `GITHUB_TOKEN`
- **AND** SHALL use the same fine-grained token scoped to `rdd-hub`

### Requirement: Fallback rate limit handling

The REST fallback SHALL apply the same rate limit handling (exponential backoff, retry) as MCP transport.

#### Scenario: Fallback respects rate limits
- **WHEN** REST fallback receives 403 rate limit response
- **THEN** the client SHALL wait and retry with exponential backoff (same as MCP transport)
- **AND** SHALL log the rate limit event to `.mcp-trace.jsonl`

### Requirement: Fallback failure propagates error

If both MCP Server unreachable AND REST fallback fails, the client SHALL return the REST error, not the MCP connection error.

#### Scenario: Both MCP and REST fail
- **WHEN** MCP Server is unreachable AND REST API returns 500
- **THEN** the client SHALL return the REST error with details
- **AND** the trace entry SHALL contain both `mcp_error` and `rest_error` fields
