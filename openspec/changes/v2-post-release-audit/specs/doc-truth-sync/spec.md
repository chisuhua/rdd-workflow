## ADDED Requirements

### Requirement: adr-readme-status-truth
The system SHALL update `docs/adr/README.md` to reflect actual implementation status of each v2.0 ADR, replacing the blanket "not implemented" claim with per-ADR audit results.

#### Scenario: ADR README shows per-ADR status
- **WHEN** a user opens `docs/adr/README.md`
- **THEN** each v2.0 ADR (0002-0012) SHALL show one of: ✅ 已实施, ⚠️ 部分实施, ❌ 未实施
- **AND** the blanket "v2.0 ADRs are design drafts, not implemented" header SHALL be removed

### Requirement: v2-adr-summary-accurate
The system SHALL update `docs/v2-adr-summary.md` to include all 12 ADRs (0001-0012), fix the ADR count from 9 to 12, remove the false "not implemented" claim, and add missing ADR-0003/0011/0012 sections.

#### Scenario: v2-adr-summary shows all ADRs
- **WHEN** a user reads `docs/v2-adr-summary.md`
- **THEN** the ADR count SHALL read "12" not "9"
- **AND** ADR-0003 (three-phase architecture), ADR-0011, ADR-0012 SHALL appear in the body
- **AND** the "未实施" DRAFT banner SHALL be replaced with implementation status

### Requirement: migration-guide-no-fictional-cli
The system SHALL remove or replace all references to the non-existent `spec-workflow migrate/sync/report` CLI commands in `docs/migration/v1-to-v2.md`, replacing them with equivalent manual steps or "planned" markers.

#### Scenario: migration guide no longer references fictional CLI
- **WHEN** a user reads `docs/migration/v1-to-v2.md`
- **THEN** SHALL be zero references to `spec-workflow migrate`, `spec-workflow sync`, or `spec-workflow report`
- **AND** any previously fictional CLI commands SHALL be replaced with actionable manual steps or clear "planned for v2.1" markers

#### Scenario: dangling file paths fixed
- **WHEN** a user reads `docs/migration/v1-to-v2.md`
- **THEN** `skills/loop.md` SHALL read `skills/loop_engine.py`
- **AND** `skills/_lib/session_v20.py` SHALL read `skills/_lib/session.py`

### Requirement: install-usage-readme-metadata-sync
The system SHALL synchronize `skills/INSTALL.md`, `USAGE.md`, and `README.md` with `package.json` (v2.0.0-beta, 12 skills), including version numbers, skill counts, and directory structure listings.

#### Scenario: INSTALL.md lists all 12 skills
- **WHEN** a user installs via `skill_use("INSTALL")`
- **THEN** the skill list in the description SHALL include all 12 skills (not 10)
- **AND** the package.json template SHALL derive version from the actual package.json

#### Scenario: USAGE.md shows correct version
- **WHEN** a user reads `USAGE.md`
- **THEN** the version header SHALL be v2.0.0-beta (not v1.1)
- **AND** the .zcf state files table SHALL list only existing files
- **AND** there SHALL be no duplicate section headers

#### Scenario: README.md directory structure is complete
- **WHEN** a user reads `README.md`
- **THEN** the directory tree SHALL include guide-arch.md, guide-plan.md, loop_engine.py, and the _lib/ subdirectory

### Requirement: v2-api-ref-path-corrections
The system SHALL fix incorrect file path references in `docs/v2-api-reference.md` and `docs/v2-loop-engine.md`.

#### Scenario: API reference uses correct paths
- **WHEN** a user reads `docs/v2-api-reference.md`
- **THEN** all `session_v20.py` references SHALL read `session.py`
- **WHEN** a user reads `docs/v2-loop-engine.md`
- **THEN** all `loop-engine.py` references SHALL read `loop_engine.py`

### Requirement: orphaned-specs-promotion
The system SHALL promote 4 spec directories from archive to `openspec/specs/`: release-management, migration-docs, test-suite, three-phase-skills.

#### Scenario: specs directory contains 15 directories
- **WHEN** a user runs `ls openspec/specs/`
- **THEN** the listing SHALL include 15 directories (up from 11)
- **AND** the new directories SHALL be: release-management, migration-docs, test-suite, three-phase-skills