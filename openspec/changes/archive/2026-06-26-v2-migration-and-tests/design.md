## Context

Phase 4 brings the v2.0 architecture to user-visible skills. The three-phase split (ADR-0003) requires new state machines for arch and plan phases. The comprehensive test suite ensures all v2 components work together. The migration guide helps v1.x users transition.

The key design challenge is backward compatibility: v1.x users invoke `guide-spec.md`, which currently combines architecture definition and change generation. v2.0 needs to split this without breaking existing workflows. The solution: keep `guide-spec.md` as an alias that internally invokes `guide-arch.md` → `guide-plan.md` in sequence.

## Goals / Non-Goals

**Goals:**
- Provide `guide-arch.md` for architecture definition (ADR creation, roadmap definition)
- Provide `guide-plan.md` for change generation (scan, propose, deps)
- Provide comprehensive test coverage (≥ 80%)
- Provide clear migration documentation
- Maintain 100% backward compatibility via alias

**Non-Goals:**
- Replacing v1.x skill implementations
- Auto-migration of user data
- Training or onboarding materials
- Performance optimization (separate concern)

## Decisions

### Decision 1: `guide-spec.md` becomes alias for arch + plan

- **Why**: Existing v1.x workflows continue to work without code changes
- **Alternative**: Force users to update to new skill names
- **Rejected**: Breaking change is a major adoption barrier

### Decision 2: Phase handoff via JSON files, not state vector

- **Why**: Phase handoff is v2.0-specific; JSON files are simpler than extending state vector
- **Alternative**: Extend state vector with handoff fields
- **Rejected**: State vector is for runtime state; handoff is for phase-boundary data

### Decision 3: Test suite uses pytest, not bats

- **Why**: pytest is the Python standard; bats is for shell scripts
- **Alternative**: bats (consistent with v1.x)
- **Rejected**: v2.0 has 5,000+ lines of Python; pytest is more appropriate

### Decision 4: Migration guide is human-written, not auto-generated

- **Why**: Migration involves conceptual shifts (state machine → loop) that need explanation
- **Alternative**: Auto-generate from config diff
- **Rejected**: Cannot capture conceptual changes

## Risks / Trade-offs

- **Risk**: Splitting `guide-spec.md` may lose functionality
  - **Mitigation**: Alias pattern preserves v1.x behavior; integration tests verify equivalence
- **Risk**: Test coverage target (≥ 80%) may be hard to achieve
  - **Mitigation**: Phase 4 dedicated to testing; can iterate to reach target
- **Risk**: Migration guide may not cover all user patterns
  - **Mitigation**: Beta testing with 5+ users; iterate on feedback
- **Trade-off**: Three skills instead of two adds complexity — accepted for clearer separation of concerns
