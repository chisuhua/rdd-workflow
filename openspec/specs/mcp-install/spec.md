# mcp-install Specification

## Purpose
TBD - created by archiving change add-mcp-cross-repo-protocol. Update Purpose after archive.
## Requirements
### Requirement: install.sh --spoke-init subcommand

The `install.sh` script SHALL accept a `--spoke-init` flag that copies the `.cursorrules.cross-repo-hub` template to the target Spoke repository.

#### Scenario: Spoke init copies template to target repo
- **WHEN** user runs `bash install.sh --spoke-init /path/to/spoke`
- **THEN** the script SHALL copy `skills/templates/.cursorrules.cross-repo-hub` to `/path/to/spoke/.cursorrules`
- **AND** SHALL output `"已注入 12 条跨项目协同协议到 /path/to/spoke/.cursorrules"`

#### Scenario: Target directory is not a git repo
- **WHEN** `install.sh --spoke-init /path/to/non-git`
- **THEN** the script SHALL output `"警告: /path/to/non-git 不是 git 仓库，跳过 cursorrules 注入"`
- **AND** SHALL exit with code 0 (non-blocking)

### Requirement: .cursorrules.cross-repo-hub template content

The template file SHALL contain at least 12 protocol rules governing Spoke-Hub interaction, including issue reading conventions, status update rules, contract sync protocols, and error handling expectations.

#### Scenario: Template includes hub_read_issue protocol rule
- **WHEN** Spoke AI reads the injected `.cursorrules`
- **THEN** it SHALL contain a rule stating that before creating a new change proposal, the Spoke AI SHOULD call `hub_read_issue` to check existing Hub issues with the same title

#### Scenario: Template includes rate limit courtesy rule
- **WHEN** Spoke AI reads the injected `.cursorrules`
- **THEN** it SHALL contain a rule stating that before making parallel `hub_create_issue` calls, the Spoke AI SHOULD wait 1 second between calls to respect Hub rate limits

### Requirement: Prompt boundary between Spoke AI and Hub AI

The MCP Client interface SHALL clearly separate Spoke AI's tool-calling boundary from Hub AI's execution boundary. The Spoke AI SHALL only interact via MCP tools; it SHALL NOT directly call GitHub REST API for Hub operations.

#### Scenario: Spoke AI uses MCP tools only for Hub interactions
- **WHEN** Spoke AI needs to read a Hub issue
- **THEN** it SHALL call `hub_read_issue` MCP tool
- **AND** it SHALL NOT call `gh issue view` directly for Hub repo issues

### Requirement: Hub validation gate

Before the MCP Server is considered operational, a manual Hub validation gate SHALL be passed: an operator SHALL verify the MCP Server endpoint is reachable and returns a valid JSON-RPC response.

#### Scenario: Manual validation via MCP Server health check
- **WHEN** Hub operator runs `curl https://<hub-mcp-server>/health`
- **THEN** the response SHALL be `{"status": "ok", "protocol_version": "0.5"}`
- **AND** the validation result SHALL be logged to `.mcp-trace.jsonl`

#### Scenario: Validation failure blocks Spoke operations
- **WHEN** Hub MCP Server health check returns non-200 or invalid JSON
- **THEN** Spoke MCP Client SHALL output `"Hub MCP Server validation failed: <reason>"`
- **AND** SHALL NOT attempt MCP calls until validation passes

