# doc-truth-sync Specification

## Purpose
TBD - created by archiving change v2-post-release-audit. Update Purpose after archive.
## Requirements
### Requirement: adr-readme-status-truth
The system SHALL update `docs/adr/README.md` to reflect actual implementation status of each v2.0 ADR, replacing the blanket "not implemented" claim with per-ADR audit results.

#### Scenario: ADR README shows per-ADR status
- **WHEN** a user opens `docs/adr/README.md`
- **THEN** every ADR file under `docs/adr/` SHALL appear in the ADR 列表的表格
  with a non-empty 状态 cell
- **AND** the blanket "v2.0 ADRs are design drafts, not implemented" header SHALL be removed
- **AND** the ADR 列表的表格 SHALL be byte-identical to the output of
  `_lib/adr_index_generator.py` (locked by `tests/unit/test_adr_index_gate.py`)

### Requirement: adr-index-covers-all-real-adrs

The system SHALL keep `docs/adr/README.md`'s ADR 列表 synchronized with the
actual ADR files under `docs/adr/`, and SHALL NOT hardcode an ADR count in
any documentation surface.

> `docs/v2-adr-summary.md` no longer exists — its content was folded into
> `docs/adr/README.md` and `docs/architecture/` (docs-restructure, 2026-08-07).
> The ADR count is therefore derived from disk (L2), never written as a literal.

#### Scenario: ADR 列表 covers every ADR file on disk

- **WHEN** a user opens `docs/adr/README.md`
- **THEN** every `docs/adr/ADR-*.md` file SHALL appear in the ADR 列表的表格
  with a non-empty 状态 cell

#### Scenario: ADR counts are derived from disk, never hardcoded

- **WHEN** any documentation surface states how many ADRs exist
- **THEN** the number SHALL equal the count of `docs/adr/ADR-*.md` on disk
- **AND** no documentation surface SHALL hardcode an ADR count

### Requirement: migration-guide-no-fictional-cli
The system SHALL remove or replace all references to the non-existent `rdd-workflow migrate/sync/report` CLI commands in `docs/migration/v1-to-v2.md`, replacing them with equivalent manual steps or "planned" markers.

#### Scenario: migration guide fictional CLI references carry a planned marker
- **WHEN** a user reads `docs/migration/v1-to-v2.md`
- **THEN** every reference to `rdd-workflow migrate`, `rdd-workflow sync`, or
  `rdd-workflow report` SHALL appear on a line that also carries an explicit
  planned / 未实现 marker (e.g. "规划中，v2.1 实现")
- **AND** any previously fictional CLI commands SHALL be replaced with actionable manual steps or clear "planned for v2.1" markers

#### Scenario: migration guide marks every historical path with its current location
- **WHEN** a user reads `docs/migration/v1-to-v2.md`
- **THEN** every file path listed in the 「新增技能文件」/「保留技能文件」/「弃用技能文件」
  tables SHALL carry a 「当前路径（v4.0+）」 cell
- **AND** every value in that cell SHALL be a path that exists on disk
  (paths under `docs/legacy/` count as existing)

### Requirement: install-usage-readme-metadata-sync

The system SHALL synchronize `skills/INSTALL.md`, `USAGE.md`, and `README.md`
with `package.json` (v2.0+, current skill count), including version numbers,
skill counts, and directory structure listings. The synchronized state MUST be
locked by the `doc-contract-tests-required` test Requirement above.

#### Scenario: INSTALL.md lists all current skill count

- **WHEN** a user installs via `skill_use("INSTALL")`
- **THEN** the skill list in the description SHALL include all on-disk
  `skills/<name>/SKILL.md` files
- **AND** the package.json template SHALL derive version from the actual package.json
- **AND** the count SHALL match the canonical on-disk skill count, matching
  `package.json::skills[]` length (Decision 3 = A)
- **AND** the description SHALL NOT state a src-only delta (no "11 published"
  mention); both numbers are equal so no delta explanation is needed

#### Scenario: USAGE.md shows correct version and dotted state paths

- **WHEN** a user reads `USAGE.md`
- **THEN** the version header SHALL reflect the current `package.json` version
- **AND** the state-file table SHALL list only existing/canonicalized files and
  document the known dotted-vs-undotted convention explicitly (for example,
  `.arch-handoff.json` is dotted while `deps-analysis.json` is not)
- **AND** the ship-side phase count SHALL describe 7 numbered subphases
  (Phase 1, 1.5, 2, 2.5, 3, 4, 5)
- **AND** there SHALL be no duplicate section headers

