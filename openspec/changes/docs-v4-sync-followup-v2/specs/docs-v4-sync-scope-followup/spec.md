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

#### Scenario: ONBOARDING.md transition diagram has no ac-verifier dead link

- **WHEN** `docs/ONBOARDING.md` L105 (rdd-verifier → ac-verifier transition) is rendered
- **THEN** the line does NOT reference `ac-verifier` (skill removed 2026-09-07 per ADR-0045, Oracle P1 catch)
- **AND** the transition text is rewritten to describe the self-contained LLM verification model without naming the deleted skill

#### Scenario: ONBOARDING.md has no `guide-*.md` instruction

- **WHEN** `docs/ONBOARDING.md` L370 (any contributor-facing instruction that names flat `.md` files) is rendered
- **THEN** the line does NOT say `guide-*.md` (all 4 guide-* skills deleted)
- **AND** the instruction uses either `rdd-*.md/SKILL.md` or the directory-style `skills/<name>/SKILL.md` form

#### Scenario: ONBOARDING.md phase table is 4 stage + 1 bypass

- **WHEN** the phase architecture section is rendered
- **THEN** the phase table has exactly 4 stage rows (Arch / Planner / Builder / Verifier) and 1 bypass row (Quick)
- **AND** the "Design" or "Plan" standalone phase rows do not appear (those are merged into Planner and Builder in v4)

### Requirement: docs-architecture-improvement-check-mechanisms-no-dead-links

The repository's `docs/architecture/improvement-check-mechanisms.md` MUST NOT contain links to deleted skill directories (`skills/guide-ship/`, etc.).

#### Scenario: improvement-check-mechanisms.md links resolve to existing paths

- **WHEN** `grep -rn "skills/guide-ship" docs/architecture/improvement-check-mechanisms.md` is run
- **THEN** the grep returns 0 hits
- **AND** all file path references in the document point to existing files (`skills/rdd-builder/scripts/phase2_5_review.sh` for review helper, `skills/rdd-builder/scripts/phase3_archive.sh` for archive helper — both renamed from `ship_*.sh` in v4 Wave 3 per Oracle review catch)

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

#### Scenario: skills-and-handoff.md has no live `skill_use("guide-*")` invocation

- **WHEN** L31 of skills-and-handoff.md is rendered
- **THEN** the line does NOT contain `skill_use("guide-arch")` (Oracle P1 catch — live invocation would 404 user)
- **AND** the line uses `skill_use("rdd-arch")` or a directory-style path example

### Requirement: doc-contract-test-extended-to-all-architecture-docs

The doc-contract test (`tests/integration/test_v4_doc_drift_contracts.bats`) MUST scan ALL `docs/architecture/*.md` files (not just the 3 modified by the parent change) for live `guide-*` references.

#### Scenario: Test 12 covers all docs/architecture/ files

- **WHEN** Test 12 runs
- **THEN** it iterates over all `.md` files matching `docs/architecture/*.md` (not a hardcoded 3-file list)
- **AND** any live `skill_use("guide-*")`, `Entry skill**: \`guide-*\``, or `skills/guide-*/` reference in any docs/architecture/ file fails the test
- **AND** the test excludes `rdd-arch-rdd-planner-integration.md` lines that document the compat shim (regex filtered with `grep -v 'shim\|DEPRECATED\|compat'` to allow `skill_use("guide-arch")` in shim-documentation context)
- **AND** the test does NOT match prose-only mentions like "ADR-0003 three-phase architecture" (Test 12 pattern requires `skill_use` or `Entry skill` or `skills/`, which prose lacks)

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
