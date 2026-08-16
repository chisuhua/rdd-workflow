---
name: spoke-system-prompt-injection
description: Injects Hub-and-Spoke federation protocol into AI assistant tool configuration files (Cursor, Cline, Continue, GitHub Copilot, Claude Code). Provides deploy.sh for idempotent injection, backup, and uninstall.
license: MIT
compatibility: Requires bash, git
metadata:
  version: "1.0"
  author: sisyphus
  evolved-from: "spoke-system-prompt-injection v1.0 (initial)"
  user-invocable: true
---

# Spoke System Prompt Injection — Canonical Protocol

`protocol_version: 1.0`

This document defines the canonical protocol for injecting Hub-and-Spoke federation rules into AI assistant tool configuration files.

## Overview

The Spoke System Prompt Injection enables any AI assistant tool (Cursor, Cline, Continue, GitHub Copilot, Claude Code) to participate in the rdd-hub Hub-and-Spoke federation without requiring custom MCP server configuration. Protocol content is injected as a bounded block into tool-specific configuration files.

## Protocol Semantics

All injected blocks MUST contain the following four semantic components:

### 1. RFC Initiation

When the Spoke AI needs to escalate a decision to the Hub:

- Create an RFC Issue via `hub_create_issue` with category `RFC`
- Include `stakeholders` field listing all affected repos
- Wait ≥1 second before parallel RFC creation to respect rate limits

### 2. RFC Review

When the Hub provides RFC feedback:

- Read feedback via `hub_read_issue`
- Apply feedback before proceeding with implementation
- Never skip RFC review even for small changes

### 3. Sync

When the Hub pushes contract changes:

- Pull contract via `hub_sync_contract`
- Update local `openspec/specs/` with new contract content
- Fail fast on sync errors — never silently retry

### 4. Auto-Approval Prohibition

Explicitly forbid auto-approval behaviors:

- Never auto-approve RFCs without Hub confirmation
- Never suppress sync warnings
- Never bypass rate limit handling
- Never log raw tokens

## Injection Block Format

```html
<!-- RDD-HUB-PROTOCOL-START -->
[Tool-specific header comment]
[Protocol content]
<!-- RDD-HUB-PROTOCOL-END -->
```

The bounded block uses HTML comment markers to enable:
- Idempotent re-injection (detect existing block)
- Clean uninstall (remove bounded block)
- Backup before modification

## Supported Tools

| Tool | Config File | Header Comment |
|------|-------------|---------------|
| Cursor | `.cursorrules` | `# rdd-hub Cross-Repo Protocol Rules (Cursor)` |
| Cline | `.clinerules` | `# rdd-hub Cross-Repo Protocol Rules (Cline)` |
| Continue | `.continue/rules/cross-repo-hub.md` | `# rdd-hub Cross-Repo Protocol Rules (Continue)` |
| GitHub Copilot | `.github/copilot-instructions.md` | `# rdd-hub Cross-Repo Protocol Rules (GitHub Copilot)` |
| Claude Code | `CLAUDE.md` | `# rdd-hub Cross-Repo Protocol Rules (Claude Code)` |

## Usage

```bash
# Deploy to all tools
bash skills/spoke-system-prompt-injection/scripts/deploy.sh --tools all

# Deploy to specific tool
bash skills/spoke-system-prompt-injection/scripts/deploy.sh --tools cursor

# Check status
bash skills/spoke-system-prompt-injection/scripts/deploy.sh --status

# Uninstall (restore from backup)
bash skills/spoke-system-prompt-injection/scripts/deploy.sh --uninstall --tools all
```

## Security Notes

- Protocol block is read-only once injected
- Backup files are created with `.bak.YYYYMMDD` suffix before modification
- Uninstall restores from the most recent backup
