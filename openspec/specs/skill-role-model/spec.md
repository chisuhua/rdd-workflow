# skill-role-model Specification

## Purpose
TBD - created by archiving change add-phase-role-model. Update Purpose after archive.
## Requirements
### Requirement: skill-frontmatter-role-field-optional

The 4 `guide-*` SKILL.md files (`guide-arch`, `guide-design`, `guide-plan`, `guide-ship`) MAY include a top-level `role:` field in their YAML frontmatter. The field is optional and existing SKILL.md files without the field MUST continue to load and parse correctly.

#### Scenario: skill loads without role field

- GIVEN a SKILL.md without a `role:` field
- WHEN `skill_use("guide-arch")` (or any phase skill) is invoked
- THEN the skill loads successfully
- AND no parse error is raised

#### Scenario: skill loads with role field

- GIVEN a SKILL.md with a `role:` field containing `title`, `perspective`, `boundaries.owns`, `boundaries.not_owns`, `boundaries.human_involvement`
- WHEN `skill_use("guide-arch")` (or any phase skill) is invoked
- THEN the skill loads successfully
- AND the `role:` field is accessible via the schema-validated frontmatter

### Requirement: skill-role-schema-defined

A JSON schema (`_lib/schemas/skill_role_schema.json`) MUST define the `role:` field structure with the following sub-fields:
- `title` (string, required)
- `perspective` (string, required)
- `boundaries.owns` (array of strings, required)
- `boundaries.not_owns` (array of strings, required)
- `boundaries.human_involvement` (enum: "high" | "medium" | "low", required)

#### Scenario: schema validates complete role field

- GIVEN a SKILL.md with all 5 role sub-fields present
- WHEN the schema validator runs
- THEN validation passes

#### Scenario: schema rejects missing sub-field

- GIVEN a SKILL.md with `role:` but missing `title`
- WHEN the schema validator runs
- THEN validation reports a missing `title` error

### Requirement: skill-role-boundaries-accurate

For each phase skill, `role.boundaries.owns` MUST exactly match the file paths listed in the SKILL.md's "职责边界" section's "拥有" bullet (verified by manual review at PR time).

#### Scenario: guide-arch owns ADR + roadmap

- GIVEN the `guide-arch` SKILL.md
- WHEN checking `role.boundaries.owns`
- THEN it contains `docs/adr/ADR-*.md` and `roadmap.md` (matching the existing "职责边界" section)

### Requirement: skill-role-human-involvement-level

The `role.boundaries.human_involvement` field MUST use one of three values: `high`, `medium`, or `low`, corresponding to the ADR-0003 gradient (high = arch, medium = design/plan, low = ship).

#### Scenario: guide-arch has high involvement

- GIVEN the `guide-arch` SKILL.md has `role.boundaries.human_involvement: high`
- WHEN the schema validator runs
- THEN validation passes

#### Scenario: invalid human_involvement value rejected

- GIVEN a SKILL.md with `role.boundaries.human_involvement: extreme`
- WHEN the schema validator runs
- THEN validation fails (allowed values: high/medium/low)

### Requirement: skill-role-metadata-consistent-across-phases

All 4 phase SKILL.md files (`guide-arch`, `guide-design`, `guide-plan`, `guide-ship`) MUST have the same `role:` field structure with all 5 sub-fields present (no missing sub-fields across the 4 files).

#### Scenario: all 4 skills have complete role fields

- GIVEN the 4 phase SKILL.md files
- WHEN the bats test verifies each has 5 sub-fields
- THEN all 4 pass the test

