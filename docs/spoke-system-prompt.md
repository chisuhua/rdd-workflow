# Spoke System Prompt Injection Guide

> Enable AI assistant tools (Cursor, Cline, Continue, GitHub Copilot, Claude Code) to participate in the rdd-hub Hub-and-Spoke federation.

## Overview

The Spoke System Prompt Injection injects Hub-and-Spoke federation protocol rules into AI assistant tool configuration files. This enables any AI tool to participate in the federation without requiring custom MCP server configuration.

## Quick Start

```bash
# Deploy protocol to all supported AI tools
bash skills/spoke-system-prompt-injection/scripts/deploy.sh --tools all

# Check injection status
bash skills/spoke-system-prompt-injection/scripts/deploy.sh --status

# Uninstall (restore from backup)
bash skills/spoke-system-prompt-injection/scripts/deploy.sh --uninstall --tools all
```

## Supported Tools

| Tool | Config File | Deploy Command |
|------|-------------|----------------|
| Cursor | `.cursorrules` | `--tools cursor` |
| Cline | `.clinerules` | `--tools cline` |
| Continue | `.continue/rules/cross-repo-hub.md` | `--tools continue` |
| GitHub Copilot | `.github/copilot-instructions.md` | `--tools copilot` |
| Claude Code | `CLAUDE.md` | `--tools claude` |

Deploy to multiple tools:
```bash
bash skills/spoke-system-prompt-injection/scripts/deploy.sh --tools cursor,cline
```

## Protocol Rules

### RFC Initiation
Before creating RFC Issues:
1. Check for duplicates via `hub_read_issue`
2. Include `stakeholders` field in every RFC body
3. Wait ≥1 second between parallel RFC creation (rate limit: 5000 req/hour)

### RFC Review
- Apply Hub feedback before proceeding with implementation
- Never skip RFC review even for small changes

### Sync
- Pull contract changes via `hub_sync_contract`
- Fail fast on sync errors — never silently retry

### Auto-Approval Prohibition
- Never auto-approve RFCs without Hub confirmation
- Never suppress sync warnings
- Never bypass rate limit handling
- Never log raw tokens

## How It Works

1. **Detection**: The deploy script checks if the target directory is a git repository
2. **Idempotency Check**: Looks for existing `<!-- RDD-HUB-PROTOCOL-START -->` marker
3. **Backup**: Creates `{filename}.bak.YYYYMMDD` backup before modification
4. **Injection**: Appends bounded protocol block to tool config file
5. **Status**: Reports success/failure for each tool

## Uninstallation

```bash
# Uninstall from all tools (restores from backup)
bash skills/spoke-system-prompt-injection/scripts/deploy.sh --uninstall --tools all

# Uninstall from specific tool
bash skills/spoke-system-prompt-injection/scripts/deploy.sh --uninstall --tools cursor
```

## Integration with install.sh

The `install.sh --spoke-init` command invokes deploy.sh:

```bash
# Install .cursorrules to current project
bash install.sh --spoke-init

# Install specific tools
bash install.sh --spoke-init --tools cursor,cline
```

## Security

- Protocol block is read-only once injected
- Backup files preserve original content
- Uninstall restores from the most recent backup
- No network calls during injection
