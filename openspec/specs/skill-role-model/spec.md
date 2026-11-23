# skill-role-model Specification

## Purpose
TBD - created by archiving change add-phase-role-model. Update Purpose after archive.

## Requirements

### Requirement: skill-frontmatter-role-field-optional

The 4 phase SKILL.md files (`rdd-arch`, `rdd-planner`, `rdd-builder`, `rdd-verifier`) MAY include a top-level `role:` field in their YAML frontmatter. The field is optional and existing SKILL.md files without the field MUST continue to load and parse correctly.

#### Scenario: skill loads without role field

- GIVEN a SKILL.md without a `role:` field
- WHEN `skill_use("rdd-arch")` (or any phase skill) is invoked（v4 重命名，原 `guide-arch`）
<!-- v4-residue:allow=rename-history -->
- THEN the skill loads successfully
- AND no parse error is raised

#### Scenario: skill loads with role field

- GIVEN a SKILL.md with a `role:` field containing `title`, `perspective`, `boundaries.owns`, `boundaries.not_owns`, `boundaries.human_involvement`
- WHEN `skill_use("rdd-arch")` (or any phase skill) is invoked（v4 重命名，原 `guide-arch`）
<!-- v4-residue:allow=rename-history -->
- THEN the skill loads successfully
- AND the `role:` field is accessible via the schema-validated frontmatter

### Requirement: skill-role-schema-defined

A JSON schema (`_lib/schemas/skill_role_schema.json`) MUST define the `role:` field structure with the following sub-fields:
- `title` (string, required)
- `perspective` (string, required)
- `boundaries.owns` (array of strings, required)
- `boundaries.not_owns` (array of strings, required)
- `boundaries.human_involvement` (enum: "high" | "medium" | "low", required, **nested under `boundaries`**)

Each string in `boundaries.owns` and `boundaries.not_owns` MUST be a bare path or glob. Parenthetical notes are NOT permitted: the schema MUST reject any entry containing `(` or `)`.

Ownership entries use two placeholder forms — `<name>` and `<change>` — which are equivalent for matching purposes. Consumers MUST normalize `<change>` to `<name>` before comparison.

#### Requirement: ownership-entry-matching-semantics

Ownership entries are matched against a candidate path with the following normative algorithm.

**1. Normalize each entry**
- Expand `{a,b}` brace alternatives into separate entries.
- Replace `<name>` and `<change>` with `*`.

**2. Classify each entry by its trailing `/`**
- **File entry** (no trailing `/`): matched by `fnmatch` against the candidate path (`*` crosses `/`).
- **Directory entry** (trailing `/`): matched when the candidate path lies inside that directory. The match is **segment-wise**: the directory's segments are compared against the candidate's leading segments, and a segment containing `*` matches exactly ONE candidate segment (it does not cross `/`). The candidate must be strictly inside the directory (or be the directory itself). Example: `openspec/changes/<name>/` → `openspec/changes/*/` matches `openspec/changes/my-change/proposal.md`, because `*` consumes the single segment `my-change`.

**3. Decide ownership of a candidate path**
- If any **file-level** entry in `not_owns` matches → the path is NOT owned.
- Else if any **file-level** entry in `owns` matches → the path IS owned.
- Else if any **directory-level** entry in `not_owns` matches → the path is NOT owned.
- Else if any **directory-level** entry in `owns` matches → the path IS owned.
- Else → undecided (no entry claims it).

Two precedence rules follow from that order:

- **Within one level, `not_owns` wins over `owns`.** An explicit exclusion is
  more specific than a general grant.
- **File-level entries take precedence over directory-level entries.** This is
  what lets `rdd-quick` own `openspec/changes/<name>/tasks.md` while not
  owning the enclosing `openspec/changes/<name>/` — the file-level grant is
  more specific than the directory-level exclusion.

The two rules are independent: a file-level `not_owns` entry therefore beats a
file-level `owns` entry, but loses to nothing at the file level.

This requirement specifies the per-skill evaluation only. The following are explicitly OUT of scope here and MUST be specified before any consumer relies on them: cross-skill arbitration (which skill owns a path that several skills claim — `openspec/changes/<name>/tasks.md` is claimed by both `rdd-builder` and `rdd-quick` today), candidate-path relativity (project-relative vs absolute vs package-relative — `rdd-env-bootstrap` owns package-internal paths such as `skills/rdd-doctor/` while `rdd-planner` owns project-relative ones), and whether a directory entry's `*` is a wildcard segment or a literal.

#### Scenario: a file owned inside a directory that is not owned

