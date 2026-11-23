# feat-roadmap-discovery-completion Specification

## Purpose
TBD - created by archiving change feat-roadmap-discovery-completion. Update Purpose after archive.
## Requirements
### Requirement: roadmap-feature doctor category MUST check 3 invariants

The system MUST provide `rddf doctor --category roadmap-feature` that reports findings (without modifying any files) for the following 3 invariants:

#### Scenario: All features valid, no drift
- **GIVEN** `.rddf/roadmap/features/*.md` exist with complete frontmatter (id/kind/status/phase_refs/主题)
- **AND** `.rddf/state/iteration.json::feature_view.features` contains every active feature id
- **AND** either AGENTS.md has no `<!-- AUTO: feature fragments start -->` block, or its block's table matches the current feature set
- **WHEN** `rddf doctor --category roadmap-feature` runs
- **THEN** zero findings emitted, exit code 0

#### Scenario: Feature fragment missing frontmatter field
- **GIVEN** `.rddf/roadmap/features/feat-x.md` exists but frontmatter lacks `主题` field
- **WHEN** `rddf doctor --category roadmap-feature` runs
- **THEN** emits 1 WARNING finding with category `roadmap-feature.frontmatter`,
  snippet `feat-x.md: missing required field '主题'`, exit code 1

#### Scenario: AGENTS.md AUTO block contains stale feature
- **GIVEN** `.rddf/roadmap/features/feat-active.md` exists with status active
- **AND** AGENTS.md AUTO block contains `feat-deleted` (not in features/)
- **WHEN** `rddf doctor --category roadmap-feature` runs
- **THEN** emits 1 CRITICAL finding with category `roadmap-feature.agents-drift`,
  snippet `AGENTS.md AUTO block contains stale feature id 'feat-deleted'`,
  fix_hint `rddf roadmap --update-agent-md`, exit code 2

#### Scenario: iteration.json feature_view missing active feature
- **GIVEN** `.rddf/roadmap/features/feat-x.md` exists with status active
- **AND** `.rddf/state/iteration.json::feature_view.features` does not contain `feat-x`
- **WHEN** `rddf doctor --category roadmap-feature` runs
- **THEN** emits 1 CRITICAL finding with category `roadmap-feature.iteration-drift`,
  snippet `iteration.json feature_view missing active feature 'feat-x'`,
  fix_hint `rddf doctor --category roadmap-feature (auto-recovery planned in follow-up)`, exit code 2

### Requirement: rdd-arch Phase 1 MUST output active feature fragments

The system MUST surface current active feature fragments to AI agents during the
rdd-arch Phase 1 setup stage by calling `rddf roadmap list-features --format table`
and rendering its output as part of the Phase 1 status display.

#### Scenario: rdd-arch Phase 1 entry shows active features
- **GIVEN** `.rddf/roadmap/features/feat-x.md` exists with status active
- **WHEN** AI agent invokes `skill_use("rdd-arch")` and reaches Phase 1 setup
- **THEN** the status display includes a "Feature Fragments" section listing `feat-x` from `rddf roadmap list-features --format table` output

