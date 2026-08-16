# cross-repo-deps-cache Specification

## Purpose
TBD - created by archiving change add-cross-repo-state-schemas. Update Purpose after archive.
## Requirements
### Requirement: Cross-repo dependency graph caching

The system SHALL cache cross-repo dependency graph scan results with TTL support.

#### Scenario: Cache dependency scan results
- **WHEN** a cross-repo dependency scan completes
- **THEN** `.rddf/state/.cross-repo-deps-cache.json` is written
- **AND** `cache_generated_at` records scan time
- **AND** `spokes` lists all scanned repos

#### Scenario: Use cached dependency graph
- **WHEN** deps analysis runs and cache is fresh (within TTL)
- **THEN** cached `dependency_graph` is used instead of rescanning
- **AND** `ttl_seconds` controls cache freshness (default 3600s)

#### Scenario: Cache staleness detection
- **WHEN** cached graph exceeds TTL
- **THEN** cache is considered stale
- **AND** fresh scan should be triggered

---

### Requirement: Dependency graph structure

The dependency graph MUST contain valid nodes and edges.

#### Scenario: Valid dependency graph nodes
- **GIVEN** nodes with `id`, `repo`, `change`, `wave` required fields
- **WHEN** schema validation runs on node entries
- **THEN** nodes pass validation

#### Scenario: Valid dependency graph edges
- **GIVEN** edges with `from`, `to`, `type` required fields
- **WHEN** schema validation runs on edge entries
- **THEN** edges pass validation

#### Scenario: Edge type enum validation
- **GIVEN** an edge with `type` not in `strong, weak, manual_deps`
- **WHEN** schema validation runs
- **THEN** validation fails with enum error

---

### Requirement: Blocked changes tracking

The system SHALL track changes blocked by cross-repo dependencies.

#### Scenario: Record blocked change with Hub Issue
- **WHEN** a change is blocked by cross-repo dependency
- **THEN** `blocked_changes` entry links change to `blocked_by` and `hub_issue`
- **AND** pattern `^[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+#[0-9]+$` is enforced for hub_issue

#### Scenario: Empty blocked_changes when no blockers
- **WHEN** no changes are blocked
- **THEN** `blocked_changes` is an empty array `[]`

