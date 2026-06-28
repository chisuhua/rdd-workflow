# roadmap-planning Specification

## Purpose
TBD - created by archiving change v3-roadmap. Update Purpose after archive.
## Requirements
### Requirement: future-adr-evaluation
The system SHALL evaluate each of the 4 unimplemented ADRs (ADR-0009~0012) for implementation effort, business value, and dependencies, producing a decision table with target release assignment.

#### Scenario: ADR evaluation complete
- **WHEN** all 4 ADRs are evaluated
- **THEN** each ADR SHALL have: effort estimate (S/M/L/XL), target release (v2.1/v3.0), and dependency list
- **AND** the decisions SHALL be recorded in `docs/adr/README.md`

### Requirement: placeholder-change-creation
The system SHALL create placeholder openspec changes for each ADR that receives a target release assignment, with at minimum `.openspec.yaml` and `proposal.md`.

#### Scenario: placeholder changes exist
- **WHEN** a user runs `ls openspec/changes/`
- **THEN** the listing SHALL include change directories for each approved future ADR

### Requirement: roadmap-update
The system SHALL update `roadmap.md` from its current generic "Phase 1: User-defined" structure to concrete phase definitions with target releases, effort estimates, and cross-ADR dependencies.

#### Scenario: roadmap reflects v3.0 plan
- **WHEN** a user reads `roadmap.md`
- **THEN** the document SHALL contain sections for v2.0 (completed), v2.1 (planned), and v3.0 (forward-looking)
- **AND** each phase SHALL reference its corresponding openspec change

