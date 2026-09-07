# remove-ac-verifier-completely Specification

## Purpose
TBD - created by archiving change remove-ac-verifier-completely. Update Purpose after archive.
## Requirements
### Requirement: ac-verifier skill deletion
The `ac-verifier` skill and all its implementation files MUST be removed from `skills/ac-verifier/`.

#### Scenario: skill directory removed
- **WHEN** the repository is checked out after this change
- **THEN** `skills/ac-verifier/` MUST NOT exist
- **AND** `git ls-files skills/ac-verifier/` MUST be empty
- **AND** `git grep "from skills.ac_verifier"` MUST NOT return any source file

### Requirement: ac-verify CLI friendly error
The `rddf ac-verify` command MUST exit 4 with a clear migration hint to `rddf rdd-verify`.

#### Scenario: user invokes `rddf ac-verify --help`
- **WHEN** the user runs `rddf ac-verify --help` or `rddf ac-verify` (no subcommand)
- **THEN** the exit code MUST be 4
- **AND** the stderr output MUST contain "removed per ADR-0045"
- **AND** the stderr output MUST contain "rddf rdd-verify"

#### Scenario: user invokes `rddf ac-verify <subcommand>`
- **WHEN** the user runs any subcommand under `rddf ac-verify`
- **THEN** the exit code MUST be 4
- **AND** the same migration hint MUST be printed

### Requirement: ac-verify CLI route removal
The `_lib/cli/__init__.py` MUST NOT register `ac-verify` as a working CLI subcommand.

#### Scenario: `rddf --help` does not list ac-verify as active
- **WHEN** the user runs `rddf --help`
- **THEN** the help output MUST NOT list `ac-verify` as an available subcommand (it may appear in a "removed" section, OR not appear at all)

#### Scenario: route table omits ac-verify
- **WHEN** `_lib/cli/__init__.py` is read
- **THEN** the routes dict MUST NOT contain `"ac-verify"` key

### Requirement: _default_runner alias removal
The `_lib/cli/rdd_verify_cmd.py` MUST NOT define `_default_runner = _stage_context_runner` alias.

#### Scenario: alias removed from rdd_verify_cmd.py
- **WHEN** `_lib/cli/rdd_verify_cmd.py` is read
- **THEN** it MUST NOT contain the symbol `_default_runner` (only `_stage_context_runner` and `_default_run`)

#### Scenario: no caller depends on _default_runner
- **WHEN** the entire repository is grep'd
- **THEN** `_default_runner` MUST NOT appear in `_lib/`, `skills/`, `tests/`, or `install.sh` (excluding `openspec/changes/archive/`)

### Requirement: ac-verifier test file removal
Five ac-verifier-specific test files MUST be removed. Two archive-gate tests that happen to share the `ac_verifier` prefix in their filenames MUST be preserved (they test `rdd-verifier` cache).

#### Scenario: deleted unit tests
- **WHEN** the test files are listed
- **THEN** `tests/unit/test_ac_verifier.py` MUST NOT exist
- **AND** `tests/unit/test_ac_verifier_providers.py` MUST NOT exist

#### Scenario: deleted integration tests
- **WHEN** the integration test files are listed
- **THEN** `tests/integration/test_ac_verifier_e2e.bats` MUST NOT exist
- **AND** `tests/integration/test_ac_verifier_http_live.bats` MUST NOT exist
- **AND** `tests/integration/test_ac_verifier_skill.bats` MUST NOT exist

#### Scenario: preserved archive-gate tests
- **WHEN** the archive-gate test files are listed
- **THEN** `tests/integration/test_ac_verifier_archive_gate.bats` MUST still exist (with internal references rewritten to `rdd-verifier`)
- **AND** `tests/integration/test_rdd_verifier_archive_compat.bats` MUST still exist
- **AND** `tests/unit/test_ac_verdict_cache_schema.py` MUST still exist (tests rdd-verifier cache schema, not ac-verifier skill)

### Requirement: top-level docs cleanup
Top-level documentation MUST NOT reference ac-verifier as an active skill.

#### Scenario: AGENTS.md has no ac-verifier reference
- **WHEN** `AGENTS.md` is read
- **THEN** it MUST NOT mention `ac-verifier` (excluding the removal status line in archived ADR pointers)

#### Scenario: README.md has no ac-verifier reference
- **WHEN** `README.md` is read
- **THEN** it MUST NOT list `ac-verifier` in the 目录结构 block
- **AND** the sub-skill count MUST be 26 (was 27)

#### Scenario: install.sh has no ac-verifier reference
- **WHEN** `install.sh` is read
- **THEN** the symlink loop MUST NOT include `ac-verifier`

### Requirement: ADR historical reference
The ADR-0045 (and related ADR-0034, ADR-0035) MUST be preserved as historical record with a removal status note appended.

#### Scenario: ADR-0045 carries removal note
- **WHEN** `docs/adr/ADR-0045-inline-ac-verifier-into-rdd-verifier.md` is read
- **THEN** it MUST contain a status line: "Status: Removed via `remove-ac-verifier-completely` (this minor release)"
- **AND** the original ADR body MUST NOT be deleted

#### Scenario: ADR-0034 carries note
- **WHEN** `docs/adr/ADR-0034-rdd-verifier-verify-phase-architecture.md` is read
- **THEN** it MUST contain a note: "The ac-verifier skill referenced in this ADR was removed in `remove-ac-verifier-completely`. The rdd-verifier v2.0 (ADR-0045) supersedes it."

#### Scenario: ADR-0035 carries note
- **WHEN** `docs/adr/ADR-0035-verifier-archive-gate-boundary.md` is read
- **THEN** it MUST contain a note: "The ac-verifier subprocess fallback referenced in this ADR was removed in `remove-ac-verifier-completely`."

### Requirement: regression zero new failures
`./test.sh --full --regression` MUST report 0 new bats failures vs the baseline (`KNOWN_FAILURES.txt`).

#### Scenario: bats regression baseline preserved
- **WHEN** `./test.sh --full --regression` is run
- **THEN** the report MUST show "新增失败: 0" or "✅ 0 新增失败"
- **AND** pytest failures MUST be limited to the 11 pre-existing unit + 1 pre-existing integration collection error (verified via stash baseline)

### Requirement: openspec validate passes
The change MUST validate strictly under openspec v1.4+ validation rules.

#### Scenario: openspec validate --strict green
- **WHEN** `openspec validate remove-ac-verifier-completely --strict` is run
- **THEN** the output MUST be "Change 'remove-ac-verifier-completely' is valid"

