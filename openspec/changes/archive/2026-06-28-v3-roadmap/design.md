## Context

The v2.0.0-beta release completed the core v2.0 vision: state vector, event log, gate mechanism, loop engine, detectors, actions, interaction modes, human-in-loop nodes, tribunal, memory, lightweight sessions, and agents. 4 ADRs from the original v2.0 design scope were deferred:

- **ADR-0009 (Scheduled Triggers)**: Cron-like event triggers for the loop engine. Draft status — lowest maturity.
- **ADR-0010 (Full Multi-Session)**: v2.0 ships `lightweight session.py`. The full ADR describes parent-child session trees, parallel execution, and dependency scheduling. High value but significant effort.
- **ADR-0011 (Step Pipeline)**: Phase-template-driven step execution with trigger conditions. Replaces the current monolithic phase approach with composable steps.
- **ADR-0012 (Flow Customization)**: User-customizable flow via `.rdd-workflow/flow.yaml`, custom skill registration, conditional step skipping.

All 4 are design-complete but need implementation planning, prioritization, and resource allocation.

## Goals / Non-Goals

**Goals:**
- Evaluate each ADR for implementation effort (S/M/L/XL) and business value
- Assign each ADR to v2.1 (small, compatible additions) or v3.0 (larger, potentially breaking)
- Create placeholder openspec changes for each approved ADR
- Update roadmap.md to reflect the v3.0 vision

**Non-Goals:**
- Implementing any of the ADRs — this is planning only
- Re-opening already-decided ADR design decisions
- Deprecating v2.0 features

## Decisions

### Decision 1: Release targeting

Preliminary assessment (to be confirmed by ADR analysis):

| ADR | Recommended Target | Rationale |
|-----|-------------------|-----------|
| ADR-0009 (Scheduled Triggers) | v3.0 | Draft maturity, low urgency |
| ADR-0010 (Full Multi-Session) | v2.1 parallel track | v2.0 has lightweight base; parallel execution is natural next step |
| ADR-0011 (Step Pipeline) | v3.0 | Architectural change to phase execution model |
| ADR-0012 (Flow Customization) | v3.0 | Depends on ADR-0011's step model |

### Decision 2: Placeholder changes use minimal structure

Each placeholder openspec change will contain just `.openspec.yaml` and `proposal.md` (with ADR reference and scope). Full `design.md` and `tasks.md` will be created when implementation starts.

### Decision 3: roadmap.md becomes the v3.0 planning document

Replace the generic "Phase 1: User-defined" structure with concrete phase definitions mapped to ADRs. This makes roadmap.md actually useful for planning.