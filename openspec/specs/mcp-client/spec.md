# mcp-client Specification

## Purpose
TBD - created by archiving change add-mcp-cross-repo-protocol. Update Purpose after archive.
## Requirements
### Requirement: hub_read_issue tool

The MCP Client SHALL expose a `hub_read_issue` tool that accepts `issue_number` (integer), `owner` (string), and `repo` (string) parameters and returns a normalized Issue object conforming to the Hub Issue JSON Schema.

#### Scenario: Successful read returns normalized Issue
- **WHEN** Spoke AI calls `mcp_client.call_tool("hub_read_issue", {"issue_number": 42, "owner": "org", "repo": "rdd-hub"})`
- **THEN** the client SHALL return a JSON object containing `number`, `title`, `body`, `state`, `status`, `stakeholders`, `contract_impact`, and `labels`
- **AND** the response SHALL be logged to `.rddf/state/.mcp-trace.jsonl`

#### Scenario: Issue not found returns error
- **WHEN** Spoke AI calls `hub_read_issue` with a non-existent `issue_number`
- **THEN** the client SHALL return a JSON object with `error: "not_found"` and HTTP 404 equivalent code
- **AND** the error SHALL be logged to `.rddf/state/.mcp-trace.jsonl`

### Requirement: hub_create_issue tool

The MCP Client SHALL expose a `hub_create_issue` tool that accepts `title` (string), `body` (string), `stakeholders` (array of strings), and `contract_impact` (string) parameters and returns the created Issue object.

#### Scenario: Successful creation returns Issue with ID
- **WHEN** Spoke AI calls `mcp_client.call_tool("hub_create_issue", {"title": "RFC: New API", "body": "..."})`
- **THEN** the client SHALL return a JSON object with `number`, `title`, `body`, `state`, `created_at`, and `url`
- **AND** the issue SHALL be created in the Hub repository via MCP Server

#### Scenario: Missing required field returns validation error
- **WHEN** Spoke AI calls `hub_create_issue` without `title`
- **THEN** the client SHALL return `error: "validation_error"` with field name `"title"` as required
- **AND** no issue SHALL be created

### Requirement: hub_update_status tool

The MCP Client SHALL expose a `hub_update_status` tool that accepts `issue_number` (integer), `status` (string), and optional `comment` (string) parameters.

#### Scenario: Status update without comment
- **WHEN** Spoke AI calls `hub_update_status` with valid issue_number and status
- **THEN** the client SHALL update the Issue's `Status` custom field via MCP Server
- **AND** SHALL return `{"success": true, "issue_number": <n>, "status": <new_status>}`

#### Scenario: Status update with comment
- **WHEN** Spoke AI calls `hub_update_status` with issue_number, status, and comment
- **THEN** the client SHALL update the Issue status AND post a comment to the Issue
- **AND** SHALL return `{"success": true, "issue_number": <n>, "status": <new_status>, "comment_id": <id>}`

### Requirement: hub_sync_contract tool

The MCP Client SHALL expose a `hub_sync_contract` tool that accepts `contract_id` (string) and `state` (string) parameters and returns a synchronization receipt.

#### Scenario: Contract sync with valid contract_id
- **WHEN** Spoke AI calls `hub_sync_contract` with a valid contract_id and state
- **THEN** the client SHALL send a sync message to the Hub MCP Server
- **AND** SHALL return a receipt with `contract_id`, `synced_at`, and `hub_confirmed: true`

#### Scenario: Contract sync during Hub MCP Server outage triggers fallback
- **WHEN** Hub MCP Server is unreachable during `hub_sync_contract` call
- **THEN** the client SHALL invoke REST fallback per `mcp-fallback` specification
- **AND** SHALL log the fallback invocation to trace

### Requirement: Trace logging on every tool call

Every invocation of any MCP Client tool SHALL be logged to `.rddf/state/.mcp-trace.jsonl` as a JSONL entry containing `timestamp`, `tool_name`, `args`, `result` or `error`, and `transport` used.

#### Scenario: Trace entry written after successful call
- **WHEN** any MCP Client tool returns successfully
- **THEN** a JSONL line SHALL be appended to `.rddf/state/.mcp-trace.jsonl`
- **AND** the entry SHALL contain `tool_name`, `args`, `result`, `transport`, and ISO8601 `timestamp`

#### Scenario: Trace entry written after failed call
- **WHEN** any MCP Client tool returns an error
- **THEN** a JSONL line SHALL be appended with `error` field populated
- **AND** the entry SHALL indicate whether fallback was attempted

