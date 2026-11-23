# populate-code-verification Specification

## Purpose
TBD - created by archiving change extend-populate-roadmap-with-code-verification. Update Purpose after archive.
## Requirements
### Requirement: code-verify-flag

The `populate-roadmap-from-arch` command SHALL accept a `--code-verify` flag with three values: `off` (default, v1.0-compatible), `on` (enables verification, non-blocking), and `strict` (blocking on discrepancy).

#### Scenario: default behavior unchanged
- **WHEN** a user runs `populate-roadmap-from-arch --yes` (no `--code-verify` flag)
- **THEN** the system SHALL behave identically to v1.0 — no Step 1.5 verification, fragment body uses `*（已实施 v2.0.0+）*` markers, no supplementary JSON written
- **AND** the exit code SHALL be 0 on success

#### Scenario: explicit off
- **WHEN** a user runs `populate-roadmap-from-arch --yes --code-verify=off`
- **THEN** the system SHALL behave identically to the default (no verification)

#### Scenario: enable verification
- **WHEN** a user runs `populate-roadmap-from-arch --yes --code-verify=on`
- **THEN** the system SHALL execute Step 1.5 verification for each ADR
- **AND** write `.rddf/state/.populate-supplementary.json` with verification records
- **AND** fragment body SHALL use one of 4 verification-aware badges
- **AND** the exit code SHALL be 0 even if discrepancies exist

#### Scenario: strict mode blocks discrepancy
- **WHEN** a user runs `populate-roadmap-from-arch --yes --code-verify=strict`
- **THEN** the system SHALL execute Step 1.5 verification
- **AND** if any ADR has `has_discrepancy=true`, the system SHALL exit with code 2
- **AND** stderr SHALL list the discrepant ADR(s) by ID

### Requirement: adr-code-verification

The system SHALL verify each ADR's self-claimed implementation status against actual code by parsing the ADR's `## 决策` / `Decision` section for code symbols and checking their existence in the codebase.

#### Scenario: confirmed verification
- **WHEN** an ADR claims `已实施 v2.0.0+` and ≥80% of expected symbols are found in code
- **THEN** `verification_status` SHALL be `confirmed`
- **AND** `has_discrepancy` SHALL be `false`

#### Scenario: self-claim-only
- **WHEN** an ADR claims `已实施 v2.0.0+` but <80% of expected symbols are found in code
- **THEN** `verification_status` SHALL be `self-claim-only`
- **AND** `has_discrepancy` SHALL be `true`

#### Scenario: placeholder-as-claimed
- **WHEN** an ADR claims placeholder/未实施 status and no expected symbols are found in code
- **THEN** `verification_status` SHALL be `placeholder-as-claimed`
- **AND** `has_discrepancy` SHALL be `false`

#### Scenario: placeholder-but-exists (contradiction)
- **WHEN** an ADR claims placeholder/未实施 status but ≥1 expected symbol IS found in code
- **THEN** `verification_status` SHALL be `placeholder-but-exists`
- **AND** `has_discrepancy` SHALL be `true`

### Requirement: verification-data-source

The system SHALL prefer codebase-memory-mcp for symbol lookup (fast, indexed call graph) and fall back to grep when mcp is unavailable.

#### Scenario: mcp available
- **WHEN** codebase-memory-mcp is running and indexed
- **THEN** the system SHALL use `search_graph` / `get_code_snippet` for symbol lookup
- **AND** SHALL emit no warning

#### Scenario: mcp unavailable graceful degradation
- **WHEN** codebase-memory-mcp is not reachable
- **THEN** the system SHALL fall back to `grep -rn "<symbol>" --include='*.py' --include='*.sh'` over the project root
- **AND** SHALL emit a single warning noting fallback is in use
- **AND** SHALL continue verification without blocking

### Requirement: supplementary-output

The system SHALL persist verification results to `.rddf/state/.populate-supplementary.json` (gitignored view file) following the `populate_supplementary_schema.json` v1 schema.

#### Scenario: supplementary written
- **WHEN** `--code-verify=on|strict` completes verification
- **THEN** `.rddf/state/.populate-supplementary.json` SHALL exist
- **AND** SHALL contain one record per ADR with: `adr_id`, `self_claim_version`, `verification_status`, `code_symbols_found`, `code_symbols_expected`, `has_discrepancy`, `verified_at`

#### Scenario: dry-run skips write
- **WHEN** a user runs `populate-roadmap-from-arch --dry-run --code-verify=on`
- **THEN** the system SHALL print verification results to stdout
- **AND** SHALL NOT write `.populate-supplementary.json`

### Requirement: fragment-body-badges

The system SHALL render the `## 已实施能力` section of each roadmap fragment using 4 verification-aware badges when `--code-verify=on|strict` is in effect.

#### Scenario: confirmed badge
- **WHEN** verification_status is `confirmed`
- **THEN** the rendered line SHALL use `*（已实施 v2.0.0+ + 代码验证）*`

#### Scenario: self-claim-only badge
- **WHEN** verification_status is `self-claim-only`
- **THEN** the rendered line SHALL use `*（已实施 v2.0.0+ 仅自报）*`

#### Scenario: placeholder-but-exists badge
- **WHEN** verification_status is `placeholder-but-exists`
- **THEN** the rendered line SHALL use `*（占位 + 代码已现 ⚠️）*`

#### Scenario: placeholder-as-claimed badge
- **WHEN** verification_status is `placeholder-as-claimed`
- **THEN** the rendered line SHALL use `*（占位 + 代码未现）*`

### Requirement: v1-backward-compatibility

The system SHALL preserve v1.0 public API and CLI surface — no existing flag, function signature, or fragment frontmatter field SHALL be modified.

#### Scenario: no CLI regression
- **WHEN** a user runs `populate-roadmap-from-arch --phase phase-1 --dry-run --no-backup --yes`
- **THEN** the system SHALL accept all v1.0 flags unchanged
- **AND** fragment output SHALL match v1.0 (no new badges, no supplementary.json)

#### Scenario: v1 tests still pass
- **WHEN** the v1.0 test suite (`tests/unit/test_populate_lib.py` + `tests/integration/test_populate_roadmap_from_arch.bats`) runs against the modified `populate_lib.py`
- **THEN** all 12 pytest + 10 bats cases SHALL continue to pass without modification

