# rdd-doctor-coverage-completion Specification

## Purpose
TBD - created by archiving change add-rdd-doctor-coverage-completion.

The rdd-doctor skill MUST expose 22 diagnostic categories, all wired through a lazy-import `_CHECKERS` dict. CI MUST護送 14 of the 22 categories via structural (fail-on-CRITICAL) and advisory (warn-only) gates.

## Requirements

### Requirement: lazy-import _CHECKERS dict

The `_CHECKERS` dict in `skills/rdd-doctor/scripts/doctor_main.py` MUST be a `name -> import_path` string map. `aggregate_findings` MUST resolve the callable via `_resolve_check(name)` on first invocation per category (memoizes back into the dict).

#### Scenario: temp-fixture tests pass without eager _lib import

GIVEN a test fixture copies `skills/rdd-doctor/` to a tempdir WITHOUT `_lib/`
WHEN `python3 <tempdir>/rdd-doctor/scripts/doctor_main.py --category proposal-section` runs
THEN the call succeeds (no `ModuleNotFoundError`) and emits proposal-section findings
AND `bats tests/integration/test_rdd_doctor_proposal_section.bats` shows 5/5 PASS.

#### Scenario: first-call lazy-resolve

GIVEN `_CHECKERS["state"] == "checks.state_schema_check.run"` (string)
WHEN `aggregate_findings` is invoked with `category="state"`
THEN `_resolve_check("state")` adds repo root to sys.path, imports `checks.state_schema_check`, resolves `.run`, and memoizes back into `_CHECKERS["state"]`.

### Requirement: 22 diagnostic categories wired

The `doctor_main._CHECKERS` dict MUST contain exactly 22 entries: state, plan-tdd, roadmap-meta, proposal-table, proposal-section, tasks-checkbox, migration-residue, orphan-gates, roadmap-refs, roadmap-feature, roadmap-md-integrity, roadmap-phases, docs-consistency, ai-context-bootstrap, gitignore, bypass-audit, improvement-frontmatter-consistency, objective-lifecycle, objective-structure, arch-audit, review-debt, roadmap-backup.

#### Scenario: review-debt detects unticketed TODO markers

GIVEN `.py/.sh/.bats` source contains bare `# TODO fix later` (no ticket id)
WHEN `bash skills/rdd-doctor/scripts/doctor.sh --category review-debt` runs
THEN the check emits `WARNING` Finding under `review-debt.unticketed-marker`.

#### Scenario: review-debt skips ticketed markers

GIVEN source contains `# TODO(RDDF-123) do thing` (ticket id present)
WHEN the review-debt check runs
THEN no Finding is emitted (ticket-reference form treated as resolved).

#### Scenario: roadmap-backup detects stale snapshots

GIVEN `.rddf/roadmap/.backup/20260101T120000Z/` exists (>90 days old)
WHEN `bash skills/rdd-doctor/scripts/doctor.sh --category roadmap-backup` runs
THEN the check emits `WARNING` Finding under `roadmap-backup.stale-snapshot`.

#### Scenario: roadmap-backup detects multiple snapshots

GIVEN `.rddf/roadmap/.backup/` contains ≥2 timestamped subdirectories
WHEN the roadmap-backup check runs
THEN the check emits `WARNING` Finding under `roadmap-backup.multiple-snapshots` (consolidation suggestion).

### Requirement: CI护送 14 of 22 categories

Per `.github/workflows/test.yml`, the rdd-doctor CI gate MUST護送 10 structural categories (fail-on-CRITICAL, exit ≥2 blocks PR) and 4 advisory categories (warn-only, never blocks):

**Structural** (10): state, plan-tdd, roadmap-meta, roadmap-refs, roadmap-feature, roadmap-md-integrity, roadmap-phases, objective-lifecycle, objective-structure, arch-audit.

**Advisory** (4): bypass-audit, migration-residue, review-debt, roadmap-backup.

#### Scenario: structural gate blocks on CRITICAL

GIVEN master has an unresolved `.rddf/roadmap.md` drift (e.g. missing AUTO-INDEX segment)
WHEN CI runs the structural gate
THEN the gate exits 1 and the PR cannot merge.

#### Scenario: advisory gate does not block

GIVEN master has a 100-day-old `.rddf/roadmap/.backup/` dir
WHEN CI runs the advisory gate
THEN the gate exits 0 with `::warning` annotation (warning logged but not blocking).

#### Scenario: 8 ungated categories available via direct invocation

GIVEN proposal-table, proposal-section, tasks-checkbox, orphan-gates, ai-context-bootstrap, gitignore, improvement-frontmatter-consistency, docs-consistency
WHEN user runs `bash skills/rdd-doctor/scripts/doctor.sh --category <name>` directly
THEN the check runs (single-category invocation) and emits findings normally.

### Requirement: sync test locks category count

The `bats tests/integration/test_rdd_doctor_skills_md_sync.bats` MUST dynamically parse `_CHECKERS.keys()` and assert that SKILL.md table row count == number of wired categories, with bidirectional subset checks (every documented is wired; every wired is documented).

#### Scenario: drift detection

GIVEN a developer adds a 23rd category to `_CHECKERS` but forgets to update SKILL.md table
WHEN the sync bats runs
THEN test 4 (every wired category is documented) fails with the 23rd category name.