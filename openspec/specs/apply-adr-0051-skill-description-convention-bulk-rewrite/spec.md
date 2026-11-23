# apply-adr-0051-skill-description-convention-bulk-rewrite Specification

## Purpose
TBD - created by archiving change apply-adr-0051-skill-description-convention-bulk-rewrite. Update Purpose after archive.
## Requirements
### Requirement: skill-description-convention

Every `skills/*/SKILL.md` frontmatter `description` field MUST comply with ADR-0051's single-responsibility convention: it answers only "when to invoke this skill" and references (rather than duplicates) `role.boundaries.owns / not_owns` for boundary ownership. Anti-routing guidance belongs in `guide` recommender, not in individual skill descriptions.

#### Scenario: description under 200 tokens

- **WHEN** an AI agent reads a skill's `description` field for skill-selection
- **THEN** the description is no more than 200 tokens (approximately 800 characters)
- **AND** the description prioritizes identity, trigger preconditions, and default behavior

#### Scenario: description has no anti-trigger phrasing

- **WHEN** an AI agent reads a skill's `description` field
- **THEN** the description does NOT contain phrases like `DO NOT use`, `Prefer <other> instead`, `Legacy entry`, or equivalent anti-routing language
- **AND** anti-routing judgment is centralized per-skill in each `SKILL.md` description（原集中落点 `skills/guide/SKILL.md` 已随 ADR-0063 归档）

#### Scenario: description references rather than duplicates boundaries

- **WHEN** an AI agent reads a skill's `description` field for ownership boundary context
- **THEN** the description references `role.boundaries.owns / not_owns` rather than copying the lists verbatim
- **AND** single-source-of-truth for boundaries is the `role.boundaries` field per ADR-0028

#### Scenario: description does not guide to deprecated paths

- **WHEN** an AI agent reads a skill's `description` field
- **THEN** the description does NOT direct the agent to deprecated or legacy fallback paths (e.g. `propose` sub-skill, `.plan-handoff.json` fallback)
- **AND** the description maintains "strict gatekeeper" tone — only canonical preconditions are stated

#### Scenario: guide recommender centralizes anti-routing

- **WHEN** an AI agent uses the `guide` skill to select the next skill to invoke
- **THEN** the recommender consults a centralized anti-routing table covering all 26 skills
- **AND** the centralized table covers the same anti-routing information previously distributed in skill descriptions (DO NOT use / Prefer instead / Legacy entry cases)