#### Scenario: README.md directory structure is complete

- **WHEN** a user reads `README.md`
- **THEN** the directory tree SHALL include `rdd-arch/SKILL.md`, `rdd-builder/SKILL.md`,
  `loop_engine.py`, and the `_lib/` subdirectory
- **AND** the skill count in any narrative text SHALL match the canonical
  on-disk skill count

### Requirement: promoted-specs-remain-promoted
The system SHALL keep the 4 spec directories promoted from the archive present under `openspec/specs/`: release-management, migration-docs, test-suite, three-phase-skills.

#### Scenario: promoted spec directories are present
- **WHEN** a user runs `ls openspec/specs/`
- **THEN** the listing SHALL include: release-management, migration-docs, test-suite, three-phase-skills
- **AND** the requirement SHALL NOT pin a total directory count

### Requirement: doc-contract-tests-required

The system SHALL provide anti-drift contract tests that catch silent rot between
documentation surfaces (USAGE.md, AGENTS.md, INSTALL.md, README.md,
package.json, docs/adr/README.md) and OpenSpec specs. The tests MUST fail CI
(error severity) when any of the following drift classes are observed:

- **D1 — Skill count drift**: `package.json::skills[]` length disagrees with
  the canonical on-disk skill count (`skills/<name>/SKILL.md`, excluding
  `deprecated:` shims) (the lengths MUST be equal — Decision 3 翻 A 后所有
  skill 都通过 npm 发布,无 src-only 例外,`package.json` 不应有 `_comment` 字段声明 src-only)。
- **D2 — ADR index drift**: `docs/adr/README.md` references an ADR number whose
  `ADR-NNNN-*.md` file does not exist, OR fails to reference a real ADR file.
- **D3 — Ship-side phase count drift**: USAGE.md describes ship-side phases
  differently from `openspec/specs/general/spec.md::Requirement general-docs-match-code`.
- **D4 — State-file path convention drift**: state-file paths diverge from
  production code or from the explicit canonical/legacy notes. Current known
  production paths include `.rddf/state/.arch-handoff.json`,
  `.rddf/state/.plan-handoff.json`, `.rddf/state/.deps-candidates.json`,
  `.rddf/state/.deps-output.md`, `.rddf/state/deps-analysis.json`,
  `.rddf/state/iteration.json`, `.rddf/state/sessions.json`, and
  `.rddf/state/index.md`. `roadmap-state.json` has both dotted and undotted
  references and MUST be called out as a canonicalization decision rather than
  silently normalized. One exception: `improvement-suggestions.md` at project root
  is intentionally git-tracked and undotted.
- **D5 — `npm test` composition drift**: `package.json::scripts.test` SHALL run
  both the bats suite and the pytest suite (v3.0+: `npm run test:bats &&
  npm run test:python`). It SHALL NOT revert to running bats only, and it
  SHALL NOT drop the pytest suite — a contributor MUST NOT edit the docs to
  claim that `npm test` skips Python.
- **D6 — guide-spec reference**: any docs or spec mentions `guide-spec` as a
<!-- v4-residue:allow=guard -->
  current skill (it was removed in v2.0; `guide-arch` + `guide-plan` are the
<!-- v4-residue:allow=rename-history -->
  v2.0+ replacements).
- **D7 — ADR-0013 numbering collision**: `docs/adr/` SHALL NOT contain more
  than one `ADR-0013-*.md` file. The v2.0.2 renumbering moved
  `incremental-skeleton-planning` to ADR-0020; the disk is the single source
  of truth for ADR numbering (no README flag is required).

The tests SHALL live at:

- `tests/integration/test_doc_contracts.bats` (drift classes D1, D3, D4, D6)
- `tests/integration/test_adr_index.bats` (drift class D2)
- `tests/unit/test_doc_contracts.py` (drift classes D1, D4, D5, D6; cross-spec checks)

The tests MUST run in CI without new dependencies (only `bats`, `pytest`,
`grep`, `find`, `python3` stdlib). Tests MUST be sub-second.

The tests MUST emit actionable error messages identifying the offending doc,
the offending field, and the expected vs actual value.

#### Scenario: skill count drift is caught (D1)

- **WHEN** a contributor adds `skills/foo/SKILL.md` without updating `package.json::skills[]`
- **AND** CI runs `bats tests/integration/test_doc_contracts.bats`
- **THEN** the test exits 1
- **AND** stderr identifies which doc reports the stale count
- **AND** stderr includes both numbers (disk vs manifest) for fast triage

#### Scenario: ADR index references nonexistent file (D2)

