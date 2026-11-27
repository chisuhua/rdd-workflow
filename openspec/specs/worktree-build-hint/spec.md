# worktree-build-hint Specification

## Purpose
TBD - created by archiving change improve-worktree-build-hint. Update Purpose after archive.

## Requirements

### Requirement: Worktree creation SHALL announce a missing build directory

When Phase 2 creates a worktree that has no `build/` directory, it SHALL print one fixed-text hint line on stderr telling the agent that the first build may be slow and that it should run the build as a background task instead of polling with sleep. The hint SHALL NOT appear when a `build/` directory exists, the detection SHALL be read-only, and no execution behaviour SHALL change.

#### Scenario: A worktree without a build directory gets the hint

- **WHEN** Phase 2 created a worktree whose directory has no `build/`
- **THEN** the Phase 2 output is inspected
