## Context

Phase 5 is the release phase. After four phases of building infrastructure, engine, advanced features, and migration, the v2.0.0-beta is ready to ship. The goal is to collect real-world feedback from at least 5 users and fix any critical (P0) issues found.

This phase is intentionally short (1 week, 3-4 person-days) because the focus is shipping and learning, not building more features.

## Goals / Non-Goals

**Goals:**
- Release v2.0.0-beta to npm
- Collect feedback from ≥ 5 beta users
- Fix all P0 issues found in beta
- Document release notes

**Non-Goals:**
- Adding new features to beta
- Full v2.0.0 stable release (separate future change)
- Marketing or promotion
- Long-term support commitments

## Decisions

### Decision 1: Beta version explicitly marked unstable

- **Why**: v2.0 is a major architectural change; users need to know it may have rough edges
- **Alternative**: Ship as v2.0.0 stable
- **Rejected**: Skipping beta skips the learning loop

### Decision 2: Feedback via GitHub Issues, not separate system

- **Why**: GitHub Issues is the standard; users already have accounts
- **Alternative**: Custom feedback form
- **Rejected**: Adds maintenance burden; users prefer familiar tools

### Decision 3: Performance optimizations are opportunistic, not required

- **Why**: v2.0 architecture is already structured for performance; further optimization can wait
- **Alternative**: Mandatory performance benchmarks
- **Rejected**: Premature optimization; beta feedback may reveal different priorities

## Risks / Trade-offs

- **Risk**: Critical bugs discovered in beta could delay stable release
  - **Mitigation**: Beta is explicitly unstable; set expectations in release notes
- **Risk**: Low user adoption (< 5 users)
  - **Mitigation**: Recruit from existing v1.x user base; offer migration support
- **Risk**: Performance issues surface
  - **Mitigation**: Performance optimizations included; can be expanded based on profiling
- **Trade-off**: Beta length (1 week) vs thoroughness — chose beta for fast learning cycle
