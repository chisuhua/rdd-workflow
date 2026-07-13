---
SCOPE: shared
STATUS: PROPOSED
DATE: 2026-07-11
CHANGE: sync-workflow-contracts
RELATED: add-spec-validation-gates (validators will treat this change's MODIFIED Requirements the same way as any other change)
RELATED_INCIDENT: 2026-07-11 post-release audit; 7 drift categories identified across USAGE/AGENTS/INSTALL/README/package.json/ADR index/openspec specs (see change proposal.md §Why)
---

# Capability: doc-truth-sync

> Synchronize the documentation surfaces (USAGE.md, AGENTS.md, INSTALL.md, README.md,
> package.json, docs/adr/README.md, openspec/specs) with production skill code,
> and add anti-drift contract tests that fail CI when any surface diverges from
> another.
>
> **Status**: Spec delta (PROPOSED). The original `doc-truth-sync` capability was
> archived from `v2-post-release-audit`. This change extends it with explicit
> anti-drift test Requirements.

## ADDED Requirements

### Requirement: doc-contract-tests-required

The system SHALL provide anti-drift contract tests that catch silent rot between
documentation surfaces (USAGE.md, AGENTS.md, INSTALL.md, README.md,
package.json, docs/adr/README.md) and OpenSpec specs. The tests MUST fail CI
(error severity) when any of the following drift classes are observed:

- **D1 — Skill count drift**: `package.json::skills[]` length disagrees with
  `ls skills/*.md | wc -l` (the lengths MUST be equal — Decision 3 翻 A 后所有
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
  silently normalized. One exception: `proposal-suggestions.md` at project root
  is intentionally git-tracked and undotted.
- **D5 — `npm test` trap regression**: `package.json::scripts.test` no longer
  contains exactly `bats tests/` (the npm-vs-pytest caveat requires
  `pytest tests/` to be a separate, explicit invocation).
- **D6 — guide-spec reference**: any docs or spec mentions `guide-spec` as a
  current skill (it was removed in v2.0; `guide-arch` + `guide-plan` are the
  v2.0+ replacements).
- **D7 — ADR-0013 dup unflagged**: `docs/adr/README.md` does not explicitly
  flag the duplicated ADR-0013 numbering (`extract-scan-state` +
  `incremental-skeleton-planning`) with a follow-up decision note.

The tests SHALL live at:

- `tests/integration/test_doc_contracts.bats` (drift classes D1, D3, D4, D5, D6)
- `tests/integration/test_adr_index.bats` (drift class D2)
- `tests/unit/test_doc_contracts.py` (drift classes D1, D4, D6; cross-spec checks)

The tests MUST run in CI without new dependencies (only `bats`, `pytest`,
`grep`, `find`, `python3` stdlib). Tests MUST be sub-second.

The tests MUST emit actionable error messages identifying the offending doc,
the offending field, and the expected vs actual value.

#### Scenario: skill count drift is caught (D1)

- **WHEN** a contributor adds `skills/foo.md` without updating `package.json::skills[]`
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

- **WHEN** USAGE.md describes ship-side as "Phase 1, 1.5, 2, 2.5, 3, 4, 5" (7 numbered subphases)
- **AND** `openspec/specs/general/spec.md::Requirement general-docs-match-code::Scenario USAGE.md ship-side phase count`
  still asserts "5 阶段 + 1 退出"
- **AND** CI runs `bats tests/integration/test_doc_contracts.bats`
- **THEN** the test exits 1
- **AND** stderr reports the discrepancy (7 vs 5)

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

#### Scenario: npm test trap regression (D5)

- **WHEN** a contributor modifies `package.json::scripts.test` to include
  `pytest tests/` (in addition to or instead of `bats tests/`)
- **AND** CI runs `bats tests/integration/test_doc_contracts.bats`
- **THEN** the npm-test-vs-pytest test exits 1
- **AND** stderr reminds: "npm test MUST only run bats; pytest is a separate command"

#### Scenario: guide-spec reference caught (D6)

- **WHEN** any doc file (USAGE.md, AGENTS.md, INSTALL.md, README.md, *.md under
  `openspec/specs/`, `docs/adr/`) contains the literal string `guide-spec` as a
  current skill (excluding historical references dated pre-v2.0)
- **AND** CI runs `pytest tests/unit/test_doc_contracts.py`
- **THEN** the test exits 1
- **AND** stderr identifies the file and line containing the stale reference

#### Scenario: ADR-0013 dup unflagged (D7)

- **WHEN** `docs/adr/README.md` does NOT contain a flag/follow-up note about
  the duplicated ADR-0013 numbering
- **AND** CI runs `bats tests/integration/test_adr_index.bats`
- **THEN** the test exits 1
- **AND** stderr identifies the missing flag block

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

- **WHEN** USAGE.md says ship-side has 5 phases
- **AND** `skills/guide-ship.md` describes 7 numbered subphases
- **AND** `openspec/specs/general/spec.md::Requirement general-docs-match-code` says 5 phases
- **THEN** the contributor MUST update USAGE.md and general/spec.md to match
  `skills/guide-ship.md` (the L1 source)
- **AND** MUST NOT modify `skills/guide-ship.md` to "match the docs"

## MODIFIED Requirements

### Requirement: install-usage-readme-metadata-sync

The system SHALL synchronize `skills/INSTALL.md`, `USAGE.md`, and `README.md`
with `package.json` (v2.0+, current skill count), including version numbers,
skill counts, and directory structure listings. The synchronized state MUST be
locked by the `doc-contract-tests-required` test Requirement above.

#### Scenario: INSTALL.md lists all current skill count

- **WHEN** a user installs via `skill_use("INSTALL")`
- **THEN** the skill list in the description SHALL include all on-disk
  `skills/*.md` files
- **AND** the package.json template SHALL derive version from the actual package.json
- **AND** the count SHALL be 13 (current `ls skills/*.md | wc -l`), matching
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
- **THEN** the directory tree SHALL include `guide-arch.md`, `guide-plan.md`,
  `loop_engine.py`, and the `_lib/` subdirectory
- **AND** the skill count in any narrative text SHALL match `ls skills/*.md`

### Requirement: v2-adr-summary-accurate

The system SHALL update `docs/v2-adr-summary.md` (if it exists) and
`docs/adr/README.md` to include all real ADRs (0001-0019), fix the ADR count
from "9" or "12" or "13" to "19" (real ADRs in `docs/adr/`), remove any blanket
"not implemented" claims, and add missing ADR-0013/0014/0015/0017/0018/0019
sections.

#### Scenario: v2-adr-summary shows all real ADRs

- **WHEN** a user reads `docs/v2-adr-summary.md` (if it exists)
- **THEN** the ADR count SHALL read "19" (current real ADRs)
- **AND** ADR-0013, 0014, 0015, 0017, 0018, 0019 SHALL appear in the body
- **AND** any "未实施" DRAFT banner SHALL be replaced with implementation status

#### Scenario: docs/adr/README.md status table covers all real ADRs

- **WHEN** a user opens `docs/adr/README.md`
- **THEN** each real ADR (0001-0019) SHALL appear in the v2.0 ADR status table
  at the top of the file
- **AND** the duplicated ADR-0013 (`extract-scan-state` +
  `incremental-skeleton-planning`) SHALL have an explicit follow-up flag
  pointing to the future `init-deep` decision
- **AND** the ADR list table SHALL have consistent numbering with the status
  table

## REMOVED Requirements

(none)

## RENAMED Requirements

(none)