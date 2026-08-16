# add-spoke-system-prompt-injection Design

## Context

The Hub-and-Spoke federated collaboration protocol (`rdd-hub/docs/mcp-protocols.md`) relies on human documentation to guide Spoke AI environments (Claude Code, Cursor, Continue, Cline, GitHub Copilot). However, AI assistants do not read documentation by default—they operate based on their system prompts and configuration files. Without injection of protocol awareness into these configuration files, Spoke AIs cannot:
- Know that a Hub repository exists
- Understand how to initiate RFCs via GitHub MCP
- Know when to use `--hub-issue` to unblock design-done
- Recognize that auto-approving cross-repo proposals is prohibited

This design addresses the injection layer: how to reliably, idempotently, and reversibly embed Hub protocol awareness into all five mainstream AI coding tools.

## Goals / Non-Goals

**Goals:**
- Inject Hub protocol awareness into all five AI tool configuration formats (Cursor, Cline, Continue, Copilot, Claude Code)
- Ensure deployment is idempotent (re-running produces identical state, no duplicate content)
- Provide a one-command uninstall that rolls back to pre-injection state with backup
- Integrate with `install.sh --spoke-init` for seamless project onboarding
- Cover RFC initiation, RFC review, contract sync, and the auto-approval prohibition
- Version all templates against a single `protocol_version` variable

**Non-Goals:**
- This spec does NOT define the MCP protocol implementation itself (that belongs to `add-mcp-cross-repo-protocol`)
- This spec does NOT modify the Hub repository itself (that belongs to `add-rdd-hub-bootstrap`)
- This spec does NOT force adoption—teams choose which tools to inject
- This spec does NOT provide automatic cross-repo approval—explicit prohibition is the design

## Decisions

### 1. Decision: Marker-Based Idempotent Injection

**Decision:** Use HTML comment markers (`<!-- RDD-HUB-PROTOCOL-START -->` / `<!-- RDD-HUB-PROTOCOL-END -->`) to bound injected content, enabling both duplicate detection and clean removal.

**Rationale:**
- Markers are valid in all five target file formats (Markdown, YAML frontmatter, plain text configs)
- Detection is a simple `grep` check—fast and portable
- Bounded blocks enable precise uninstall without affecting surrounding content
- Markers serve as self-documenting proof that the file was intentionally modified

**Alternatives considered:**
- Hash-based content comparison: Rejected because it makes incremental edits fragile
- Version headers only: Rejected because it doesn't provide clean removal boundaries

### 2. Decision: Per-Tool Template Files in `templates/` Subdirectory

**Decision:** Store the five AI tool templates as separate files in `skills/spoke-system-prompt-injection/templates/` rather than generating them programmatically.

**Rationale:**
- Each AI tool has distinct syntax (Cursor uses `.cursorrules`, Cline uses `.clinerules`, etc.)
- Separate files allow tool-specific formatting without conditional logic
- Templates can be updated independently when a tool's format changes
- The `inject.md` file serves as the canonical content source that all five templates embed

**Alternatives considered:**
- Single template with tool-specific post-processing: Rejected—too much conditional logic in deploy.sh
- Generation from a schema: Rejected—over-engineering for five static files

### 3. Decision: Backup Before Modification with Datestamp

**Decision:** Before injecting into any file, create a backup with format `{filename}.bak.YYYYMMDD`.

**Rationale:**
- Datestamp enables multiple deployment cycles without overwriting backups
- Timestamp is human-readable and sortable
- Backup is created even if injection later fails—defensive
- Restoration is deterministic: copy backup over current file, then delete backup

**Alternatives considered:**
- Single `.bak` without date: Rejected—repeated deploy cycles would overwrite the only backup
- Git-based rollback: Rejected—deploy.sh should not depend on git history being clean

### 4. Decision: `deploy.sh` as Single Entry Point

**Decision:** All deployment, uninstall, and status operations flow through a single `deploy.sh` script with `--tools`, `--uninstall`, and `--status` flags.

**Rationale:**
- Single entry point simplifies the install integration (`install.sh --spoke-init` calls one script)
- Tool detection and injection logic are centralized
- idempotency checks live in one place
- Flags are composable: `--tools cursor,claude --uninstall`

**Alternatives considered:**
- Separate `inject.sh` and `uninstall.sh`: Rejected—two scripts to integrate with install.sh
- Python-based deploy: Rejected—bash is more portable and has no runtime dependency

### 5. Decision: `install.sh --spoke-init` Integration Point

**Decision:** Add `--spoke-init` as a flag to the existing `install.sh` that invokes `deploy.sh` with appropriate defaults.

**Rationale:**
- Leverages existing install.sh infrastructure rather than creating parallel onboarding
- `--spoke-init` is opt-in—existing installs are unaffected
- Teams can skip injection by not passing `--spoke-init`

**Alternatives considered:**
- Separate `spoke-init.sh`: Rejected—adds another entry point to maintain
- Auto-detection on install: Rejected—auto-injection without explicit consent is surprising

### 6. Decision: Protocol Version Centralized in `inject.md`

**Decision:** All templates reference `protocol_version` defined in `inject.md` rather than hardcoding version strings.

**Rationale:**
- Single source of truth for version—update in one place, all templates reflect it
- Enables future version-comparison logic in deploy.sh for upgrade/downgrade decisions
- Templates embed the version at deploy time (static snapshot), not runtime

**Alternatives considered:**
- Version in each template: Rejected—updating requires editing five files
- Runtime version lookup: Rejected—deploy.sh should be simple; templates should be static

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| AI tool format changes (e.g., Cursor renames `.cursorrules`) | Templates are separate files; only the affected template needs update |
| User edits injected content manually | Markers provide boundaries, but manual edits inside the block may persist after uninstall |
| Install script proliferation | `--spoke-init` keeps integration in one install.sh rather than adding more scripts |
| Tool detection false positives | `find` with explicit filename patterns reduces false matches |
| Backup accumulation | Backup files are created per-deploy; no automatic cleanup—user must manage manually |
