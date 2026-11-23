# adr-index Specification

## Purpose
TBD - created by archiving change adr-index-auto-sync. Update Purpose after archive.
## Requirements
### Requirement: ADR Index README table auto-generated from disk

The system SHALL automatically generate the `## ADR 列表` table in `docs/adr/README.md` by scanning all `docs/adr/ADR-*.md` files on disk and extracting their `> **状态**:`, `> **日期**:`, and `> **决策者**:` metadata blocks.

The generated table SHALL be placed between `<!-- ADR_INDEX_START -->` and `<!-- ADR_INDEX_END -->` markers.

#### Scenario: Generator regenerates table matching disk

- **WHEN** developer runs `python3 _lib/adr_index_generator.py`
- **THEN** the markdown table header `| ADR | 标题 | 状态 | 日期 |` appears in stdout
- **AND** exactly 34 rows of `| [ADR-XXXX](...)` appear (excluding ADR-0000 template)

#### Scenario: Generator skips template files

- **WHEN** the scanner encounters `docs/adr/ADR-0000-template.md`
- **THEN** the file is skipped from the rendered table
- **AND** no row containing `ADR-0000` appears in the output

### Requirement: CI guard validates README table matches disk

A bats integration test SHALL verify that the table inside the ADR_INDEX markers in `docs/adr/README.md` contains exactly the same number of ADR rows as the number of `ADR-*.md` files on disk (excluding template).

#### Scenario: Bats test passes when table is consistent

- **WHEN** developer runs `bats tests/integration/test_adr_index.bats`
- **AND** the README table row count equals the disk file count (34)
- **THEN** all 4 test cases pass

#### Scenario: Bats test fails when table drifts

- **WHEN** developer adds `ADR-0035` to disk but forgets to regenerate README
- **THEN** test `adr_index: docs/adr/README.md status table is consistent with disk` fails
- **AND** the developer is prompted to regenerate the table