- GIVEN `owns` contains `openspec/changes/<name>/tasks.md`
- AND `not_owns` contains `openspec/changes/<name>/`
- WHEN the path `openspec/changes/my-change/tasks.md` is evaluated
- THEN it IS owned (the file entry wins over the directory entry)

#### Scenario: a file-level exclusion beats a file-level grant

- GIVEN `owns` contains `.rddf/plans/<name>.md`
- AND `not_owns` contains `.rddf/plans/quick-*.md`
- WHEN the path `.rddf/plans/quick-x.md` is evaluated
- THEN it is NOT owned

#### Scenario: other files inside a not-owned directory are not owned

- GIVEN `owns` contains `openspec/changes/<name>/tasks.md`
- AND `not_owns` contains `openspec/changes/<name>/`
- WHEN the path `openspec/changes/my-change/proposal.md` is evaluated
- THEN it is NOT owned

#### Scenario: brace alternatives are expanded before matching

- GIVEN `owns` contains `openspec/changes/<name>/{tasks,design}.md`
- WHEN the path `openspec/changes/my-change/tasks.md` is evaluated
- THEN it IS owned

#### Scenario: schema validates complete role field

- GIVEN a SKILL.md with all 5 role sub-fields present and `human_involvement` nested under `boundaries`
- WHEN the schema validator runs
- THEN validation passes

#### Scenario: schema rejects missing sub-field

- GIVEN a SKILL.md with `role:` but missing `title`
- WHEN the schema validator runs
- THEN validation reports a missing `title` error

#### Scenario: schema rejects human_involvement at the wrong nesting level

- GIVEN a SKILL.md with `human_involvement` directly under `role:` instead of under `boundaries:`
- WHEN the schema validator runs
- THEN validation fails with "Additional properties are not allowed"

#### Scenario: schema rejects parenthetical note in owns

- GIVEN an owns entry `"openspec/changes/<name>/proposal.md (per ADR-0025)"`
- WHEN the schema validator runs
- THEN validation fails

#### Scenario: schema accepts glob syntax

- GIVEN an owns entry `"openspec/changes/<name>/{tasks,design}.md"`
- WHEN the schema validator runs
- THEN validation passes

### Requirement: skill-role-boundaries-accurate

For each phase skill, `role.boundaries.owns` MUST exactly match the file paths listed in the SKILL.md's "职责边界" section's "拥有" bullet (verified by manual review at PR time).

#### Scenario: rdd-arch owns ADR + roadmap

- GIVEN the `rdd-arch` SKILL.md
- WHEN checking `role.boundaries.owns`
- THEN it contains `docs/adr/ADR-*.md` and `roadmap.md` (matching the existing "职责边界" section)

### Requirement: skill-role-human-involvement-level

The `role.boundaries.human_involvement` field MUST use one of three values: `high`, `medium`, or `low`, corresponding to the ADR-0003 gradient (high = arch, medium = design/plan, low = ship).

#### Scenario: rdd-arch has high involvement

- GIVEN the `rdd-arch` SKILL.md has `role.boundaries.human_involvement: high`
- WHEN the schema validator runs
- THEN validation passes

#### Scenario: invalid human_involvement value rejected

- GIVEN a SKILL.md with `role.boundaries.human_involvement: extreme`
- WHEN the schema validator runs
- THEN validation fails (allowed values: high/medium/low)

### Requirement: skill-role-metadata-consistent-across-phases

All 4 phase SKILL.md files (`rdd-arch`, `rdd-planner`, `rdd-builder`, `rdd-verifier`) MUST have the same `role:` field structure with all 5 sub-fields present (no missing sub-fields across the 4 files).

#### Scenario: all 4 skills have complete role fields

- GIVEN the 4 phase SKILL.md files
- WHEN the bats test verifies each has 5 sub-fields
- THEN all 4 pass the test

### Requirement: skill-role-owns-generated-artifacts-only

A phase skill's `role.boundaries.owns` MUST NOT list an artifact that the skill does not generate. When a skill stops (or never starts) producing an artifact, the entry MUST be removed from `owns` rather than kept aspirationally.

#### Scenario: rdd-builder does not claim design.md

- GIVEN `skills/rdd-builder/scripts/phase1_plan.sh` never writes `openspec/changes/<name>/design.md`
- WHEN `role.boundaries.owns` of `rdd-builder` is inspected
- THEN no entry contains `design.md`
- AND the SKILL.md body states that `design.md` is authored by the executing agent

#### Scenario: every shipped skill frontmatter passes schema

- WHEN all `skills/*/SKILL.md` role frontmatters are validated against `skill_role_schema.json`
- THEN all pass (currently 7 skills declare `role:`)
