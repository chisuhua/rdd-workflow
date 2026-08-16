# ai-tool-templates Specification

## Purpose
TBD - created by archiving change add-spoke-system-prompt-injection. Update Purpose after archive.
## Requirements
### Requirement: five-ai-tool-templates-covered

The system SHALL provide Hub protocol injection templates for all five mainstream AI coding tools.

#### Scenario: Cursor template
- **WHEN** `.cursorrules.cross-repo-hub` is deployed to a Spoke repository
- **THEN** it SHALL contain the full Hub protocol content including RFC initiation, review, sync, and prohibition on auto-approval

#### Scenario: Cline template
- **WHEN** `.clinerules.cross-repo-hub` is deployed to a Spoke repository
- **THEN** it SHALL contain equivalent Hub protocol content adapted for Cline's configuration format

#### Scenario: Continue template
- **WHEN** `.continue/rules/cross-repo-hub.md` is deployed to a Spoke repository
- **THEN** it SHALL contain equivalent Hub protocol content in Continue's rule format

#### Scenario: GitHub Copilot template
- **WHEN** `.github/copilot-instructions.md` is deployed to a Spoke repository
- **THEN** it SHALL contain equivalent Hub protocol content for Copilot's instruction format

#### Scenario: Claude Code template
- **WHEN** `CLAUDE.md` is augmented with Hub protocol content
- **THEN** it SHALL contain equivalent Hub protocol content in Claude Code's convention

### Requirement: template-content-equivalence

All five templates SHALL convey identical protocol semantics despite format differences.

#### Scenario: RFC initiation workflow
- **WHEN** any of the five templates is read
- **THEN** each SHALL describe the RFC initiation workflow referencing `rdd-hub` repository and `GitHub MCP`

#### Scenario: Cross-repo approval prohibition
- **WHEN** any of the five templates is read
- **THEN** each SHALL explicitly prohibit AI from automatically approving cross-repo proposals

#### Scenario: Design-done挂起 awareness
- **WHEN** any of the five templates is read
- **THEN** each SHALL describe how to monitor Hub Issue status for design-done unblocking

### Requirement: idempotent-injection-marker

Each template deployment SHALL use a marker to prevent duplicate injection.

#### Scenario: Marker detection prevents double-injection
- **WHEN** `deploy.sh` runs on a repository that already has the Hub protocol injected
- **THEN** it SHALL detect the marker `<!-- RDD-HUB-PROTOCOL-START -->`
- **AND** skip re-injection for that file

#### Scenario: Marker spans protocol block
- **WHEN** the marker is present
- **THEN** the protocol content is bounded by `<!-- RDD-HUB-PROTOCOL-START -->` and `<!-- RDD-HUB-PROTOCOL-END -->`