- **WHEN** `docs/adr/README.md` lists `ADR-0020` with no corresponding
  `docs/adr/ADR-0020-*.md` file
- **AND** CI runs `bats tests/integration/test_adr_index.bats`
- **THEN** the test exits 1
- **AND** stderr identifies the missing ADR file

#### Scenario: ADR index omits a real ADR (D2 inverse)

- **WHEN** `docs/adr/ADR-0017-rddf-session.md` exists on disk
- **AND** `docs/adr/README.md` does NOT list `ADR-0017` in its status table
- **AND** CI runs `bats tests/integration/test_adr_index.bats`
- **THEN** the test exits 1
- **AND** stderr identifies the missing-from-index ADR file

#### Scenario: ship-side phase count drift (D3)

- **WHEN** USAGE.md and
  `openspec/specs/general/spec.md::Requirement general-docs-match-code::Scenario USAGE.md ship-side phase count`
  describe the ship-side subphase count differently
- **AND** CI runs `bats tests/integration/test_doc_contracts.bats`
- **THEN** the test exits 1
- **AND** stderr reports the discrepancy (both numbers)

#### Scenario: state-file path convention inconsistency (D4)

- **WHEN** general/spec.md references a state file path that does not match the
  production skill code (for example `handoff.json` instead of
  `.rddf/state/.arch-handoff.json`, or `.sisyphus/plans/<name>.md` instead of
  `.rddf/plans/<name>.md`)
- **AND** USAGE.md uses `.rddf/state/.arch-handoff.json` and
  `.rddf/plans/<name>.md`
- **AND** CI runs `pytest tests/unit/test_doc_contracts.py`
- **THEN** the test exits 1
- **AND** stderr identifies the inconsistent path

#### Scenario: npm test composition drift (D5)

- **WHEN** a contributor modifies `package.json::scripts.test` to drop
  `npm run test:python` (or `npm run test:bats`) from the composed `npm test`
- **AND** CI runs `pytest tests/unit/test_doc_contracts.py`
- **THEN** the npm-test-composition test exits 1
- **AND** stderr reminds: "npm test MUST run both the bats and the pytest suite"
- **AND** the docs SHALL NOT be edited to claim that `npm test` skips Python

#### Scenario: guide-spec reference caught (D6)
<!-- v4-residue:allow=guard -->

- **WHEN** any doc file (USAGE.md, AGENTS.md, INSTALL.md, README.md, *.md under
  `openspec/specs/`, `docs/adr/`) contains the literal string `guide-spec` as a
<!-- v4-residue:allow=guard -->
  current skill (excluding historical references dated pre-v2.0)
- **AND** CI runs `pytest tests/unit/test_doc_contracts.py`
- **THEN** the test exits 1
- **AND** stderr identifies the file and line containing the stale reference

#### Scenario: ADR-0013 numbering collision (D7)

- **WHEN** `docs/adr/` contains more than one `ADR-0013-*.md` file
- **AND** CI runs `bats tests/integration/test_adr_index.bats`
- **THEN** the test exits 1
- **AND** stderr identifies the colliding files

### Requirement: doc-surfaces-share-truth-source

The system SHALL establish a documented truth-source hierarchy so contributors
can resolve conflicts when docs disagree:

- **L1 (highest)**: production skill code (`skills/*.md`, `skills/_lib/*.py`).
  Modifying these changes runtime behavior.
- **L2**: filesystem ground truth (`ls`, `find`). Counts and lists are
  authoritative for "what exists".
- **L3**: distribution contract (`package.json::skills[]`) and OpenSpec specs
  (`openspec/specs/*/spec.md`). These are the "promised" surfaces.
- **L4 (lowest)**: narrative documentation (`USAGE.md`, `AGENTS.md`, `INSTALL.md`,
  `README.md`). These mirror L1-L3 with explanatory prose.

When reconciling drift, the rule is L4 → L3 → L2 → L1 (narrative docs follow
the contract, which follows the disk, which follows the runtime). L1 is never
modified to satisfy a doc; docs are updated to match L1.

#### Scenario: Contributor resolves conflict using truth-source hierarchy

- **WHEN** USAGE.md and
  `openspec/specs/general/spec.md::Requirement general-docs-match-code`
  describe the ship-side subphase count differently from
  `skills/rdd-builder/SKILL.md`
- **THEN** the contributor MUST update USAGE.md and general/spec.md to match
  `skills/rdd-builder/SKILL.md` (the L1 source)
- **AND** MUST NOT modify `skills/rdd-builder/SKILL.md` to "match the docs"

