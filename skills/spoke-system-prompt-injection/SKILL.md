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

# Spoke System Prompt Injection

Injects Hub-and-Spoke federation protocol into AI assistant tool configuration files.

## Overview

This skill enables any AI assistant tool (Cursor, Cline, Continue, GitHub Copilot, Claude Code) to participate in the rdd-hub Hub-and-Spoke federation. Protocol content is injected as a bounded block into tool-specific configuration files.

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

## Tool Configuration Files

| Tool | Config File |
|------|-------------|
| Cursor | `.cursorrules` |
| Cline | `.clinerules` |
| Continue | `.continue/rules/cross-repo-hub.md` |
| GitHub Copilot | `.github/copilot-instructions.md` |
| Claude Code | `CLAUDE.md` |

## Protocol Semantics

### RFC Initiation
Before creating RFC Issues, check for duplicates via `hub_read_issue`. Include `stakeholders` field in every RFC body. Wait ≥1 second between parallel RFC creation.

### RFC Review
Apply Hub feedback before proceeding with implementation. Never skip RFC review.

### Sync
Pull contract changes via `hub_sync_contract`. Fail fast on sync errors.

### Auto-Approval Prohibition
- Never auto-approve RFCs without Hub confirmation
- Never suppress sync warnings
- Never bypass rate limit handling

## Idempotency

The injection is idempotent — running twice produces identical output (no duplicate injection). The bounded block uses HTML comment markers:

```
<!-- RDD-HUB-PROTOCOL-START -->
...
<!-- RDD-HUB-PROTOCOL-END -->
```

## Backup

Backup files are created with `{filename}.bak.YYYYMMDD` suffix before modification. Uninstall restores from the most recent backup.

## Environment Variables

- `RDDF_SPOKE_TARGET_DIR` — Target directory for injection (default: cwd)
