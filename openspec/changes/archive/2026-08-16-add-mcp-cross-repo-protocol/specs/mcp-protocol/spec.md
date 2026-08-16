# mcp-protocol Specification

## Purpose
This specification defines the MCP protocol transport layer, authentication, and rate limiting for the Hub-and-Spoke cross-repo communication. It covers Stdio and Streamable HTTP dual transport, GitHub PAT fine-grained token scopes, and GitHub API rate limit handling. Grounded in ADR-0029 (MCP Integration Principles).

## ADDED Requirements

### Requirement: MCP protocol version

The system SHALL use MCP v0.5+ (2025-Q2 stable) for all Hub-Spoke communication.

#### Scenario: Client announces MCP v0.5 in handshake
- **WHEN** MCP Client connects to Hub MCP Server
- **THEN** the client SHALL send protocol version `0.5` in the handshake `protocolVersion` field
- **AND** the server SHALL respond with supported version confirmation

### Requirement: Dual transport support

The MCP Client SHALL support both Stdio and Streamable HTTP transports. The transport SHALL be selected based on the `MCP_TRANSPORT` environment variable (`stdio` or `http`), defaulting to `stdio`.

#### Scenario: Stdio transport used by default
- **WHEN** `MCP_TRANSPORT` is not set or set to `stdio`
- **THEN** the MCP Client SHALL spawn the server as a subprocess and communicate via stdin/stdout
- **AND** the subprocess SHALL be managed by the Python `mcp.client` module

#### Scenario: Streamable HTTP transport when configured
- **WHEN** `MCP_TRANSPORT` is set to `http`
- **THEN** the MCP Client SHALL connect to `MCP_SERVER_URL` via Streamable HTTP
- **AND** SHALL send all requests as HTTP POST with JSON body

### Requirement: GitHub PAT fine-grained authentication

The MCP Client SHALL use a GitHub Personal Access Token with fine-grained scopes limited to the `rdd-hub` repository only. The token SHALL be sourced from the `GITHUB_TOKEN` environment variable.

#### Scenario: Token injected via environment variable
- **WHEN** the MCP Client initializes
- **THEN** it SHALL read `GITHUB_TOKEN` from the environment
- **AND** SHALL pass it as the `Authorization: Bearer <token>` header to the MCP Server

#### Scenario: Token missing prevents connection
- **WHEN** `GITHUB_TOKEN` is not set
- **THEN** the MCP Client SHALL raise `MCPConfigurationError` with message `"GITHUB_TOKEN environment variable required"`
- **AND** SHALL NOT attempt connection

### Requirement: Rate limit handling

The MCP Client SHALL handle GitHub API rate limits gracefully, retrying with exponential backoff after rate limit reset.

#### Scenario: 403 rate limit response triggers retry
- **WHEN** MCP Server returns HTTP 403 with `X-RateLimit-Remaining: 0`
- **THEN** the client SHALL wait until `X-RateLimit-Reset` timestamp
- **AND** SHALL retry the request with exponential backoff (max 3 retries)

#### Scenario: Rate limit exceeded after retries fails gracefully
- **WHEN** MCP Client has retried 3 times and still receives 403 rate limit
- **THEN** the client SHALL return `error: "rate_limit_exceeded"` with `retry_after` field
- **AND** SHALL log the event to `.mcp-trace.jsonl`

### Requirement: Token scope restriction enforcement

The MCP Server (running in Hub) SHALL validate that incoming PAT tokens are scoped only to `rdd-hub` repo. Requests with broader scopes SHALL be rejected with HTTP 401.

#### Scenario: Valid fine-grained token accepted
- **WHEN** MCP Server receives request with `Authorization: Bearer <token>` scoped only to `rdd-hub`
- **THEN** the server SHALL process the request normally

#### Scenario: Broad scope token rejected
- **WHEN** MCP Server receives request with token having `repo` scope (all repos)
- **THEN** the server SHALL return HTTP 401 with `error: "insufficient_token_scope"`
- **AND** SHALL log the rejection
