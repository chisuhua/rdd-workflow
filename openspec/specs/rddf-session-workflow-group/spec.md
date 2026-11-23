# rddf-session-workflow-group Specification

## Purpose
TBD - created by archiving change add-rddf-session-workflow-group. Update Purpose after archive.
## Requirements
### Requirement: workflow_group Links Multiple Sessions

The rddf-session entry hook SHALL record a `workflow_group` identifier on each session, derived from `RDDF_WORKFLOW_GROUP` env var (auto-generated UUID v4 when unset).

#### Scenario: Explicit env var recorded

- GIVEN `RDDF_WORKFLOW_GROUP=batch-2026-08-02` is set
- WHEN `rddf_session_hook_entry` is invoked
- THEN the session has `workflow_group="batch-2026-08-02"`

#### Scenario: Auto-generated UUID v4

- GIVEN `RDDF_WORKFLOW_GROUP` is unset on first entry
- WHEN entry completes
- THEN the session has `workflow_group` matching UUID v4 format (8-4-4-4-12 hex chars, version digit = 4)

#### Scenario: Shared group across multiple entries

- GIVEN two `rddf_session_hook_entry` calls with `RDDF_WORKFLOW_GROUP=batch-2026-08-02` and `RDDF_ALLOW_CROSS_STAGE_PARALLEL=yes`
- WHEN both complete (using different owners to bypass ConflictError)
- THEN both sessions have `workflow_group="batch-2026-08-02"`

