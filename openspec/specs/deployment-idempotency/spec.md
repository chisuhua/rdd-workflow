# deployment-idempotency Specification

## Purpose
TBD - created by archiving change add-spoke-system-prompt-injection. Update Purpose after archive.
## Requirements
### Requirement: deploy-tool-detection

The deploy.sh script SHALL detect which AI tools are present in the target repository.

#### Scenario: Find Cursor config
- **WHEN** `deploy.sh --tools cursor` runs in a repository containing `.cursorrules`
- **THEN** it SHALL identify `.cursorrules` as the Cursor configuration file

#### Scenario: Skip missing tool configs
- **WHEN** `deploy.sh --tools claude,cursor` runs in a repository missing `.cursorrules`
- **THEN** it SHALL skip Cursor and only attempt Claude injection
- **AND** report "Cursor config not found, skipping"

#### Scenario: Detect all five tools
- **WHEN** `deploy.sh --tools all` runs
- **THEN** it SHALL search for `.cursorrules`, `.clinerules`, `.continue/rules/cross-repo-hub.md`, `.github/copilot-instructions.md`, and `CLAUDE.md`

### Requirement: idempotent-deployment

Repeated deployments of the same tool SHALL NOT produce duplicate protocol content.

#### Scenario: Skip already-injected files
- **WHEN** `deploy.sh --tools cursor` runs on a file already containing `<!-- RDD-HUB-PROTOCOL-START -->`
- **THEN** it SHALL output "Already injected, skipping"
- **AND** not modify the file

#### Scenario: First injection succeeds
- **WHEN** `deploy.sh --tools cursor` runs on a clean `.cursorrules`
- **THEN** it SHALL append the protocol content bounded by markers
- **AND** output "Injected successfully"

### Requirement: backup-before-modification

The deploy.sh script SHALL create a timestamped backup before modifying any configuration file.

#### Scenario: Backup created with timestamp
- **WHEN** `deploy.sh --tools cursor` prepares to modify `.cursorrules`
- **THEN** it SHALL create `.cursorrules.bak.YYYYMMDD` before any modification
- **WHERE** YYYYMMDD is the current date

#### Scenario: Backup preserves original content
- **WHEN** a backup is created
- **THEN** the backup file SHALL contain the exact original content
- **AND** the modified file SHALL contain the original + injected protocol

### Requirement: uninstall-rollback

The `--uninstall` flag SHALL remove injected protocol content and restore from backup.

#### Scenario: Uninstall removes protocol block
- **WHEN** `deploy.sh --uninstall --tools cursor` runs
- **THEN** it SHALL remove the content between `<!-- RDD-HUB-PROTOCOL-START -->` and `<!-- RDD-HUB-PROTOCOL-END -->`
- **AND** restore the file to its pre-injection state

#### Scenario: Uninstall restores from backup
- **WHEN** `deploy.sh --uninstall --tools cursor` runs
- **THEN** if a backup exists, it SHALL restore from the backup
- **AND** delete the backup file after successful restoration

#### Scenario: Uninstall without backup is clean
- **WHEN** `deploy.sh --uninstall --tools cursor` runs on a file with no backup
- **THEN** it SHALL still remove the protocol block if present
- **AND** not fail

### Requirement: multi-tool-deployment

The deploy.sh script SHALL support deploying to multiple tools in a single invocation.

#### Scenario: Comma-separated tool list
- **WHEN** `deploy.sh --tools cursor,claude,cline` runs
- **THEN** it SHALL attempt injection for all three tools sequentially
- **AND** report per-tool status

#### Scenario: Partial failure handling
- **WHEN** one tool fails (e.g., file not found)
- **THEN** deploy.sh SHALL continue to the next tool
- **AND** report which tools succeeded and which failed
- **AND** exit with non-zero status if any failed

