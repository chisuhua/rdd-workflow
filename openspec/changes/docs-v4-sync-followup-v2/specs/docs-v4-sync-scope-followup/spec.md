## ADDED Requirements

### Requirement: docs-ONBOARDING-md-reflects-v4

The repository's `docs/ONBOARDING.md` (the new-user entry point per `docs/architecture/README.md` Update Convention) MUST describe the v4 four-stage architecture with `rdd-quick` bypass, not the v3 5-phase model.

#### Scenario: ONBOARDING.md directory tree lists rdd-* skill files

- **WHEN** a new user consults `docs/ONBOARDING.md` for the skill file list
- **THEN** the directory tree shows `rdd-arch.md`, `rdd-planner.md`, `rdd-builder.md`, `rdd-verifier.md`, `rdd-quick.md`
- **AND** zero tree entries reference `guide-arch.md`, `guide-design.md`, `guide-plan.md`, `guide-ship.md`, or `guide-spec.md`

#### Scenario: ONBOARDING.md "Recommended" line uses rdd-planner

- **WHEN** `docs/ONBOARDING.md` L194 is rendered (the "💡 Recommended: skill_use(...)" line)
- **THEN** the recommended skill is `rdd-planner`
- **AND** calling `skill_use("guide-plan")` (or any other `guide-*` skill) does NOT appear in the recommended line

#### Scenario: ONBOARDING.md phase table is 4 stage + 1 bypass

- **WHEN** the phase architecture section is rendered
- **THEN** the phase table has exactly 4 stage rows (Arch / Planner / Builder / Verifier) and 1 bypass row (Quick)
- **AND** the "Design" or "Plan" standalone phase rows do not appear (those are merged into Planner and Builder in v4)

### Requirement: docs-architecture-improvement-check-mechanisms-no-dead-links

The repository's `docs/architecture/improvement-check-mechanisms.md` MUST NOT contain links to deleted skill directories (`skills/guide-ship/`, etc.).

#### Scenario: improvement-check-mechanisms.md links resolve to existing paths

- **WHEN** `grep -rn "skills/guide-ship" docs/architecture/improvement-check-mechanisms.md` is run
- **THEN** the grep returns 0 hits
- **AND** all file path references in the document point to existing files (`skills/rdd-builder/...` after fix)

### Requirement: skills-INSTALL-md-no-guide-star-skill-references

The repository's `skills/INSTALL.md` MUST NOT reference the deprecated `guide-design`, `guide-plan`, `guide-ship` skill names.

#### Scenario: INSTALL.md mentions rdd-* canonical skill names

- **WHEN** `grep -rn "guide-design\|guide-plan\|guide-ship" skills/INSTALL.md` is run
- **THEN** the grep returns 0 hits
- **AND** source-chain references point to `rdd-builder.md` (or other rdd-* skills)

### Requirement: docs-architecture-skills-and-handoff-no-deleted-path-examples

The repository's `docs/architecture/skills-and-handoff.md` MUST NOT show discovery path examples pointing to deleted skill directories.

#### Scenario: skills-and-handoff.md discovery examples use rdd-arch path

- **WHEN** the discovery path examples section is rendered
- **THEN** `grep -rn "skills/guide-arch" docs/architecture/skills-and-handoff.md` returns 0 hits
- **AND** the 4 example paths all start with `skills/rdd-arch/` or `rdd-workflow/skills/rdd-arch/`

### Requirement: doc-contract-test-extended-to-all-architecture-docs

The doc-contract test (`tests/integration/test_v4_doc_drift_contracts.bats`) MUST scan ALL `docs/architecture/*.md` files (not just the 3 modified by the parent change) for live `guide-*` references.

#### Scenario: Test 12 covers all docs/architecture/ files

- **WHEN** Test 12 runs
- **THEN** it iterates over all `.md` files matching `docs/architecture/*.md` (not a hardcoded 3-file list)
- **AND** any live `skill_use("guide-*")`, `Entry skill**: \`guide-*\``, or `skills/guide-*/` reference in any docs/architecture/ file fails the test

#### Scenario: New Test 14 covers ONBOARDING.md live skill_use commands

- **WHEN** Test 14 runs
- **THEN** it scans `docs/ONBOARDING.md` code blocks for `skill_use("guide-arch|guide-design|guide-plan|guide-ship|guide-spec")` invocations
- **AND** any match fails the test

#### Scenario: New Test 15 covers INSTALL.md guide-* references

- **WHEN** Test 15 runs
- **THEN** it greps `skills/INSTALL.md` for `guide-design|guide-plan|guide-ship` skill name references
- **AND** any match fails the test

#### Scenario: pre-patch fail verification (Test 14 + Test 15)

- **WHEN** the test file is run against the pre-patch tree (via `git stash` of the doc edits)
- **THEN** Tests 14 and 15 FAIL (catches the drift that the parent change deferred)
- **AND** after restoring the doc edits (via `git stash pop`), all 15 tests pass

### Requirement: cross-user-facing-doc-cleanup

The repository's user-facing documentation files (`README.md`, `USAGE.md`, `docs/ONBOARDING.md`) MUST NOT contain live `skill_use("guide-*")` invocations that would direct users to deleted skills.

#### Scenario: cross-doc live skill_use grep returns 0

- **WHEN** `grep -rn 'skill_use("guide-' docs/ONBOARDING.md USAGE.md README.md` is run
- **THEN** the grep returns 0 hits
- **AND** users following any of the 3 docs can `skill_use` the recommended skills without hitting a 404
