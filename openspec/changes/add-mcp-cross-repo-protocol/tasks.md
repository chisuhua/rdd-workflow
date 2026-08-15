# add-mcp-cross-repo-protocol Tasks

## Implementation Tasks

### MCP Client Implementation

- [ ] Create `skills/cross-repo-protocol/` directory structure
  - Create `skills/cross-repo-protocol/__init__.py` with package exports
  - Verify directory is added to Python path via existing `_lib` mechanism

- [ ] Create `skills/cross-repo-protocol/mcp_client.py` — MCP Client library
  - Implement `MCPClient` class with `__init__(transport, server_path, token)`
  - Implement `call_tool(tool_name, args) -> dict` with Stdio transport default
  - Implement `_fallback_to_rest(tool_name, args) -> dict` for REST fallback
  - Implement `_log_trace(entry)` appending JSONL to `.rddf/state/.mcp-trace.jsonl`
  - Implement `transport_stdio()` using `mcp` Python package SDK
  - Implement `transport_http()` using `mcp` Python package SDK with `MCP_SERVER_URL`
  - Add 5s connection timeout on MCP Server connect
  - Catch `ConnectionRefusedError`, `gaierror`, `ConnectTimeout` for fallback trigger
  - Raise `MCPConfigurationError` when `GITHUB_TOKEN` is missing

- [ ] Implement `hub_read_issue` tool in `MCPClient`
  - Map to `GET /repos/{owner}/{repo}/issues/{issue_number}`
  - Return normalized JSON with fields: `number`, `title`, `body`, `state`, `status`, `stakeholders`, `contract_impact`, `labels`

- [ ] Implement `hub_create_issue` tool in `MCPClient`
  - Map to `POST /repos/{owner}/{repo}/issues`
  - Accept `title`, `body`, `stakeholders` (array), `contract_impact` (string)
  - Return created Issue with `number`, `title`, `body`, `state`, `created_at`, `url`

- [ ] Implement `hub_update_status` tool in `MCPClient`
  - Accept `issue_number`, `status`, optional `comment`
  - Update Issue `Status` custom field via PATCH
  - If `comment` provided, also POST comment

- [ ] Implement `hub_sync_contract` tool in `MCPClient`
  - Accept `contract_id` (string) and `state` (string)
  - Send sync message via MCP Server
  - Return receipt with `contract_id`, `synced_at`, `hub_confirmed`

### Trace Implementation

- [ ] Create `.rddf/state/.mcp-trace.jsonl` trace logging
  - Implement `MCPTraceLogger` class in `skills/cross-repo-protocol/trace.py`
  - Support `append(entry)` adding JSONL line
  - Auto-create parent directory `.rddf/state/` if missing
  - Implement `redact(obj)` to mask `token`, `secret`, `password` fields
  - Compute `duration_ms` via `time.time()` before/after call

- [ ] Integrate trace logging into `MCPClient.call_tool()`
  - Log every call (success or error) to `.rddf/state/.mcp-trace.jsonl`
  - Set `fallback_attempted: true` when REST fallback triggered

### REST Fallback Implementation

- [ ] Implement `MCPClient._fallback_to_rest()` method
  - Map each tool to equivalent GitHub REST API call
  - Use `requests` library with same `GITHUB_TOKEN`
  - Respect GitHub rate limits with exponential backoff (max 3 retries)
  - Return same JSON Schema as MCP response
  - Print warning to stderr unless `MCPSuppressFallbackWarning=true`

### Auth and Transport Implementation

- [ ] Implement `GITHUB_TOKEN` environment variable reading
  - Read token in `MCPClient.__init__()`
  - Pass to MCP Server via SDK auth mechanism
  - Pass to REST fallback via `requests` headers

- [ ] Implement `MCP_TRANSPORT` environment variable for dual transport
  - Default to `stdio`
  - Support `http` for Streamable HTTP transport
  - Read `MCP_SERVER_URL` when transport is `http`

### Rate Limit Handling

- [ ] Implement rate limit detection and retry
  - Detect 403 response with `X-RateLimit-Remaining: 0`
  - Parse `X-RateLimit-Reset` timestamp
  - Wait until reset with exponential backoff
  - Return `error: "rate_limit_exceeded"` after 3 retries

### Install Integration

- [ ] Modify `install.sh` to add `--spoke-init` subcommand
  - Parse `--spoke-init` flag with target directory argument
  - Verify target is git repository (warn and skip if not)
  - Copy `skills/templates/.cursorrules.cross-repo-hub` to `<target>/.cursorrules`
  - Output confirmation message

- [ ] Create `skills/templates/.cursorrules.cross-repo-hub` template file
  - Include 12 protocol rules for Spoke AI behavior
  - Rule 1: Before creating RFC, call `hub_read_issue` to check duplicates
  - Rule 2: Wait ≥1s between parallel `hub_create_issue` calls
  - Rule 3: Every `hub_update_status` must include reason in `comment`
  - Rule 4: `hub_sync_contract` failure must notify human operator
  - Rule 5: MCP Server unreachable triggers REST fallback with warning
  - Rule 6-12: Additional protocol rules covering token handling, error propagation, retry limits, etc.

### Documentation

- [ ] Create `skills/cross-repo-protocol/SKILL.md` — MCP protocol human-readable documentation
  - Document all 4 tools with parameter types and return schemas
  - Document transport selection (`MCP_TRANSPORT`)
  - Document auth requirements (`GITHUB_TOKEN`)
  - Document trace file location and format
  - Document REST fallback behavior

## Test Tasks

- [ ] Create unit tests for `mcp_client.py`
  - Test `hub_read_issue` returns normalized Issue
  - Test `hub_create_issue` with missing title returns validation error
  - Test `hub_update_status` without comment
  - Test `hub_update_status` with comment returns comment_id
  - Test `hub_sync_contract` returns sync receipt
  - Test `GITHUB_TOKEN` missing raises `MCPConfigurationError`
  - Test trace entry written on success
  - Test trace entry written on error

- [ ] Create unit tests for REST fallback
  - Test fallback triggered on connection refused
  - Test fallback preserves return schema
  - Test fallback uses same `GITHUB_TOKEN`
  - Test fallback rate limit handling
  - Test fallback failure propagates REST error

- [ ] Create unit tests for trace logger
  - Test JSONL format compliance
  - Test sensitive data redaction
  - Test auto-create directory

- [ ] Create integration tests for `install.sh --spoke-init`
  - Test template copied to valid git repo
  - Test warning printed for non-git target
  - Test idempotent (second run overwrites)

- [ ] Create bats tests for CLI integration
  - Test `mcp_client` module imports correctly
  - Test trace file created on first call

## Validation Tasks

- [ ] Manual Hub MCP Server validation gate
  - Operator runs health check: `curl https://<hub-mcp-server>/health`
  - Verify response: `{"status": "ok", "protocol_version": "0.5"}`
  - Log validation result to `.mcp-trace.jsonl`

- [ ] Run `openspec validate add-mcp-cross-repo-protocol` — must pass all gates
