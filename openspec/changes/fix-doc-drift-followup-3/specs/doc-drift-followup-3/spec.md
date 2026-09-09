# Spec Delta: doc-drift-followup-3

## ADDED Requirements

### Requirement: guide-skill-no-stale-invocation

The `skills/guide/SKILL.md` recommender MUST NOT contain any active `skill_use("guide-*")` invocation (where `guide-*` ∈ {`guide-arch`, `guide-design`, `guide-plan`, `guide-ship`, `guide-spec`}). All such invocations MUST be replaced with their v4 canonical equivalents:
- `guide-design` → `rdd-planner`
- `guide-plan` / `guide-ship` → `rdd-builder`
- `guide-spec` → `rdd-arch`
- `guide-arch` → `rdd-arch`

The `evolved-from:` frontmatter field is exempt (legitimate historical record).

#### Scenario: stage menu references rdd-* only

GIVEN an AI agent invokes `skill_use("guide")`
WHEN the agent reads `skills/guide/SKILL.md` stage menu (L96, L143-145)
THEN the menu lists 4 stages + 1 bypass row, all named `rdd-*`
AND zero rows reference `guide-*` as skill names

#### Scenario: action mapping table is rdd-only

GIVEN an AI agent invokes `skill_use("guide")`
WHEN the agent reads the action mapping table (L175-177)
THEN every `skill_use("...")` invocation in the table references `rdd-*` skill names only

### Requirement: subs-skill-stale-invocations-removed

The following 9 sub-skill SKILL.md files MUST NOT contain active `skill_use("guide-*")` invocations or stage-routing prose that recommends `guide-*`:

- `skills/execute/SKILL.md`
- `skills/status/SKILL.md`
- `skills/deps/SKILL.md`
- `skills/add-improve/SKILL.md`
- `skills/feature/SKILL.md`
- `skills/sync-hub/SKILL.md`
- `skills/rddf-session/SKILL.md`
- `skills/openspec-gate/SKILL.md`
- `skills/rdd-env-check/SKILL.md`

The `evolved-from:` frontmatter field is exempt.

#### Scenario: live skill_use invocations are rdd-only

GIVEN an AI agent invokes any of the 9 sub-skills above
WHEN the agent reads the corresponding SKILL.md
THEN zero active `skill_use("guide-*")` invocations appear
AND zero "被 guide-plan 调用" / "被 guide-ship 调用" prose patterns appear

#### Scenario: routing context refers to rdd-* stages

GIVEN an AI agent reads any of the 9 sub-skill SKILL.md files
WHEN the agent scans for stage-routing prose ("被 X 调用", "X 阶段", "X 完成")
THEN all stage references use `rdd-arch` / `rdd-planner` / `rdd-builder` / `rdd-verifier` / `rdd-quick`

### Requirement: migration-guide-file-exists

`docs/migration/v3-to-v4.md` MUST exist and serve as the canonical migration guide for v3.0 → v4.0 users. It MUST contain at minimum:
- 5 H2 sections: 阶段数变化 / Skill 重命名映射 / Removed skills / 工作流变更 / 升级步骤
- FAQ section
- 参考 section citing ADR-0043 / ADR-0044 / ADR-0047
- ≥ 80 lines total

#### Scenario: file exists with required sections

GIVEN a user opens `docs/migration/v3-to-v4.md`
WHEN the user reads the file
THEN the file contains all 5 required H2 sections + FAQ + 参考
AND the file is ≥ 80 lines
AND the 参考 section links to ADR-0043, ADR-0044, ADR-0047

#### Scenario: ONBOARDING.md link resolves

GIVEN a user reads `docs/ONBOARDING.md` line 375
WHEN the user clicks the `docs/migration/v3-to-v4.md` link
THEN the link resolves to an existing file (no 404)

### Requirement: readme-npm-install-current

`README.md` lines 13-19 (npm install section) MUST NOT reference outdated versions. The current latest stable is v4.0.0. Specifically:
- No `v1.x` references
- No `v2.0-beta` references
- Label `latest stable = v4.0.0`

#### Scenario: npm install commands match current version

GIVEN a user reads `README.md` lines 13-19
WHEN the user reads the npm install section
THEN zero `v1.x` or `v2.0-beta` strings appear
AND `v4.0.0` (or `v4`) is indicated as latest stable

### Requirement: test-coverage-extended

`tests/integration/test_v4_doc_drift_contracts.bats` MUST be extended from 10 tests (parent change) to 19 tests, adding:
- Test 16: `skills/guide/SKILL.md` no active `skill_use("guide-*")`
- Test 17: 9 sub-skill SKILL.md files no `guide-design`/`guide-plan`/`guide-ship`
- Test 18: `docs/migration/v3-to-v4.md` exists and ≥ 80 lines
- Test 19: `README.md` L13-19 no `v1.x` or `v2.0-beta`

#### Scenario: all 19 tests pass on patched tree

GIVEN the 12 source files have been patched per AC-1 through AC-4
WHEN `bats tests/integration/test_v4_doc_drift_contracts.bats` runs
THEN all 19 tests pass

#### Scenario: tests 16-19 fail on pre-patch tree

GIVEN the 12 source files have NOT been patched (pre-change state)
WHEN `bats tests/integration/test_v4_doc_drift_contracts.bats` runs
THEN Tests 16-19 FAIL (proving they catch the regression)

### Requirement: regression-gate-clean

The full test suite MUST NOT introduce new failures beyond the existing `tests/KNOWN_FAILURES.txt` baseline.

#### Scenario: full regression test stays within baseline

GIVEN `./test.sh --full --regression` is run on the patched tree
WHEN comparing new failures against `tests/KNOWN_FAILURES.txt` baseline
THEN no new failures appear (only pre-existing baseline failures remain)

### Requirement: rdd-doctor-no-new-critical

`bash skills/rdd-doctor/scripts/doctor.sh` MUST NOT add new CRITICAL findings as a result of this change. Current baseline is 6 CRITICAL (state schema drift + proposal-section drift); post-completion count MUST be ≤ 6.

#### Scenario: doctor CRITICAL count unchanged

GIVEN `rdd-doctor` reports N CRITICAL findings before this change
WHEN the change is applied (12 files patched)
THEN `rdd-doctor` reports ≤ N CRITICAL findings (no new drift introduced)

### Requirement: spec-delta-authoritative

The spec-delta in `openspec/changes/fix-doc-drift-followup-3/specs/doc-drift-followup-3/spec.md` is the authoritative contract for this change's deliverables. Any deviation in the implementation MUST be reflected here first.

#### Scenario: implementation matches spec-delta

GIVEN the spec-delta contains 8 Requirements
WHEN the change is implemented
THEN every Requirement's "MUST" / "MUST NOT" obligation is satisfied
AND every Scenario's GIVEN/WHEN/THEN passes
