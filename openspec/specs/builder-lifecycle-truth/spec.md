# builder-lifecycle-truth Specification

## Purpose
TBD - created by archiving change fix-builder-handoff-p2-lifecycle-truth. Update Purpose after archive.

## Requirements

### Requirement: Builder handoff SHALL distinguish setup from completion

`execution_status` SHALL reflect the real implementation state, never the setup step: Phase 2 setup writes `running` (never `completed`), and `completed` is written only at archive. The Phase 2.5 review — the merge decision point — SHALL show the implementation's true progress (checked tasks over total) and SHALL report an inconsistency when the handoff claims `completed` while tasks remain unchecked. Legacy handoffs SHALL stay readable and never be taken as "done".

#### Scenario: A setup-only handoff does not claim completion

- **WHEN** Phase 2 setup finished while no task is checked yet
- **THEN** the handoff records `running` instead of `completed`, and the Phase 2.5 review shows the unchecked task count
